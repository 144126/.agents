#!/usr/bin/env node
// prune: a judge model (Haiku) marks transcript entries the session no longer needs; they are stubbed
// in a new session file (never deleted) so uuid chains and tool_use/tool_result pairs stay valid.
// Usage: prune.ts [session id|path] [--dry] [--model m]. Default session: $CLAUDE_CODE_SESSION_ID.
import { readFileSync, writeFileSync, readdirSync, existsSync, symlinkSync, statSync } from 'node:fs'
import { execFile } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { homedir, tmpdir } from 'node:os'
import { join, dirname, basename } from 'node:path'

const args = process.argv.slice(2)
const flag = (n: string) => { const i = args.indexOf(n); return i < 0 ? undefined : args.splice(i, 2)[1] }
const model = flag('--model') ?? 'claude-haiku-5-5'
const opt = (n: string) => args.includes(n) && (args.splice(args.indexOf(n), 1), true)
const dry = opt('--dry'), force = opt('--force')
const min_chars = 1000 // smaller entries are not worth a stub
const tail_chars = 80_000 // ~20k tokens of the newest context stay untouched
const batch_chars = 240_000 // ~60k tokens per judge call, under Haiku's 100k price step
const image_chars = 6000 // an image costs ~1.5k tokens
const min_gain = 60_000 // a resume rebuilds the prompt cache: below ~15k tokens (and 20%) it costs more than it saves

const home = process.env.CLAUDE_CONFIG_DIR ?? join(homedir(), '.claude')
const projects = join(home, 'projects')
const sid = args[0] ?? process.env.CLAUDE_CODE_SESSION_ID
if (!sid) throw new Error('no session: pass an id or path (CLAUDE_CODE_SESSION_ID is unset)')
const src = sid.endsWith('.jsonl') ? sid : readdirSync(projects).map(d => join(projects, d, sid + '.jsonl')).find(existsSync)
if (!src) throw new Error(`session ${sid} not found under ${projects}`)
const old = basename(src, '.jsonl')

// the live session may be mid-write: skip a torn last line
const lines: any[] = readFileSync(src, 'utf8').split('\n').flatMap(l => { try { return l ? [JSON.parse(l)] : [] } catch { return [] } })
const last_boundary = lines.findLastIndex(e => e.type === 'system' && e.subtype === 'compact_boundary')
const tool_uses = new Map<string, any>()
for (const e of lines) if (e.type === 'assistant' && Array.isArray(e.message?.content))
  for (const b of e.message.content) if (b.type === 'tool_use') tool_uses.set(b.id, b)
// Claude Code swaps big tool results for disk previews at load time (content-replacement); the model sees those
const replaced = new Map<string, string>()
for (const e of lines) if (e.type === 'content-replacement' && e.sessionId === old && !e.agentId)
  for (const r of e.replacements ?? []) if (r.kind === 'tool-result') replaced.set(r.toolUseId, r.replacement)

const text_of = (v: unknown): string => typeof v === 'string' ? v
  : Array.isArray(v) ? v.map(x => x?.text ?? '').join('\n') : JSON.stringify(v ?? '')
const images = (v: unknown) => Array.isArray(v) ? v.filter(x => x?.type === 'image').length : 0
const big_strings = (o: any) => Object.entries(o ?? {}).filter(([, v]) => typeof v === 'string' && v.length > 300) as [string, string][]
const brief = (input: any) => ['file_path', 'path', 'command', 'pattern', 'url', 'query', 'description', 'prompt']
  .filter(k => typeof input?.[k] === 'string').map(k => `${k}=${input[k].replace(/\s+/g, ' ').slice(0, 160)}`).join(' ')
const machine_user = /^\s*<(bash-stdout|bash-stderr|local-command-stdout|task-notification)/
const never = new Set(['ToolSearch', 'Skill'])

const msgs = lines.map((e, l) => [e, l] as const).filter(([e, l]) => l > last_boundary
  && (e.type === 'user' || e.type === 'assistant') && !e.isSidechain && e.message?.content != null)
const size = (e: any) => typeof e.message.content === 'string' ? e.message.content.length
  : e.message.content.reduce((s: number, b: any) => s + (b.type === 'tool_result' ? (replaced.get(b.tool_use_id) ?? text_of(b.content)).length
    + images(b.content) * image_chars : b.type === 'image' ? image_chars : b.type === 'thinking' || b.type === 'redacted_thinking' ? 0 : JSON.stringify(b).length), 0)
const total = msgs.reduce((s, [e]) => s + size(e), 0)
let seen = 0
const tail_from = msgs.findIndex(([e]) => (seen += size(e)) > total - tail_chars)

