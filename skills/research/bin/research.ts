#!/usr/bin/env node
// research "<question>" [--angle "..."]...
// 3-phase: think -> search (thinking decides) -> think
// glm-5.3-flash via OpenRouter only
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync, readdirSync, appendFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, resolve, basename } from 'node:path';

type Cfg = { baseUrl: string; apiKey: string; model: string; timeout: number; max_tokens: number; api: 'chat' | 'responses'; reasoning?: string };

const PROVIDERS: Record<string, { baseUrl: () => string; apiKey: () => string }> = {
	'amazon-bedrock-mantle': {
		baseUrl: () => (process.env.AMAZON_BEDROCK_MANTLE_OPENAI_COMPATIBLE_URL || 'https://bedrock-mantle.us-west-2.api.aws/openai/v1').replace(/\/+$/, ''),
		apiKey: () => process.env.AMAZON_BEDROCK_MANTLE_API_KEY || '',
	},
	openrouter: {
		baseUrl: () => (process.env.OPENROUTER_BASE || 'https://openrouter.ai/api/v1').replace(/\/+$/, ''),
		apiKey: () => process.env.OPENROUTER_API_KEY || '',
	},
};

let CFG: Cfg | null = null;
type Hit = { url: string; title: string; excerpt: string };
type Claim = { claim: string; quote: string; cited_primary: string | null; source_url: string };

const usages: any[] = [];
function add_usage(a: any, b: any): any {
	if (typeof b === 'number' && Number.isFinite(b)) return (typeof a === 'number' && Number.isFinite(a) ? a : 0) + b;
	if (b && typeof b === 'object' && !Array.isArray(b)) {
		const out: any = a && typeof a === 'object' && !Array.isArray(a) ? { ...a } : {};
		for (const [k, v] of Object.entries(b)) out[k] = add_usage(out[k], v);
		return out;
	}
	return b ?? a;
}
function record_usage(json: any) {
	const u = json?.usage;
	if (u && typeof u === 'object') {
		usages.push(u);
		console.log(`usage: ${JSON.stringify(u)}`);
		vlog('usage', `openrouter usage`, u);
	} else {
		console.log('usage: (none in response)');
		vlog('usage', `no usage in response`, { keys: json ? Object.keys(json).slice(0,20) : null });
	}
}
function dump_usage() {
	if (!usages.length) return;
	const total = usages.reduce((a, u) => add_usage(a, u), {});
	console.log(`usage calls: ${usages.length}`);
	usages.forEach((u, i) => console.log(`usage ${i + 1}: ${JSON.stringify(u)}`));
	console.log(`usage total: ${JSON.stringify(total)}`);
	vlog('usage:total', `run usage`, { calls: usages.length, total });
}
const die = (m: string): never => { dump_usage(); console.error(m); process.exit(1); };

