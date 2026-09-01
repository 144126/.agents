#!/usr/bin/env node
import {readFileSync,writeFileSync,existsSync,mkdirSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
import {homedir} from 'node:os'
const THINK=resolve(homedir(),'think')
const slug=s=>s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,48)||'topic'
const die=m=>{console.error(m);process.exit(1)}
const load=f=>{
  const j=JSON.parse(readFileSync(f,'utf8'))
  if(Array.isArray(j.a)) return {p:j._||'',a:j.a,d:j.d||j.a.map(()=>0)}
  const ks=Object.keys(j).filter(k=>k!=='_').sort()
  return {p:j._||'',a:ks.map(k=>j[k].s),d:ks.map(k=>j[k].d||0)}
}
const MODEL='z-ai/glm-5.3-flash'
const save=(f,p,a,d)=>{mkdirSync(dirname(f),{recursive:true});writeFileSync(f,JSON.stringify({_:p,a,d},null,'\t')+'\n')}
const prompt=(p,s)=>`Think extremely deeply about this ONE angle. Do not look at prior conclusions.\n\nGlobal context:\n${p||'(none)'}\n\nAngle:\n${s}\n\nFrom first principles. Steelman both sides. Look for contradictions. Prefer concrete.\n3–8 atomic conclusions from this angle only.\nOutput ONLY markdown bullets: "- <sentence>"`
async function call(content){
  const base=(process.env.OPENROUTER_BASE||'https://openrouter.ai/api/v1').replace(/\/+$/,'')
  const key=process.env.OPENROUTER_API_KEY||''
  if(!key) die('no OPENROUTER_API_KEY')
  const r=await fetch(base+'/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model:MODEL,messages:[{role:'user',content}],max_tokens:8192,temperature:0.7})})
  const t=await r.text()
  if(!r.ok) die(`LLM ${t.slice(0,800)} (model=${MODEL})`)
  let j;try{j=JSON.parse(t)}catch{die('bad json')}
  const c=j.choices?.[0]?.message?.content
  const s=typeof c==='string'?c.trim():Array.isArray(c)?c.map(x=>x.text||'').join('\n').trim():''
  if(!s) die('empty LLM response')
  return s
}
async function run(file){
  console.log(`rethink: ${file}\nmodel: ${MODEL}`)
  const conc=file.replace(/\.r$/,'')+'.conclusions.md'
  while(true){
    const {p,a,d}=load(file)
    const i=d.findIndex(v=>v!==1)
    if(i===-1){console.log('0 — all done');break}
    console.log(`\n── ${i+1}/${a.length} a${String(i+1).padStart(2,'0')} ──\n${a[i].slice(0,160)}`)
    const raw=await call(prompt(p,a[i]))
    const lines=raw.split('\n').map(l=>l.trim()).filter(Boolean)
    let bullets=lines.filter(l=>/^[-*•]\s+/.test(l)).map(l=>`- ${l.replace(/^[-*•]\s+/,'').trim()}`)
    if(!bullets.length) bullets=lines.map(l=>l.startsWith('-')?l:`- ${l}`)
    const clean=bullets
    if(!clean.length) die('no bullets')
    clean.forEach(b=>console.log(`  ${b}`))
    writeFileSync(conc,(existsSync(conc)?readFileSync(conc,'utf8'):'')+(clean.join('\n')+'\n'))
    d[i]=1;save(file,p,a,d)
    console.log(`  ← ${clean.length} bullets, ${d.filter(v=>v===1).length}/${a.length} done`)
  }
  if(!existsSync(conc)) die('no conclusions')
  console.log(`\nwrite → ${conc}`)
}
async function main(){
  const args=process.argv.slice(2)
  if(!args.length||args.includes('-h')||args.includes('--help')){console.log('rethink "<topic>" N [--angle "s"]...\nrethink <file.r>');process.exit(0)}
  const angles=[];const rest=[]
  for(let i=0;i<args.length;i++){const a=args[i];if(a==='--angle')angles.push(args[++i]||die('--angle needs text'));else rest.push(a)}
  const first=rest[0];if(!first) die('need <topic> N or <file.r>')
  if(first.endsWith('.r')||existsSync(resolve(first))){await run(resolve(first));return}
  const topic=first;const n=parseInt(rest[1]||'',10);if(!n||n<1||n>200) die('need <topic> N 1..200')
  if(angles.length&&angles.length!==n) die(`got ${angles.length} --angle, expected ${n}`)
  const list=angles.length?angles:Array.from({length:n},(_,i)=>`angle ${i+1} of ${n} on: ${topic}`)
  const file=resolve(THINK,slug(topic)+'.r')
  if(existsSync(file)){console.log(`resume ${file}`);await run(file);return}
  save(file,topic,list,list.map(()=>0));console.log(`init → ${file} (${n} leaves)`);await run(file)
}
main().catch(e=>{console.error(e.stack||e.message);process.exit(1)})