// item: {i: id, l: line, b: block, k: kind (r tool result, u tool input, t user text, a assistant text), n: tool + input brief, c: chars, h: preview}
type item = { i: number; l: number; b: number; k: string; n: string; c: number; h: string }
const items: item[] = [], timeline: string[] = []
const preview = (s: string) => (s.length > 600 ? s.slice(0, 400) + ' … ' + s.slice(-150) : s).replace(/\s+/g, ' ')
msgs.forEach(([e, l], m) => {
  const content = typeof e.message.content === 'string' ? [{ type: 'text', text: e.message.content }] : e.message.content
  content.forEach((b: any, bi: number) => {
    const add = (k: string, n: string, c: number, s: string) => {
      if (m < tail_from && c >= min_chars) {
        items.push({ i: items.length, l, b: bi, k, n, c, h: preview(s) })
        timeline.push(`#${items.length - 1}`)
      } else if (k === 't' || k === 'a') timeline.push(`${k === 't' ? 'user' : 'assistant'}: ${preview(s).slice(0, 300)}`)
    }
    if (b.type === 'tool_result') {
      const u = tool_uses.get(b.tool_use_id)
      if (never.has(u?.name) || (Array.isArray(b.content) && b.content.some((x: any) => x?.type === 'tool_reference'))) return
      const s = replaced.get(b.tool_use_id) ?? text_of(b.content), im = images(b.content)
      add('r', `${u?.name ?? '?'} ${brief(u?.input)}`, s.length + im * image_chars, (im ? `[${im} image] ` : '') + s)
    } else if (b.type === 'tool_use') {
      timeline.push(`call: ${b.name} ${brief(b.input)}`)
      const s = big_strings(b.input).map(([k, v]) => `${k}: ${v}`).join('\n')
      add('u', `${b.name} ${brief(b.input)}`, s.length, s)
    } else if (b.type === 'text' && !e.isMeta && !e.isCompactSummary) {
      if (e.type === 'assistant' || machine_user.test(b.text)) add(e.type === 'user' ? 't' : 'a', '', b.text.length, b.text)
      else timeline.push(`user: ${preview(b.text).slice(0, 600)}`)
    }
  })
})
if (!items.length) { console.log('nothing to prune'); process.exit(0) }