// ── extremely verbose logging ──
const VERBOSE = (() => {
	if (process.env.RESEARCH_QUIET === '1' || process.argv.includes('--quiet')) return false;
	if (process.env.RESEARCH_VERBOSE === '0' || process.argv.includes('--no-verbose')) return false;
	return true;
})();
const SIMPLE = process.env.RESEARCH_SIMPLE === '1' || process.argv.includes('--simple');
const START_MS = Date.now();
let VERBOSE_LOG_FILE: string | null = null;
function ts(): string { return new Date().toISOString(); }
function elapsed(): string { return `+${((Date.now() - START_MS)/1000).toFixed(3)}s`; }
function redact(s: string): string { return s.replace(/sk-[a-zA-Z0-9_-]{10,}/g,'sk-***').replace(/Bearer\s+[^\s"]{10,}/g,'Bearer ***').replace(/"apiKey"\s*:\s*"[^"]+"/g,'"apiKey":"***"'); }
function trunc(s: string, n=2000): string { if (s.length <= n) return s; return s.slice(0,n) + ` … [truncated ${s.length-n} chars]`; }
function jtrunc(o: any, n=2000): string { try { return trunc(JSON.stringify(o), n); } catch { return trunc(String(o), n); } }
function vlog(tag: string, msg: string, data?: any) {
	if (!VERBOSE) return;
	if (SIMPLE) {
		const short = data !== undefined ? ` ${typeof data==='string' ? trunc(data,120) : jtrunc(data,120)}` : '';
		const line = `${tag}: ${msg}${short}`;
		console.error(line);
		if (VERBOSE_LOG_FILE) try { appendFileSync(VERBOSE_LOG_FILE, line + '\n'); } catch {}
		return;
	}
	const line = `[${ts()} ${elapsed()} pid=${process.pid} ${tag}] ${msg}${data!==undefined ? ' ' + (typeof data==='string' ? trunc(data) : jtrunc(data)) : ''}`;
	console.error(line);
	if (VERBOSE_LOG_FILE) try { appendFileSync(VERBOSE_LOG_FILE, line + '\n'); } catch {}
}
function vlog_kv(tag: string, kv: Record<string, any>) {
	if (!VERBOSE) return;
	if (SIMPLE) { vlog(tag, Object.entries(kv).map(([k,v])=> `${k}=${typeof v==='string'?trunc(v,80):jtrunc(v,80)}`).join(' ')); return; }
	const parts = Object.entries(kv).map(([k,v]) => `${k}=${typeof v==='string' ? trunc(v,500) : jtrunc(v,500)}`).join(' ');
	vlog(tag, parts);
}
function hr_bytes(n: number): string { if (n<1024) return n+'B'; if (n<1024*1024) return (n/1024).toFixed(1)+'KB'; return (n/1024/1024).toFixed(2)+'MB'; }

vlog('init', `research verbose logging enabled`, { VERBOSE, argv: process.argv.slice(2), node: process.version, cwd: process.cwd(), pid: process.pid, ppid: process.ppid });
vlog('env', `env snapshot`, {
	OPENROUTER_KEY_present: !!process.env.OPENROUTER_API_KEY,
	RESEARCH_VERBOSE: process.env.RESEARCH_VERBOSE || '(default on)',
	ROOT_will_be: resolve(homedir(), 'search'),
	THINK_will_be: resolve(homedir(), 'think'),
});

const ROOT = resolve(homedir(), 'search');
const THINK = resolve(homedir(), 'think');
const CND_TS = resolve(homedir(), '.agents/skills/condense-search/cnd.ts');
const CND_PY = resolve(homedir(), '.agents/skills/condense-search/cnd.py');
const CND = existsSync(CND_TS) ? CND_TS : CND_PY;
vlog('cfg', `constants resolved`, { ROOT, THINK, CND });

function slugify(s: string): string { const r = (s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'topic').slice(0, 64); vlog('slugify', `input=${trunc(s,80)} → slug=${r}`); return r; }
function parse_model(raw: string): { provider: string; model: string } {
	const i = raw.indexOf('/');
	if (i < 1) die('model must be provider/id, e.g. amazon-bedrock-mantle/xai.grok-4.6');
	return { provider: raw.slice(0, i), model: raw.slice(i + 1) };
}
function make_cfg(spec: string, reasoning: string): Cfg {
	const { provider, model } = parse_model(spec);
	const p = PROVIDERS[provider];
	if (!p) die(`unknown provider ${provider}. known: ${Object.keys(PROVIDERS).join(', ')}`);
	const apiKey = p.apiKey();
	if (!apiKey) die(`no api key for ${provider}`);
	const cfg: Cfg = { baseUrl: p.baseUrl(), apiKey, model, timeout: 600000, max_tokens: 8000, api: 'chat', reasoning: reasoning || undefined };
	vlog('make_cfg', `cfg built`, { provider, model: cfg.model, baseUrl: cfg.baseUrl, reasoning: cfg.reasoning || 'off', key_len: apiKey.length });
	return cfg;
}
function sh(cmd: string, args: string[], timeout = 90000): { ok: boolean; out: string; err: string } {
	const cmdline = `${cmd} ${args.map(a => a.includes(' ') ? `"${a}"` : a).join(' ')}`;
	const t0 = Date.now();
	vlog('sh:start', `spawnSync`, { cmd, args, cmdline: trunc(cmdline, 600), timeout, maxBuffer: '20MB' });
	const r = spawnSync(cmd, args, { encoding: 'utf8', timeout, maxBuffer: 20 * 1024 * 1024 });
	const dt = Date.now() - t0;
	const status = r.status;
	const signal = (r as any).signal;
	vlog('sh:done', `spawnSync done`, {
		cmdline: trunc(cmdline, 400),
		status, signal,
		ok: status===0,
		duration_ms: dt,
		duration_s: (dt/1000).toFixed(3),
		stdout_bytes: (r.stdout||'').length,
		stderr_bytes: (r.stderr||'').length,
		error: (r as any).error?.message || null,
		stdout_preview: trunc(redact(r.stdout||''), 600),
		stderr_preview: trunc(redact(r.stderr||''), 600),
	});
	if (r.stdout) vlog('sh:stdout', trunc(redact(r.stdout), 1500));
	if (r.stderr) vlog('sh:stderr', trunc(redact(r.stderr), 1500));
	if ((r as any).error) vlog('sh:error', (r as any).error.message);
	return { ok: r.status === 0, out: r.stdout || '', err: r.stderr || (r as any).error?.message || '' };
}
function write_atomic(path: string, text: string) {
	const t0 = Date.now();
	vlog('write_atomic:start', `writing file`, { path, bytes: text.length, hr: hr_bytes(text.length), preview: trunc(text, 400) });
	mkdirSync(dirname(path), { recursive: true });
	const tmp = path + '.tmp';
	writeFileSync(tmp, text);
	renameSync(tmp, path);
	const dt = Date.now() - t0;
	vlog('write_atomic:done', `file written`, { path, bytes: text.length, duration_ms: dt });
	if (VERBOSE_LOG_FILE && path === VERBOSE_LOG_FILE) {} else if (VERBOSE_LOG_FILE) try { appendFileSync(VERBOSE_LOG_FILE, `[${ts()} write_atomic] ${path} ${hr_bytes(text.length)}\n`); } catch {}
}
function pid_of(url: string): string {
	const u = url.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');
	const h = createHash('sha1').update(u).digest('hex').slice(0, 16);
	vlog('pid_of', `${url} → normalized=${trunc(u,120)} → pid=${h}`);
	return h;
}
function text_of(cfg: Cfg, json: any): string {
	vlog('text_of:start', `extracting text from LLM json`, { api: cfg.api, model: cfg.model, json_keys: json ? Object.keys(json).slice(0,20) : null, has_output_text: !!json?.output_text, has_output: !!json?.output, has_choices: !!json?.choices });
	if (cfg.api === 'responses') {
		if (typeof json?.output_text === 'string' && json.output_text.trim()) {
			vlog('text_of', `using output_text`, { len: json.output_text.length, preview: trunc(json.output_text, 300) });
			return json.output_text.trim();
		}
		const parts: string[] = [];
		for (const item of json?.output || []) for (const c of item?.content || []) if (typeof c?.text === 'string') parts.push(c.text);
		const joined = parts.join('\n').trim();
		vlog('text_of', `joined output parts`, { parts: parts.length, len: joined.length, preview: trunc(joined, 300) });
		return joined;
	}
	const c = json?.choices?.[0]?.message?.content ?? json?.choices?.[0]?.text ?? '';
	vlog('text_of', `chat choices extraction`, { type: typeof c, is_array: Array.isArray(c), len: typeof c==='string' ? c.length : 0 });
	if (typeof c === 'string') return c.trim();
	if (Array.isArray(c)) return c.map((x: any) => x.text || x.content || '').join('\n').trim();
	return '';
}
async function fetch_with_cfg(cfg: Cfg, prompt: string, isChat: boolean): Promise<string> {
	const url = cfg.baseUrl + (cfg.api === 'responses' ? '/responses' : '/chat/completions');
	const body: any = cfg.api === 'responses' ? { model: cfg.model, input: prompt, max_output_tokens: cfg.max_tokens } : { model: cfg.model, messages: [{ role: 'user', content: prompt }], max_tokens: cfg.max_tokens, temperature: isChat ? 0.7 : 0.2 };
	if (cfg.reasoning) body.reasoning = { effort: cfg.reasoning };
	vlog('fetch_with_cfg:start', `LLM call start`, {
		url, model: cfg.model, api: cfg.api, isChat,
		prompt_chars: prompt.length, prompt_preview: trunc(prompt, 500),
		body_keys: Object.keys(body as any),
		timeout_ms: cfg.timeout, max_tokens: cfg.max_tokens,
	});
	let last = '';
	for (let i = 1; i <= 3; i++) {
		const attempt_t0 = Date.now();
		vlog('fetch_with_cfg:attempt', `attempt ${i}/3`, { url, model: cfg.model, prompt_len: prompt.length, body_bytes: JSON.stringify(body).length });
		const ac = new AbortController();
		const t = setTimeout(() => { vlog('fetch_with_cfg:timeout', `abort timeout fired attempt ${i}`, { timeout_ms: cfg.timeout }); ac.abort(); }, cfg.timeout);
		try {
			const fetch_t0 = Date.now();
			const res = await fetch(url, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${cfg.apiKey}`,
			'Content-Type': 'application/json',
			'HTTP-Referer': 'https://pi.dev',
			'X-OpenRouter-Title': 'pi',
			'X-OpenRouter-Categories': 'cli-agent',
		}, body: JSON.stringify(body), signal: ac.signal });
			const fetch_dt = Date.now() - fetch_t0;
			vlog('fetch_with_cfg:response', `http response attempt ${i}`, { status: res.status, statusText: res.statusText, headers: Object.fromEntries(res.headers.entries()), duration_ms: fetch_dt });
			const text = await res.text();
			vlog('fetch_with_cfg:body', `raw body attempt ${i}`, { bytes: text.length, preview: trunc(redact(text), 800), duration_total_ms: Date.now()-attempt_t0 });
			let json: any = null; try { json = JSON.parse(text); vlog('fetch_with_cfg:json', `parsed json attempt ${i}`, { keys: Object.keys(json).slice(0,20), has_error: !!json.error, has_output: !!json.output, has_choices: !!json.choices }); } catch (e:any) { vlog('fetch_with_cfg:json_parse_fail', `not json attempt ${i}`, { err: e.message, preview: trunc(text,400) }); }
			if (!res.ok) {
				last = text.slice(0, 500);
				vlog('fetch_with_cfg:http_error', `non-ok status attempt ${i}`, { status: res.status, body_preview: trunc(last, 400) });
				if (i < 3 && (res.status === 429 || res.status >= 500)) {
					const wait = i*2000;
					vlog('fetch_with_cfg:retry', `retryable status, waiting ${wait}ms`, { status: res.status });
					await new Promise(r => setTimeout(r, wait));
					continue;
				}
				throw new Error(`LLM ${text.slice(0, 800)} (model=${cfg.model})`);
			}
			const out = text_of(cfg, json);
			vlog('fetch_with_cfg:success', `extracted text attempt ${i}`, { out_len: out.length, preview: trunc(out, 500), attempt_duration_ms: Date.now()-attempt_t0 });
			if (!out) throw new Error(`empty LLM response: ${JSON.stringify(json).slice(0, 400)}`);
			record_usage(json);
			return out;
		} catch (e: any) {
			last = e.message || String(e);
			vlog('fetch_with_cfg:catch', `attempt ${i} failed`, { err: last, stack: trunc(e.stack||'', 600), duration_ms: Date.now()-attempt_t0 });
			if (i < 3) {
				const wait = i*2000;
				vlog('fetch_with_cfg:retry_wait', `waiting ${wait}ms before next attempt`, { next_attempt: i+1 });
				await new Promise(r => setTimeout(r, wait));
			} else {
				vlog('fetch_with_cfg:exhausted', `all 3 attempts failed`, { last_err: last });
				throw new Error(last);
			}
		}
		finally { clearTimeout(t); }
	}
	throw new Error(last);
}
async function llm_chain(prompt: string, isChat: boolean, where: string): Promise<string> {
	if (!CFG) die('no model cfg');
	vlog('llm_chain:start', `llm`, { where, isChat, model: CFG.model, reasoning: CFG.reasoning || 'off' });
	const out = await fetch_with_cfg(CFG, prompt, isChat);
	vlog('llm_chain:success', `model succeeded`, { model: CFG.model, out_len: out.length });
	return out;
}
async function llm(prompt: string): Promise<string> {
	vlog('llm:start', `llm() called`, { prompt_len: prompt.length, preview: trunc(prompt, 600) });
	const out = await llm_chain(prompt, false, 'llm');
	vlog('llm:success', `llm done`, { out_len: out.length, preview: trunc(out, 400) });
	return out;
}
async function llm_think(messages: { role: string; content: string }[]): Promise<string> {
	const prompt = messages.map(m => m.content).join('\n\n');
	vlog('llm_think:start', `llm_think() called`, { messages: messages.length, prompt_len: prompt.length, preview: trunc(prompt, 600) });
	const out = await llm_chain(prompt, true, 'llm_think');
	vlog('llm_think:success', `llm_think done`, { out_len: out.length });
	return out;
}

// --- thinking helpers (dynamic count — model decides how many angles) ---
function think_prompt(preamble: string | null, leaf_s: string): string {
	const p = `Think extremely deeply about this ONE angle. Do not look at prior conclusions.\n\nGlobal context:\n${preamble || '(none)'}\n\nAngle:\n${leaf_s}\n\nFrom first principles. Steelman both sides. Look for contradictions. Prefer concrete.\nGenerate as many atomic conclusions as this angle warrants — cover every distinct facet, contradiction, and implication thoroughly. Do not artificially limit yourself; produce as many high-quality bullets as needed for complete coverage.\nOutput ONLY markdown bullets: "- <sentence>"`;
	vlog('think_prompt', `built think prompt`, { preamble_len: preamble?.length||0, leaf_len: leaf_s.length, total_len: p.length, leaf_preview: trunc(leaf_s,200) });
	return p;
}
function parse_bullets(raw: string): string[] {
	vlog('parse_bullets:start', `parsing bullets`, { raw_len: raw.length, preview: trunc(raw,400) });
	const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
	const bullets = lines.filter(l => /^[-*•]\s+/.test(l)).map(l => l.replace(/^[-*•]\s+/, '').trim()).filter(Boolean);
	vlog('parse_bullets', `regex match`, { lines: lines.length, bullets_matched: bullets.length });
	if (bullets.length) {
		const res = bullets.map(b => `- ${b}`);
		vlog('parse_bullets:done', `returning bullets`, { count: res.length, preview: trunc(res.slice(0,3).join(' | '), 300) });
		return res;
	}
	const fallback = lines.filter(l => l.length > 10).map(l => (l.startsWith('-') ? l : `- ${l}`));
	vlog('parse_bullets:fallback', `no bullet markers, fallback`, { fallback_count: fallback.length });
	return fallback;
}
function norm_key(b: string): string { return b.toLowerCase().replace(/^[-*•]\s+/, '').replace(/[^a-z0-9]+/g, ' ').trim(); }
function append_dedup(existing: string, neu: string[]): string {
	vlog('append_dedup:start', `dedup merge`, { existing_lines: existing.split('\n').length, existing_bullets: (existing.match(/^- /gm)||[]).length, new_count: neu.length });
	const have = new Set(existing.split('\n').filter(s => s.trim().startsWith('-')).map(norm_key));
	const add = neu.filter(b => { const k = norm_key(b); if (!k || have.has(k)) return false; have.add(k); return true; });
	vlog('append_dedup', `dedup result`, { have_before: have.size - add.length, added: add.length, duplicates_skipped: neu.length - add.length });
	const head = existing.trim();
	return (head ? head + '\n' : '') + (add.length ? add.join('\n') + '\n' : head ? '\n' : '');
}
async function genPreAngles(q: string): Promise<string[]> {
	vlog('genPreAngles:start', `generating dynamic pre angles via LLM`, { q: trunc(q,200) });
	const prompt = `You are planning deep research on: "${q}"

Generate as many distinct thinking angles as needed to holistically cover this topic from every important perspective. Generate as many as the topic warrants for complete coverage, always be thorough. Each angle should be a distinct lens that would produce non-overlapping insights. Cover definitions, evidence for/against, mechanisms, history, economics, technical details, alternatives, risks, controversies, methods, applications, future directions, and anything else relevant.

Return ONLY JSON array of strings: ["angle 1", "angle 2", ...]`;
	try {
		const raw = await llm(prompt);
		const m = raw.match(/\[[\s\S]*\]/);
		if (m) {
			const arr = JSON.parse(m[0]);
			if (Array.isArray(arr) && arr.length) {
				const cleaned = arr.map((s:any)=>String(s).trim()).filter(Boolean);
				vlog('genPreAngles:llm', `LLM generated`, { count: cleaned.length });
				if (cleaned.length) return cleaned;
			}
		}
	} catch (e:any) { vlog('genPreAngles:fail', `LLM gen failed, fallback`, { err: e.message }); }
	// fallback: return full diverse set (not sliced to 9)
	vlog('genPreAngles:fallback', `using fallback bases`);
	const bases = [
		`${q}`,
		`core definitions and first principles of ${q}`,
		`evidence for: ${q}`,
		`evidence against: ${q}`,
		`peer-reviewed studies on ${q}`,
		`statistics and numbers: ${q}`,
		`history and timeline of ${q}`,
		`who benefits from ${q} vs who is harmed`,
		`common mistakes and misconceptions about ${q}`,
		`adjacent fields to ${q}`,
		`contrarian view: ${q} is wrong`,
		`limits and failure modes of ${q}`,
		`costs, pricing, economics of ${q}`,
		`legal and regulatory aspects of ${q}`,
		`technical implementation details of ${q}`,
		`alternative approaches to ${q}`,
		`geographic variation in ${q}`,
		`demographic differences in ${q}`,
		`long-term vs short-term effects of ${q}`,
		`risks and safety of ${q}`,
		`case studies exemplifying ${q}`,
		`measurement methods for ${q}`,
		`controversies and debates around ${q}`,
		`future directions for ${q}`,
		`practical how-to for ${q}`,
		`comparison: ${q} vs closest alternatives`,
		`underlying mechanisms of ${q}`,
		`ethical considerations of ${q}`,
		`popular coverage vs scholarly coverage of ${q}`,
		`sources and where to search for ${q}`,
		`seminal papers that defined ${q}`,
		`recent 2024-2025 developments in ${q}`,
		`open questions and unknowns about ${q}`,
		`tools and methods used to study ${q}`,
		`funding and incentives shaping ${q}`,
		`data sources for ${q}`,
		`search keywords for ${q}`,
		`primary sources to verify ${q}`,
		`secondary sources summarizing ${q}`,
		`what a skeptic would ask about ${q}`,
		`what a practitioner needs to know about ${q}`,
		`what a beginner misunderstands about ${q}`,
		`what experts disagree on regarding ${q}`,
		`quantitative models for ${q}`,
		`qualitative insights about ${q}`,
		`real-world applications of ${q}`,
		`failed attempts related to ${q}`,
		`successful deployments of ${q}`,
		`infrastructure needed for ${q}`,
		`dependencies and prerequisites for ${q}`,
		`second-order effects of ${q}`,
		`interaction of ${q} with other systems`,
		`how to falsify claims about ${q}`,
		`confidence intervals and uncertainty in ${q}`,
	];
	const out = bases;
	vlog('genPreAngles:done', `fallback generated`, { count: out.length });
	return out;
}
// keep old name as alias for compat
function gen9PreAngles(q: string): string[] { vlog('gen9PreAngles:compat', `compat shim called`); return []; }
async function genPostAngles(q: string, excerpt: string): Promise<string[]> {
	vlog('genPostAngles:start', `generating dynamic post angles via LLM`, { q: trunc(q,150), excerpt_len: excerpt.length });
	const ctx = excerpt.slice(0, 8000);
	const prompt = `You have just finished web research on: "${q}"

Gathered excerpt:\n${ctx.slice(0,6000)}

Generate as many distinct synthesis angles as needed to holistically synthesize and critique the findings. Generate as many as warranted for complete, rigorous synthesis. Cover agreement vs contradiction, strongest evidence for/against, numbers that held/failed, unknowns, misconceptions corrected, practical implications, bias assessment, primary source quality, gaps, contrarian takes still standing, confidence levels, alternative explanations, failure modes, and actionable takeaways.

Return ONLY JSON array of strings: ["angle 1", "angle 2", ...]`;
	try {
		const raw = await llm(prompt);
		const m = raw.match(/\[[\s\S]*\]/);
		if (m) {
			const arr = JSON.parse(m[0]);
			if (Array.isArray(arr) && arr.length) {
				const cleaned = arr.map((s:any)=>String(s).trim()).filter(Boolean);
				vlog('genPostAngles:llm', `LLM generated`, { count: cleaned.length });
				if (cleaned.length) return cleaned;
			}
		}
	} catch (e:any) { vlog('genPostAngles:fail', `LLM gen failed, fallback`, { err: e.message }); }
	vlog('genPostAngles:fallback', `using fallback bases`);
	const bases = [
		`synthesize overall answer to: ${q} — given:\n${ctx}`,
		`strongest evidence for ${q} from gathered sources`,
		`strongest evidence against ${q}`,
		`where sources agree vs contradict on ${q}`,
		`numbers that held up under scrutiny for ${q}`,
		`numbers that failed verification for ${q}`,
		`what remains unknown about ${q} after search`,
		`common misconceptions about ${q} corrected by sources`,
		`practical implications of ${q}`,
		`who benefits narrative vs data for ${q}`,
		`historical context synthesis for ${q}`,
		`technical nuance that changes meaning of ${q}`,
		`limits of current evidence on ${q}`,
		`bias assessment across sources for ${q}`,
		`primary source quality for ${q}`,
		`gaps where more research needed on ${q}`,
		`contrarian take still standing for ${q}`,
		`consensus view that emerged for ${q}`,
		`risk assessment synthesis for ${q}`,
		`what a decision-maker should do about ${q}`,
		`timeline implications for ${q}`,
		`second-order effects synthesis for ${q}`,
		`confidence level we should assign to each claim about ${q}`,
		`alternative explanations that fit data on ${q}`,
		`most cited sources and their credibility for ${q}`,
		`geographic or cultural caveats for ${q}`,
		`how this answer could be wrong for ${q}`,
		`what would change the conclusion about ${q}`,
		`actionable next steps from ${q}`,
		`simplest story that fits all evidence on ${q}`,
		`most surprising finding about ${q}`,
		`most contested claim about ${q}`,
		`how to explain ${q} to a non-expert`,
		`how to explain ${q} to an expert`,
		`what data would settle remaining debate on ${q}`,
		`replication status of key studies on ${q}`,
		`causal vs correlational claims about ${q}`,
		`definitions that matter for ${q}`,
		`measurement caveats for ${q}`,
		`comparative perspective: ${q} elsewhere`,
		`ethical synthesis for ${q}`,
		`long-term outlook for ${q}`,
		`short-term outlook for ${q}`,
		`interaction with adjacent fields: ${q}`,
		`failure modes that still apply to ${q}`,
		`success metrics for ${q}`,
		`infrastructure or cost synthesis for ${q}`,
		`dependency chain behind ${q}`,
		`final verdict on ${q} with calibrated uncertainty`,
		`open threads to keep watching on ${q}`,
		`what we would ask next about ${q}`,
		`how to verify this synthesis for ${q}`,
		`summary bullets that survive strict scrutiny for ${q}`,
		`key quotes that anchor the synthesis for ${q}`,
	];
	const out = bases;
	vlog('genPostAngles:done', `fallback generated`, { count: out.length });
	return out;
}
function gen9PostAngles(q: string, excerpt: string): string[] { vlog('gen9PostAngles:compat', `compat shim`); return []; }

async function run_thinking_phase(slug: string, question: string, phase: 'pre' | 'post', angles: string[], wd: string, state: any) {
	const t0 = Date.now();
	vlog('run_thinking_phase:start', `phase=${phase} slug=${slug} angles=${angles.length}`, { question: trunc(question,200), wd, state_keys: Object.keys(state) });
	const label = phase;
	const thinkFile = resolve(THINK, `${slug}-research-${label}.r`);
	const concFile = resolve(THINK, `${slug}-research-${label}.conclusions.md`);
	const finalMd = resolve(THINK, `${slug}-research-${label}.md`);
	vlog('run_thinking_phase:paths', `resolved paths`, { thinkFile, concFile, finalMd, think_exists: existsSync(thinkFile), conc_exists: existsSync(concFile) });
	mkdirSync(THINK, { recursive: true });
	// init tree if needed
	if (!existsSync(thinkFile)) {
		vlog('run_thinking_phase:init', `initializing think tree`, { label, angles: angles.length });
		const tree: any = { _: question };
		angles.forEach((s, i) => { tree[`a${String(i+1).padStart(2,'0')}`] = { s, d: 0 }; });
		write_atomic(thinkFile, JSON.stringify(tree, null, '\t')+'\n');
		console.log(`think init ${label}: ${thinkFile} (${angles.length} leaves)`);
		vlog('run_thinking_phase:init_done', `tree written`, { thinkFile, leaves: angles.length });
	} else {
		vlog('run_thinking_phase:exists', `think file exists, loading`, { thinkFile, bytes: statSync(thinkFile).size });
	}
	// load and iterate
	const loadTree = (): { preamble: string | null, tree: any } => {
		const raw = readFileSync(thinkFile,'utf8');
		vlog('loadTree', `reading think file`, { bytes: raw.length, preview: trunc(raw,400) });
		const j = JSON.parse(raw);
		const pre = typeof j._ === 'string' ? j._ : null; delete j._;
		vlog('loadTree', `parsed`, { preamble_len: pre?.length||0, leaves: Object.keys(j).length });
		return { preamble: pre, tree: j };
	};
	const saveTree = (pre: string | null, tree: any) => {
		vlog('saveTree', `saving tree`, { preamble_len: pre?.length||0, leaves: Object.keys(tree).length });
		const body:any = pre===null?{}:{_:pre}; Object.assign(body,tree); write_atomic(thinkFile, JSON.stringify(body,null,'\t')+'\n');
	};
	let doneLeaves = new Set<string>((state[`done_think_${label}`] as string[]) || []);
	vlog('run_thinking_phase:doneLeaves', `initial doneLeaves`, { from_state: (state[`done_think_${label}`]||[]).length, set_size: doneLeaves.size });
	// also parse existing conclusions file for done markers
	if (existsSync(concFile)) {
		const c = readFileSync(concFile,'utf8');
		vlog('run_thinking_phase:concFile', `existing conc file`, { bytes: c.length, bullets: (c.match(/^- /gm)||[]).length });
		for (const m of c.matchAll(/<!-- done: (.+) -->/g)) doneLeaves.add(m[1]);
		vlog('run_thinking_phase:concFile_done', `after scanning conc file`, { doneLeaves: doneLeaves.size });
	}
	console.log(`\n=== thinking ${label} (${angles.length} steps) ===`);
	vlog('run_thinking_phase:loop_start', `starting loop`, { angles: angles.length, already_done: doneLeaves.size });
	for (let idx=0; idx<angles.length; idx++) {
		const id = `a${String(idx+1).padStart(2,'0')}`;
		if (doneLeaves.has(id)) { vlog('run_thinking_phase:skip', `skip ${id} already done`); console.log(`  skip think ${label} ${id}`); continue; }
		const { preamble, tree } = loadTree();
		const node = tree[id];
		vlog('run_thinking_phase:node', `processing ${id}`, { s: trunc(node?.s||'',200), d: node?.d, idx: idx+1 });
		if (!node) { vlog('run_thinking_phase:no_node', `no node for ${id}`); continue; }
		if (node.d === 1) { vlog('run_thinking_phase:node_done', `node already marked done`); doneLeaves.add(id); continue; }
		console.log(`\n── think ${label} ${idx+1}/${angles.length} ${id} ──`);
		console.log(`s: ${node.s.slice(0,140)}${node.s.length>140?'…':''}`);
		const think_t0 = Date.now();
		const raw = await llm_think([{ role:'user', content: think_prompt(preamble, node.s)}]);
		vlog('run_thinking_phase:llm_done', `llm_think returned for ${id}`, { duration_ms: Date.now()-think_t0, raw_len: raw.length, preview: trunc(raw,500) });
		const bullets = parse_bullets(raw);
		vlog('run_thinking_phase:bullets', `parsed bullets for ${id}`, { count: bullets.length, bullets: bullets.slice(0,5) });
		if (!bullets.length) { console.error(`no bullets from ${id}, raw: ${raw.slice(0,200)}`); vlog('run_thinking_phase:no_bullets', `no bullets`, { raw_preview: trunc(raw,400) }); continue; }
		bullets.forEach(b=>console.log(`    ${b}`));
		const existing = existsSync(concFile) ? readFileSync(concFile,'utf8') : '';
		vlog('run_thinking_phase:merge', `merging bullets`, { existing_bytes: existing.length, new_bullets: bullets.length });
		const merged = append_dedup(existing, bullets) + `<!-- done: ${id} -->\n`;
		write_atomic(concFile, merged);
		vlog('run_thinking_phase:wrote_conc', `wrote conc`, { concFile, bytes: merged.length, bullets_total: (merged.match(/^- /gm)||[]).length });
		node.d=1; saveTree(preamble, tree);
		doneLeaves.add(id);
		state[`done_think_${label}`] = [...doneLeaves];
		write_atomic(resolve(wd,'state.json'), JSON.stringify(state,null,'\t')+'\n');
		vlog('run_thinking_phase:state_saved', `state updated`, { done_think: state[`done_think_${label}`].length });
	}
	// finalize md
	if (existsSync(concFile)) {
		const body = readFileSync(concFile,'utf8');
		vlog('run_thinking_phase:finalize', `finalizing md`, { conc_bytes: body.length, bullets: (body.match(/^- /gm)||[]).length });
		write_atomic(finalMd, `# ${slug} think ${label}\n\n` + body.replace(/^<!-- done: .+ -->\n/gm,''));
		console.log(`think ${label} → ${finalMd} (${(body.match(/^- /gm)||[]).length} bullets)`);
		vlog('run_thinking_phase:finalize_done', `final md written`, { finalMd, duration_total_ms: Date.now()-t0 });
	}
	const ret = existsSync(concFile) ? readFileSync(concFile,'utf8') : '';
	vlog('run_thinking_phase:return', `phase ${label} complete`, { ret_bytes: ret.length, duration_ms: Date.now()-t0 });
	return ret;
}

async function extract_search_queries(preThinkText: string, question: string): Promise<string[]> {
	const t0 = Date.now();
	vlog('extract_search_queries:start', `deriving queries`, { question: trunc(question,200), preThink_chars: preThinkText.length, preThink_preview: trunc(preThinkText, 500) });
	const prompt = `From the following pre-thinking about question, extract distinct web search queries that together cover the whole question. No duplicates. Output JSON array of strings only.\n\nQuestion: ${question}\n\nPre-thinking:\n${preThinkText.slice(0,24000)}\n\nReturn ONLY JSON: ["query1","query2",...]`;
	vlog('extract_search_queries:prompt', `prompt built`, { prompt_len: prompt.length, preview: trunc(prompt,600) });
	const raw = await llm(prompt);
	vlog('extract_search_queries:raw', `llm returned`, { raw_len: raw.length, preview: trunc(raw,600), duration_ms: Date.now()-t0 });
	const m = raw.match(/\[[\s\S]*\]/);
	if (!m) { vlog('extract_search_queries:no_match', `no JSON array found, fallback to [question]`); return [question]; }
	vlog('extract_search_queries:match', `found JSON array`, { match_len: m[0].length, preview: trunc(m[0],400) });
	try { const arr = JSON.parse(m[0]); vlog('extract_search_queries:parsed', `parsed array`, { count: arr.length, arr }); if (Array.isArray(arr) && arr.length) return arr.map((s:any)=>String(s).trim()).filter(Boolean); } catch (e:any) { vlog('extract_search_queries:parse_fail', `json parse fail`, { err: e.message }); }
	return [question];
}

function parse_hits(raw: string): Hit[] {
	vlog('parse_hits:start', `parsing search hits`, { raw_len: raw.length, preview: trunc(raw,600) });
	let d:any; try{ d=JSON.parse(raw);} catch (e:any){ vlog('parse_hits:json_fail', `json parse fail`, { err: e.message }); return [];}
	const rows = Array.isArray(d) ? d : d.results || d.data?.web || d.data?.results || d.web || (Array.isArray(d.data)?d.data:[]);
	vlog('parse_hits:rows', `rows extracted`, { is_array: Array.isArray(rows), count: Array.isArray(rows)?rows.length:'n/a', keys: d?Object.keys(d).slice(0,10):null });
	if (!Array.isArray(rows)) { vlog('parse_hits:no_rows', `rows not array`); return []; }
	const out: Hit[]=[]; for (const r of rows){ const url=r.url||r.link||''; if(!url.startsWith('http')) { vlog('parse_hits:skip', `skip non-http url`, { url: trunc(url,100) }); continue; } const excerpts=Array.isArray(r.excerpts)?r.excerpts.join('\n'):r.excerpt||r.description||r.snippet||''; out.push({url, title:r.title||url, excerpt:String(excerpts)});}
	vlog('parse_hits:done', `parsed hits`, { count: out.length, urls: out.slice(0,3).map(h=>h.url) });
	return out;
}
function search_angle(angle: string, dest: string): Hit[] {
	vlog('search_angle:start', `search_angle`, { angle: trunc(angle,200), dest });
	const t0 = Date.now();
	const r=sh('firecrawl',['search',angle,'--limit','8','--json','-o',dest],90000);
	vlog('search_angle:sh_done', `firecrawl search done`, { ok: r.ok, duration_ms: Date.now()-t0, dest_exists: existsSync(dest), dest_bytes: existsSync(dest)?statSync(dest).size:0 });
	if(!existsSync(dest)){ console.error(`  ! search failed: ${r.err.slice(0,200)||r.out.slice(0,200)}`); vlog('search_angle:fail', `no dest file`, { err: trunc(r.err,400), out: trunc(r.out,400) }); return [];}
	const raw = readFileSync(dest,'utf8');
	vlog('search_angle:raw', `read dest`, { bytes: raw.length, preview: trunc(raw,500) });
	const hits = parse_hits(raw);
	vlog('search_angle:done', `hits`, { count: hits.length, duration_ms: Date.now()-t0 });
	return hits;
}
function scrape(url: string, dest: string): string {
	vlog('scrape:start', `scrape`, { url, dest });
	const t0 = Date.now();
	const r=sh('firecrawl',['scrape',url,'-o',dest],90000);
	vlog('scrape:sh_done', `firecrawl scrape done`, { ok: r.ok, duration_ms: Date.now()-t0, dest_exists: existsSync(dest) });
	if(!existsSync(dest)){ console.error(`  ! scrape failed ${url}: ${r.err.slice(0,160)}`); vlog('scrape:fail', `no dest`, { err: trunc(r.err,300) }); return '';}
	const raw = readFileSync(dest,'utf8');
	vlog('scrape:read', `read scraped file`, { bytes: raw.length, preview: trunc(raw,500), duration_ms: Date.now()-t0 });
	return raw;
}
function extract_prompt(url: string, page: string): string {
	const p = `Extract quote-anchored claims from this ONE page. Invent nothing.\nReturn ONLY JSON, no markdown fence:\n{"source_url":"${url}","claims":[{"claim":"atomic sentence with scope","quote":"verbatim ≤40 words from the page","cited_primary":null}]}\nRules: quote verbatim from the page; every number/date in claim must sit in quote; one number per claim; one idea per claim; empty claims array is valid.\n\nPAGE:\n${page.slice(0,24000)}`;
	vlog('extract_prompt', `built extract prompt`, { url, page_len: page.length, prompt_len: p.length, preview: trunc(p,400) });
	return p;
}
function parse_extract(raw: string, url: string): Claim[] {
	vlog('parse_extract:start', `parsing extract`, { url, raw_len: raw.length, preview: trunc(raw,600) });
	const m=raw.match(/\{[\s\S]*\}/); if(!m) { vlog('parse_extract:no_match', `no json object found`); return []; }
	vlog('parse_extract:match', `found json`, { match_len: m[0].length, preview: trunc(m[0],400) });
	try{ const d=JSON.parse(m[0]); const claims=Array.isArray(d.claims)?d.claims:[]; vlog('parse_extract:claims_raw', `raw claims`, { count: claims.length }); const out = claims.filter((c:any)=>c&&typeof c.claim==='string'&&typeof c.quote==='string').map((c:any)=>({claim:c.claim.trim(),quote:c.quote.trim(),cited_primary:c.cited_primary||null,source_url:d.source_url||url})); vlog('parse_extract:done', `filtered claims`, { count: out.length, claims: out.slice(0,2) }); return out; }catch (e:any){ vlog('parse_extract:parse_fail', `json parse fail`, { err: e.message }); return [];}
}
function cnd(args: string[]) {
	const t0 = Date.now();
	const isTs = CND.endsWith('.ts');
	const bin = isTs ? 'bun' : 'python3';
	vlog('cnd:start', `cnd invocation`, { args, cnd_path: CND, full_cmd: `${bin} ${CND} ${args.join(' ')}` });
	let r = sh(bin,[CND,...args],30000);
	if (!r.ok && isTs && bin==='bun') { vlog('cnd:fallback', `bun failed (${trunc(r.err,200)}), trying npx tsx`); const r2 = sh('npx',['--yes','tsx',CND,...args],30000); if (r2.ok) r = r2; else { vlog('cnd:fallback', `npx tsx also failed: ${trunc(r2.err,200)}`); if (!r2.ok && existsSync(CND_PY)) { vlog('cnd:fallback', `trying python ${CND_PY}`); const r3 = sh('python3',[CND_PY,...args],30000); if (r3.ok) r = r3; else r = r2; } else if (!r2.ok) r = r2; } }
	else if (!r.ok && isTs && existsSync(CND_PY)) { vlog('cnd:fallback', `ts failed, trying python ${CND_PY}`); const r3 = sh('python3',[CND_PY,...args],30000); if (r3.ok) r = r3; }
	vlog('cnd:done', `cnd result`, { ok: r.ok, duration_ms: Date.now()-t0, out_len: r.out.length, err_len: r.err.length, out_preview: trunc(r.out,400), err_preview: trunc(r.err,400) });
	if(!r.ok) { vlog('cnd:fail', `cnd failed`, { args, err: trunc(r.err,600), out: trunc(r.out,600) }); die(`cnd ${args[0]} failed: ${r.err||r.out}`.slice(0,400)); }
	return r.out;
}

async function run(question: string, slug: string, explicitAngles: string[]) {
	const run_t0 = Date.now();
	vlog('run:start', `run() entered`, { question: trunc(question,300), slug, explicitAngles: explicitAngles.length, explicit_preview: explicitAngles.slice(0,3).map(s=>trunc(s,100)) });
	const wd = resolve(ROOT, slug);
	vlog('run:wd', `wd resolved`, { wd, exists_before: existsSync(wd) });
	mkdirSync(wd,{recursive:true});
	VERBOSE_LOG_FILE = resolve(wd, 'verbose.log');
	vlog('run:verbose_log', `verbose log file`, { VERBOSE_LOG_FILE });
	try { appendFileSync(VERBOSE_LOG_FILE, `\n=== run ${ts()} ${elapsed()} slug=${slug} question=${trunc(question,120)} ===\n`); } catch {}
	const state_path = resolve(wd,'state.json');
	vlog('run:state_path', `state path`, { state_path, exists: existsSync(state_path) });
	let state:any = existsSync(state_path) ? JSON.parse(readFileSync(state_path,'utf8')) : { question, slug, done:[], phase:'pre' };
	vlog('run:state_loaded', `state loaded`, { state: jtrunc(state, 1500), bytes: existsSync(state_path)?statSync(state_path).size:0 });
	state.question = question; state.slug = slug;
	write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n');
	vlog('run:state_written', `state written after slug/question update`);
	if (!existsSync(resolve(wd,'meta.json'))) {
		vlog('run:meta_missing', `meta.json missing, cnd init`);
		cnd(['init', question,'--slug',slug,'--question',question]);
		vlog('run:meta_done', `cnd init done`, { meta_exists: existsSync(resolve(wd,'meta.json')) });
	} else {
		vlog('run:meta_exists', `meta.json exists`, { path: resolve(wd,'meta.json') });
	}

	console.log(`research: ${slug}`);
	vlog('run:model', `model`, { model: CFG?.model, reasoning: CFG?.reasoning || 'off' });
	console.log(`model: ${CFG?.model} reasoning=${CFG?.reasoning || 'off'}`);

	// PHASE 1: dynamic thinking pre (model decides count)
	let preText = '';
	if (!state.done.includes('phase:pre-think')) {
		vlog('run:pre_think_needed', `pre-think phase needed`);
		const preAngles = explicitAngles.length ? explicitAngles : await genPreAngles(question);
		vlog('run:pre_angles', `pre angles ready`, { count: preAngles.length, explicit: explicitAngles.length>=9 });
		preText = await run_thinking_phase(slug, question, 'pre', preAngles, wd, state);
		vlog('run:pre_think_done', `pre-think complete`, { preText_len: preText.length, duration_ms: Date.now()-run_t0 });
		state.done.push('phase:pre-think');
		write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n');
		vlog('run:state_after_pre', `state saved`, { done: state.done });
	} else {
		const concFile = resolve(THINK, `${slug}-research-pre.conclusions.md`);
		vlog('run:pre_think_skip', `skip pre-think, cached`, { concFile, exists: existsSync(concFile) });
		preText = existsSync(concFile) ? readFileSync(concFile,'utf8') : '';
		vlog('run:pre_think_cached', `cached preText`, { len: preText.length, preview: trunc(preText,300) });
		console.log(`skip pre-think, ${preText.length} chars cached`);
	}

	// Decide searches from thinking (unless user gave explicit angles)
	let angles: string[];
	if (explicitAngles.length) { angles = explicitAngles; console.log(`using explicit ${angles.length} angles`); vlog('run:angles_explicit', `using explicit`, { count: angles.length }); }
	else if (!state.angles || !state.angles.length) {
		console.log(`\n=== deriving search queries from pre-thinking ===`);
		vlog('run:derive_queries', `deriving queries from pre-thinking`, { preText_len: preText.length });
		angles = await extract_search_queries(preText, question);
		console.log(`derived ${angles.length} queries:`); angles.forEach((a,i)=>console.log(`  ${i+1}. ${a}`));
		vlog('run:derived_queries', `derived`, { count: angles.length, queries: angles });
		state.angles = angles;
		write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n');
	} else { angles = state.angles; console.log(`using cached ${angles.length} queries`); vlog('run:cached_angles', `cached angles`, { count: angles.length, queries: angles }); }

	// PHASE 2: search
	vlog('run:phase2_search', `starting search phase`, { angles: angles.length });
	const kept = new Map<string,Hit>();
	for(let i=0;i<angles.length;i++){
		const angle=angles[i]; const id=`a${String(i+1).padStart(2,'0')}`;
		vlog('run:search_loop', `search ${id} ${i+1}/${angles.length}`, { angle: trunc(angle,200), already_done: (state.done as string[]).includes('search:'+id) });
		if((state.done as string[]).includes('search:'+id)){ console.log(`  skip search ${id}`); vlog('run:search_skip', `skip ${id}`); continue; }
		console.log(`\n── search ${i+1}/${angles.length} ${id} ──`);
		console.log(`q: ${angle}`);
		const dest=resolve(wd,`search-${id}.json`);
		vlog('run:search_fire', `firecrawl search`, { dest, angle });
		const hits=search_angle(angle,dest);
		console.log(`  ${hits.length} hits`);
		vlog('run:search_hits', `hits for ${id}`, { count: hits.length, urls: hits.slice(0,3).map(h=>h.url) });
		for(const h of hits) if(!kept.has(h.url)) kept.set(h.url,h);
		vlog('run:kept_after', `kept size after ${id}`, { kept: kept.size });
		state.done.push('search:'+id);
		write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n');
	}
	vlog('run:search_reconcile', `reconciling kept with files on disk`);
	for(let i=0;i<angles.length;i++){
		const dest=resolve(wd,`search-a${String(i+1).padStart(2,'0')}.json`);
		const exists = existsSync(dest);
		vlog('run:reconcile', `checking ${dest}`, { exists });
		if(exists) {
			const raw = readFileSync(dest,'utf8');
			const hits = parse_hits(raw);
			vlog('run:reconcile_hits', `parsed`, { dest, count: hits.length });
			for(const h of hits) if(!kept.has(h.url)) kept.set(h.url,h);
		}
	}
	const urls=[...kept.values()];
	console.log(`\n${urls.length} unique urls`);
	vlog('run:urls', `unique urls collected`, { count: urls.length, sample: urls.slice(0,5).map(u=>u.url) });
	for(const h of urls){
		const pid=pid_of(h.url);
		vlog('run:page_loop', `page ${h.url}`, { pid, already_done: (state.done as string[]).includes('page:'+pid) });
		if((state.done as string[]).includes('page:'+pid)){ console.log(`  skip ${h.url}`); vlog('run:page_skip', `skip ${h.url}`); continue; }
		console.log(`\n── page ${h.url} ──`);
		const txt_path=resolve(wd,'pages',`${pid}.txt`);
		vlog('run:page_txt_path', `txt_path`, { txt_path, exists: existsSync(txt_path) });
		let text=existsSync(txt_path)?readFileSync(txt_path,'utf8'):'';
		vlog('run:page_text_cached', `cached text`, { len: text.length, exists: !!text });
		if(!text){ vlog('run:scrape_needed', `scraping ${h.url}`); const scraped=scrape(h.url, resolve(wd,`scrape-${pid}.md`)); text=scraped||h.excerpt||''; vlog('run:scrape_result', `scraped`, { scraped_len: scraped.length, excerpt_len: h.excerpt.length, final_len: text.length }); if(text) write_atomic(txt_path,text); }
		if(!text.trim()){ console.log('  empty, skip'); vlog('run:page_empty', `empty page skip`); state.done.push('page:'+pid); write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n'); continue; }
		vlog('run:cnd_add_source', `cnd add-source`, { url: h.url, title: trunc(h.title,100), txt_path });
		cnd(['add-source',slug,'--url',h.url,'--title',h.title,'--file',txt_path]);
		console.log('  → extract');
		vlog('run:extract_start', `extract claims for ${h.url}`, { text_len: text.length });
		const extract_t0 = Date.now();
		const raw= await llm(extract_prompt(h.url,text));
		vlog('run:extract_raw', `llm extract done`, { duration_ms: Date.now()-extract_t0, raw_len: raw.length, preview: trunc(raw,500) });
		const claims=parse_extract(raw,h.url);
		const ext=resolve(wd,'extracts',`${pid}.json`);
		vlog('run:extract_write', `writing extract`, { ext, claims: claims.length });
		write_atomic(ext, JSON.stringify({source_url:h.url,claims},null,'\t')+'\n');
		console.log(`  ← ${claims.length} claims`);
		vlog('run:page_done', `page done ${h.url}`, { claims: claims.length, duration_ms: Date.now()-extract_t0 });
		state.done.push('page:'+pid);
		write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n');
	}
	const extracts=urls.map(h=>resolve(wd,'extracts',`${pid_of(h.url)}.json`)).filter(existsSync);
	vlog('run:extracts_collected', `extracts on disk`, { count: extracts.length, expected: urls.length, extracts });
	if(!extracts.length) { vlog('run:no_extracts', `no extracts, dying`); die('incomplete — no extracts'); }
	vlog('run:cnd_ingest', `ingest-extract`, { count: extracts.length });
	cnd(['ingest-extract',slug,...extracts]);
	vlog('run:cnd_gate', `gate`);
	cnd(['gate',slug]);
	// before final write, do post thinking
	if (!state.done.includes('phase:post-think')) {
		vlog('run:post_think_needed', `post-think needed`);
		// gather excerpt for post angles: first 8k of extracts
		let excerpt = '';
		try{
			excerpt = extracts.slice(0,3).map(f=>readFileSync(f,'utf8').slice(0,2000)).join('\n').slice(0,8000);
			vlog('run:post_excerpt', `excerpt for post angles`, { excerpt_len: excerpt.length, preview: trunc(excerpt,400) });
		}catch (e:any){ vlog('run:post_excerpt_fail', `excerpt fail`, { err: e.message }); }
		const postAngles = await genPostAngles(question, excerpt);
		vlog('run:post_angles', `post angles`, { count: postAngles.length });
		await run_thinking_phase(slug, question, 'post', postAngles, wd, state);
		state.done.push('phase:post-think');
		write_atomic(state_path, JSON.stringify(state,null,'\t')+'\n');
		vlog('run:post_think_done', `post think done`);
		// append post conclusions to ledger? we will let cnd write then augment
	} else {
		vlog('run:post_think_skip', `skip post-think`);
	}
	vlog('run:cnd_write', `cnd write`, { slug, question: trunc(question,150) });
	cnd(['write',slug,'--question',question]);
	// augment final ledger with post-thinking synthesis if available
	const pub = resolve(ROOT, slug+'.md');
	const postConc = resolve(THINK, `${slug}-research-post.conclusions.md`);
	vlog('run:augment_check', `check augment`, { pub, pub_exists: existsSync(pub), postConc, post_exists: existsSync(postConc) });
	if (existsSync(pub) && existsSync(postConc)) {
		const ledger = readFileSync(pub,'utf8');
		const synth = readFileSync(postConc,'utf8').replace(/^<!-- done: .+ -->\n/gm,'').slice(0,12000);
		vlog('run:augment', `augmenting ledger`, { ledger_len: ledger.length, synth_len: synth.length });
		const augmented = ledger + `\n\n---\n\n## Post-search synthesis (dynamic-angle thinking)\n\n${synth}\n`;
		write_atomic(pub, augmented);
		console.log(`augmented ledger with post-thinking`);
		vlog('run:augmented', `ledger augmented`);
	}
	if(!existsSync(pub)) { vlog('run:no_pub', `no ledger at ${pub}`); die('incomplete — no ledger'); }
	console.log(`\nwrite → ${pub}`);
	console.log('0 — done');
	dump_usage();
	vlog('run:done', `run complete`, { pub, duration_total_ms: Date.now()-run_t0, duration_total_s: ((Date.now()-run_t0)/1000).toFixed(1) });
	if (VERBOSE_LOG_FILE) vlog('run:verbose_log_file', `verbose log at ${VERBOSE_LOG_FILE}`, { bytes: existsSync(VERBOSE_LOG_FILE)?statSync(VERBOSE_LOG_FILE).size:0 });
}

async function main(){
	const t0 = Date.now();
	vlog('main:start', `main entered`, { args: process.argv.slice(2), argc: process.argv.length });
	const args=process.argv.slice(2);
	if(!args.length||args.includes('-h')||args.includes('--help')){ console.log(`research "<question>" [--model provider/id] [--reasoning high] [--angle "s"]...\nresearch <slug>`); process.exit(0); }
	const angles:string[]=[]; const rest:string[]=[];
	let spec = process.env.RESEARCH_MODEL || 'openrouter/z-ai/glm-5.3-flash';
	let reasoning = process.env.RESEARCH_REASONING || '';
	vlog('main:parse_args', `parsing args`, { raw: args });
	for(let i=0;i<args.length;i++){ const a=args[i]; if(a==='--angle') { const val = args[++i]||die('--angle needs text'); angles.push(val); vlog('main:angle', `angle added`, { val: trunc(val,200), total: angles.length }); } else if(a==='--model') { spec = args[++i]||die('--model needs provider/id'); } else if(a==='--reasoning') { reasoning = args[++i]||die('--reasoning needs a level'); } else if(a==='--fast') { vlog('main:fast_ignored', `--fast ignored`); continue; } else if(a==='--verbose') { vlog('main:verbose_flag', `--verbose explicit`); continue; } else if(a==='--quiet' || a==='--no-verbose') { vlog('main:quiet_flag', `${a} explicit`); continue; } else rest.push(a); }
	CFG = make_cfg(spec, reasoning);
	vlog('main:parsed', `parsed`, { angles: angles.length, rest, rest_preview: rest.slice(0,3).map(s=>trunc(s,100)) });
	const first=rest[0]||die('need <question>');
	const maybe_n=rest[1]&&/^\d+$/.test(rest[1])?parseInt(rest[1],10):0;
	vlog('main:first', `first arg`, { first: trunc(first,200), maybe_n, rest_len: rest.length });
	// if maybe_n given, treat as legacy n -> generate that many but we override to 9 thinking, so ignore n except for compatibility
	if(maybe_n && !angles.length){ /* legacy: will be overridden by 9 think but keep for backward compat search length */ vlog('main:legacy_n', `legacy n=${maybe_n} ignored`); }
	const resume_dir=resolve(ROOT,first);
	vlog('main:resume_check', `checking resume`, { resume_dir, exists: existsSync(resume_dir), has_state: existsSync(resolve(resume_dir,'state.json')), has_meta: existsSync(resolve(resume_dir,'meta.json')) });
	const is_slug=existsSync(resolve(resume_dir,'state.json'))||existsSync(resolve(resume_dir,'meta.json'));
	vlog('main:is_slug', `is_slug=${is_slug}`);
	let question=first; let slug=slugify(first);
	vlog('main:slug_initial', `initial slug`, { slug, question: trunc(question,150) });
	if(is_slug && !maybe_n){ slug=first; const st_path = resolve(resume_dir,'state.json'); const st=existsSync(st_path)?JSON.parse(readFileSync(st_path,'utf8')):{}; vlog('main:resume_state', `resume state`, { st_path, exists: existsSync(st_path), state: jtrunc(st,1500) }); question=st.question||first; const saved:string[]=st.angles||[]; vlog('main:saved_angles', `saved angles`, { count: saved.length }); if(!angles.length&&saved.length) { angles.push(...saved); vlog('main:restored_angles', `restored saved angles`, { count: angles.length }); } }
	vlog('main:run_call', `calling run()`, { question: trunc(question,200), slug, angles: angles.length, elapsed_ms: Date.now()-t0 });
	await run(question,slug,angles);
	vlog('main:done', `main done`, { duration_ms: Date.now()-t0 });
}
main().catch(e=>{ dump_usage(); vlog('main:uncaught', `uncaught error`, { err: e.message, stack: trunc(e.stack||'',2000) }); console.error(e.stack||e.message); process.exit(1); });