const kinds: Record<string, string> = { r: 'tool output', u: 'tool input', t: 'command output', a: 'assistant msg' }
const ask = (batch: item[]) => new Promise<{ p: number[]; cost: number }>((done, fail) => {
  const ids = new Set(batch.map(x => `#${x.i}`))
  const prompt = `You prune a coding agent's conversation so it fits in less context. The agent continues the task afterwards.
For each numbered entry decide if the agent still needs its full text to finish the current task.
Prune when: output already acted on or superseded (a file read again or edited later, a command re-run later), exploration that led nowhere, verbose logs and listings, failed attempts already fixed, screenshots already looked at, long inputs whose effect is on disk (Write/Edit bodies).
Keep when it holds user requirements, decisions, constraints, unresolved errors, facts stored nowhere else, or the current state of work. When unsure, keep.
A pruned entry becomes a short stub naming the tool and its input, so the agent can re-run it.

Conversation in order (#n = entry to judge, shown below):
${timeline.map(t => ids.has(t) ? t : t.startsWith('#') ? '(other entry)' : t).join('\n')}

Entries (id | kind | tool and input | chars | preview):
${batch.map(x => `#${x.i} | ${kinds[x.k]} | ${x.n} | ${x.c}\n${x.h}`).join('\n\n')}

Return {"p": [ids to prune]}.`
  const env = { ...process.env }
  for (const k of ['CLAUDECODE', 'CLAUDE_CODE_EFFORT_LEVEL', 'CLAUDE_EFFORT', 'MAX_THINKING_TOKENS', 'CLAUDE_CODE_SESSION_ID',
    'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN']) delete env[k]
  const p = execFile('claude', ['-p', '--model', model, '--effort', 'low', '--no-session-persistence', '--tools', '',
    '--strict-mcp-config', '--disable-slash-commands', '--system-prompt', 'You judge transcript entries. Answer only with the schema.',
    '--output-format', 'json', '--json-schema', JSON.stringify({ type: 'object', properties: { p: { type: 'array', items: { type: 'integer' } } }, required: ['p'] })],
    { env, cwd: tmpdir(), maxBuffer: 1 << 26, timeout: 300_000 }, (err, out) => {
      try {
        const r = JSON.parse(out)
        if (r.is_error || !r.structured_output) throw new Error(r.result ?? r.subtype)
        done({ p: r.structured_output.p, cost: r.total_cost_usd ?? 0 })
      } catch (e) { fail(new Error(`judge failed: ${err?.message ?? e}`)) }
    })
  p.stdin!.end(prompt)
})
const batches: item[][] = [[]]
let fill = 0
for (const x of items) {
  if (fill + x.h.length > batch_chars && batches.at(-1)!.length) batches.push([]), fill = 0
  batches.at(-1)!.push(x), fill += x.h.length + x.n.length + 40
}
const verdicts = await Promise.all(batches.map(ask))
const pick = new Set(verdicts.flatMap(v => v.p))
const pruned = items.filter(x => pick.has(x.i))
const cost = verdicts.reduce((s, v) => s + v.cost, 0)

let freed = 0
for (const x of pruned) {
  const e = lines[x.l]
  if (typeof e.message.content === 'string') e.message.content = [{ type: 'text', text: e.message.content }]
  const b = e.message.content[x.b]
  let stub: string
  if (x.k === 'r') {
    b.content = stub = `[pruned: ${x.n.trim().slice(0, 200)} output, ${x.c} chars. Re-run if needed.]`
    if (replaced.has(b.tool_use_id)) replaced.set(b.tool_use_id, stub)
  } else if (x.k === 'u') {
    for (const [k, v] of big_strings(b.input)) b.input[k] = `[pruned ${v.length} chars]`
    stub = ''
  } else b.text = stub = b.text.slice(0, 200) + ` … [pruned ${x.c} chars]`
  freed += x.c - stub.length
}
for (const e of lines) if (e.type === 'content-replacement' && e.sessionId === old && !e.agentId)
  for (const r of e.replacements ?? []) if (r.kind === 'tool-result' && replaced.has(r.toolUseId)) r.replacement = replaced.get(r.toolUseId)

const k = (n: number) => `${Math.round(n / 4000)}k`
const report = `${pruned.length}/${items.length} entries pruned: ~${k(total)} → ~${k(total - freed)} tokens without thinking ($${cost.toFixed(3)}, ${batches.length} judge call${batches.length > 1 ? 's' : ''})`
if (dry) {
  for (const x of items) console.log(pick.has(x.i) ? '-' : '+', `#${x.i}`, kinds[x.k], x.n.slice(0, 80), x.c, x.h.slice(0, 80))
  console.log(report, '(dry run, nothing written)')
  process.exit(0)
}
if (!force && freed < min_gain && freed < total / 5) { console.log(report, '(too little to gain; --force writes anyway)'); process.exit(0) }

// the snapshot ends on this very Bash call, which has no result yet: answer it so the resumed agent sees prune succeed
const id = randomUUID()
const resolved = new Set(lines.flatMap(e => e.type === 'user' && Array.isArray(e.message?.content)
  ? e.message.content.filter((b: any) => b.type === 'tool_result').map((b: any) => b.tool_use_id) : []))
const leaf = lines.findLast(e => (e.type === 'user' || e.type === 'assistant') && !e.isSidechain)
const open = leaf?.type === 'assistant' ? lines.filter(e => e.type === 'assistant' && e.message?.id === leaf.message.id && !e.isSidechain)
  .flatMap(e => e.message.content.filter((b: any) => b.type === 'tool_use' && !resolved.has(b.id))) : []
if (open.length) lines.push({
  parentUuid: leaf.uuid, isSidechain: false, type: 'user', uuid: randomUUID(), timestamp: new Date().toISOString(),
  userType: leaf.userType, entrypoint: leaf.entrypoint, cwd: leaf.cwd, sessionId: old, version: leaf.version, gitBranch: leaf.gitBranch,
  message: { role: 'user', content: open.map((b: any) => ({ type: 'tool_result', tool_use_id: b.id,
    content: `${report}. This is the pruned session ${id}; the unpruned original is ${src}.` })) },
  toolUseResult: { stdout: report, stderr: '', interrupted: false, isImage: false }, sourceToolAssistantUUID: leaf.uuid,
})

const title = lines.findLast(e => e.type === 'custom-title' || e.type === 'ai-title')
if (title) for (const k of ['customTitle', 'aiTitle']) if (title[k]) title[k] += ' (pruned)'

const uuids = new Set(lines.map(e => e.uuid).filter(Boolean))
const broken = lines.filter(e => e.parentUuid && !uuids.has(e.parentUuid) && !e.isSidechain).length
if (broken) console.error(`warning: ${broken} entries point at missing parents (as in the original)`)
const dst = join(dirname(src), id + '.jsonl')
writeFileSync(dst, lines.map(e => JSON.stringify(e.sessionId === old ? { ...e, sessionId: id } : e)).join('\n') + '\n', { mode: 0o600 })
// subagent transcripts, saved tool outputs and /rewind backups are keyed by session id: share them
for (const d of [join(dirname(src), old), join(home, 'file-history', old)])
  if (existsSync(d)) symlinkSync(d, join(dirname(d), id))
console.log(report)
console.log(`resume: /exit, then claude --resume ${id}`)
if (statSync(src).nlink > 1) console.log('note: the original is pinned (hardlink); re-pin the pruned session')
