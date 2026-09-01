#!/usr/bin/env bun
// research "<question>" [--angle "..."] [--think] [--slug s] [--resume slug] [--verbose]
// phases: (opt think pre) -> search -> scrape+extract -> gate -> write -> (opt think post -> synthesis.md)
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync, readdirSync, appendFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, resolve } from 'node:path';

type Cfg = { baseUrl: string; apiKey: string; model: string; timeout: number; max_tokens: number; api: 'chat' | 'responses'; reasoning?: string };
type Hit = { url: string; title: string; excerpt: string };
type Claim = { claim: string; quote: string; cited_primary: string | null; source_url: string };
type State = {
	question: string;
	slug: string;
	done: string[];                // "search:a01" | "page:<pid>" | "phase:pre-think" | "phase:post-think" | "phase:search" | "phase:pages"
	angles?: string[];
	done_think_pre?: string[];
	done_think_post?: string[];
	phase?: string;
};

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
const ROOT = resolve(homedir(), 'search');
const THINK = resolve(homedir(), 'think');
const CND_TS = resolve(homedir(), '.agents/skills/condense-search/cnd.ts');
const CND_PY = resolve(homedir(), '.agents/skills/condense-search/cnd.py');
const CND = existsSync(CND_TS) ? CND_TS : CND_PY;

const CONCURRENCY = 5;
const MAX_ANGLES = 12;
const MAX_PRE_ANGLES = 10;
const MAX_POST_ANGLES = 10;
const VERBOSE = process.env.RESEARCH_VERBOSE === '1' || process.argv.includes('--verbose');
const QUIET = process.env.RESEARCH_QUIET === '1' || process.argv.includes('--quiet');

function log(msg: string) { if (VERBOSE && !QUIET) console.error(msg); }
function die(m: string): never { console.error(m); process.exit(1); }

// ——— utils ———
function slugify(s: string): string { return (s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'topic').slice(0, 64); }
function parse_model(raw: string): { provider: string; model: string } {
	const i = raw.indexOf('/');
	if (i < 1) die('model must be provider/id, e.g. openrouter/z-ai/glm-5.3-flash');
	return { provider: raw.slice(0, i), model: raw.slice(i + 1) };
}
function make_cfg(spec: string, reasoning: string): Cfg {
	const { provider, model } = parse_model(spec);
	const p = PROVIDERS[provider];
	if (!p) die(`unknown provider ${provider}. known: ${Object.keys(PROVIDERS).join(', ')}`);
	const apiKey = p.apiKey();
	if (!apiKey) die(`no api key for ${provider}`);
	return { baseUrl: p.baseUrl(), apiKey, model, timeout: 600000, max_tokens: 7000, api: 'chat', reasoning: reasoning || undefined };
}

// async spawn, not spawnSync
function sh(cmd: string, args: string[], timeoutMs = 90000): Promise<{ ok: boolean; out: string; err: string }> {
	return new Promise(res => {
		const child = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
		let out = '', err = '';
		let timed = false;
		const t = setTimeout(() => { timed = true; child.kill('SIGTERM'); }, timeoutMs);
		child.stdout.on('data', d => { out += d.toString(); if (out.length > 20 * 1024 * 1024) child.kill('SIGTERM'); });
		child.stderr.on('data', d => { err += d.toString(); });
		child.on('error', e => { clearTimeout(t); res({ ok: false, out, err: e.message }); });
		child.on('close', code => {
			clearTimeout(t);
			if (timed) res({ ok: false, out, err: err + ' timeout' });
			else res({ ok: code === 0, out, err });
		});
	});
}
function write_atomic(path: string, text: string) {
	mkdirSync(dirname(path), { recursive: true });
	const tmp = path + '.tmp';
	writeFileSync(tmp, text);
	renameSync(tmp, path);
}
function pid_of(url: string): string {
	const u = url.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');
	return createHash('sha1').update(u).digest('hex').slice(0, 16);
}

// ——— LLM ———
function text_of(cfg: Cfg, json: unknown): string {
	const j = json as Record<string, unknown>;
	if (cfg.api === 'responses') {
		if (typeof (j as { output_text?: unknown }).output_text === 'string' && ((j as { output_text: string }).output_text.trim())) return (j as { output_text: string }).output_text.trim();
		const parts: string[] = [];
		for (const item of ((j as { output?: unknown[] }).output || []) as Array<{ content?: Array<{ text?: string }> }>) for (const c of (item?.content || [])) if (typeof c?.text === 'string') parts.push(c.text);
		return parts.join('\n').trim();
	}
	const ch = (j as { choices?: Array<{ message?: { content?: unknown }; text?: unknown }> }).choices?.[0];
	const c = ch?.message?.content ?? ch?.text ?? '';
	if (typeof c === 'string') return c.trim();
	if (Array.isArray(c)) return (c as Array<{ text?: string; content?: string }>).map(x => x.text || x.content || '').join('\n').trim();
	return '';
}

async function fetch_with_cfg(cfg: Cfg, prompt: string, isChat: boolean): Promise<string> {
	const url = cfg.baseUrl + (cfg.api === 'responses' ? '/responses' : '/chat/completions');
	const body: Record<string, unknown> = cfg.api === 'responses'
		? { model: cfg.model, input: prompt, max_output_tokens: cfg.max_tokens }
		: { model: cfg.model, messages: [{ role: 'user', content: prompt }], max_tokens: cfg.max_tokens, temperature: isChat ? 0.7 : 0.2 };
	if (cfg.reasoning) (body as Record<string, unknown>).reasoning = { effort: cfg.reasoning };
	for (let i = 1; i <= 3; i++) {
		const ac = new AbortController();
		const t = setTimeout(() => ac.abort(), cfg.timeout);
		try {
			const res = await fetch(url, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${cfg.apiKey}`,
					'Content-Type': 'application/json',
					'HTTP-Referer': 'https://pi.dev',
					'X-OpenRouter-Title': 'pi',
				},
				body: JSON.stringify(body), signal: ac.signal
			});
			const text = await res.text();
			let json: unknown = null; try { json = JSON.parse(text); } catch {}
			if (!res.ok) {
				if (i < 3 && (res.status === 429 || res.status >= 500)) { await new Promise(r => setTimeout(r, i * 2000)); continue; }
				throw new Error(`LLM ${text.slice(0, 800)} (model=${cfg.model})`);
			}
			const out = text_of(cfg, json);
			if (!out) throw new Error(`empty LLM response: ${JSON.stringify(json).slice(0, 400)}`);
			return out;
		} catch (e: unknown) {
			const msg = (e as Error).message || String(e);
			if (i === 3) throw new Error(msg);
			await new Promise(r => setTimeout(r, i * 2000));
		} finally { clearTimeout(t); }
	}
	throw new Error('unreachable');
}
async function llm(prompt: string): Promise<string> {
	if (!CFG) die('no model cfg');
	return fetch_with_cfg(CFG, prompt, false);
}
async function llm_think(messages: { role: string; content: string }[]): Promise<string> {
	if (!CFG) die('no model cfg');
	return fetch_with_cfg(CFG, messages.map(m => m.content).join('\n\n'), true);
}

// ——— concurrency ———
function pLimit(n: number) {
	let active = 0;
	const q: Array<() => void> = [];
	const run = async <T>(fn: () => Promise<T>): Promise<T> => {
		if (active >= n) await new Promise<void>(res => q.push(res));
		active++;
		try { return await fn(); } finally { active--; const nxt = q.shift(); if (nxt) nxt(); }
	};
	return run;
}

// ——— thinking ———
function think_prompt(preamble: string | null, leaf_s: string): string {
	return `Think deeply about this ONE angle. Do not look at prior conclusions.\n\nGlobal context:\n${preamble || '(none)'}\n\nAngle:\n${leaf_s}\n\nSteelman both sides. Look for contradictions. Prefer concrete.\nOutput ONLY markdown bullets: "- <sentence>" (one idea per bullet)`;
}
function parse_bullets(raw: string): string[] {
	const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
	const bullets = lines.filter(l => /^[-*•]\s+/.test(l)).map(l => l.replace(/^[-*•]\s+/, '').trim()).filter(Boolean);
	if (bullets.length) return bullets.map(b => `- ${b}`);
	return lines.filter(l => l.length > 15 && !l.startsWith('{') && !l.startsWith('[')).map(l => (l.startsWith('-') ? l : `- ${l}`));
}
function norm_key(b: string): string { return b.toLowerCase().replace(/^[-*•]\s+/, '').replace(/[^a-z0-9]+/g, ' ').trim(); }
function append_dedup(existing: string, neu: string[]): string {
	const have = new Set(existing.split('\n').filter(s => s.trim().startsWith('-')).map(norm_key));
	const add = neu.filter(b => { const k = norm_key(b); if (!k || have.has(k)) return false; have.add(k); return true; });
	const head = existing.trim();
	return (head ? head + '\n' : '') + (add.length ? add.join('\n') + '\n' : head ? '\n' : '');
}

async function genPreAngles(q: string): Promise<string[]> {
	const prompt = `You are planning research on: "${q}"\nGenerate up to ${MAX_PRE_ANGLES} distinct thinking angles that together holistically cover this topic. Each angle is a distinct lens producing non-overlapping insights. Cover definitions, evidence for/against, mechanisms, history, economics, risks, alternatives, controversies, methods, applications.\nReturn ONLY JSON array of strings: ["angle 1", ...]`;
	try {
		const raw = await llm(prompt);
		const m = raw.match(/\[[\s\S]*\]/);
		if (m) {
			const arr = JSON.parse(m[0]) as unknown;
			if (Array.isArray(arr) && arr.length) {
				const cleaned = (arr as unknown[]).map(s => String(s).trim()).filter(Boolean).slice(0, MAX_PRE_ANGLES);
				if (cleaned.length) return cleaned;
			}
		}
	} catch {}
	return [
		`core definitions and first principles of ${q}`,
		`evidence for: ${q}`,
		`evidence against: ${q}`,
		`statistics and numbers: ${q}`,
		`history and timeline of ${q}`,
		`risks and failure modes of ${q}`,
		`costs and economics of ${q}`,
		`alternative approaches to ${q}`,
		`mechanisms underlying ${q}`,
		`open questions about ${q}`,
	].slice(0, MAX_PRE_ANGLES);
}

async function genPostAngles(q: string, excerpt: string): Promise<string[]> {
	const ctx = excerpt.slice(0, 8000);
	const prompt = `You have web research on: "${q}"\n\nExcerpt:\n${ctx.slice(0, 6000)}\n\nGenerate up to ${MAX_POST_ANGLES} distinct synthesis angles to critique findings. Cover agreement vs contradiction, strongest evidence for/against, numbers that held/failed, unknowns, bias, gaps, contrarian takes, confidence, actionable takeaways.\nReturn ONLY JSON array of strings: ["angle 1", ...]`;
	try {
		const raw = await llm(prompt);
		const m = raw.match(/\[[\s\S]*\]/);
		if (m) {
			const arr = JSON.parse(m[0]) as unknown;
			if (Array.isArray(arr) && arr.length) {
				const cleaned = (arr as unknown[]).map(s => String(s).trim()).filter(Boolean).slice(0, MAX_POST_ANGLES);
				if (cleaned.length) return cleaned;
			}
		}
	} catch {}
	return [
		`synthesize overall answer to: ${q} — given:\n${ctx.slice(0, 1500)}`,
		`strongest evidence for ${q} from gathered sources`,
		`strongest evidence against ${q}`,
		`where sources agree vs contradict on ${q}`,
		`numbers that held up under scrutiny for ${q}`,
		`what remains unknown about ${q} after search`,
		`practical implications of ${q}`,
		`bias and source quality for ${q}`,
		`gaps where more research needed on ${q}`,
		`confidence we should assign to claims about ${q}`,
	].slice(0, MAX_POST_ANGLES);
}

async function run_thinking_phase(slug: string, question: string, phase: 'pre' | 'post', angles: string[], wd: string, state: State): Promise<string> {
	const label = phase;
	const thinkFile = resolve(THINK, `${slug}-research-${label}.r`);
	const concFile = resolve(THINK, `${slug}-research-${label}.conclusions.md`);
	const finalMd = resolve(THINK, `${slug}-research-${label}.md`);
	mkdirSync(THINK, { recursive: true });

	if (!existsSync(thinkFile)) {
		const tree: Record<string, unknown> = { _: question };
		angles.forEach((s, i) => { tree[`a${String(i + 1).padStart(2, '0')}`] = { s, d: 0 }; });
		write_atomic(thinkFile, JSON.stringify(tree, null, '\t') + '\n');
		console.log(`think init ${label}: ${thinkFile} (${angles.length} leaves)`);
	}

	const loadTree = (): { preamble: string | null; tree: Record<string, { s: string; d: number }> } => {
		const j = JSON.parse(readFileSync(thinkFile, 'utf8')) as Record<string, unknown>;
		const pre = typeof j._ === 'string' ? (j._ as string) : null; delete j._;
		return { preamble: pre, tree: j as Record<string, { s: string; d: number }> };
	};
	const saveTree = (pre: string | null, tree: Record<string, { s: string; d: number }>) => {
		const body: Record<string, unknown> = pre === null ? {} : { _: pre }; Object.assign(body, tree);
		write_atomic(thinkFile, JSON.stringify(body, null, '\t') + '\n');
	};

	const doneKey = `done_think_${label}` as keyof State;
	let doneLeaves = new Set<string>((state[doneKey] as unknown as string[]) || []);
	if (existsSync(concFile)) {
		const c = readFileSync(concFile, 'utf8');
		for (const m of c.matchAll(/<!-- done: (.+) -->/g)) doneLeaves.add(m[1]);
	}

	console.log(`\n=== thinking ${label} (${angles.length} steps, concurrency ${CONCURRENCY}) ===`);

	const limit = pLimit(CONCURRENCY);
	const pending = angles.map((_, idx) => `a${String(idx + 1).padStart(2, '0')}`).filter(id => !doneLeaves.has(id));

	// fetch all in parallel, then merge sequentially to avoid races
	type Res = { id: string; bullets: string[]; raw: string };
	const results: Res[] = [];
	const errors: string[] = [];

	await Promise.all(pending.map(id => limit(async () => {
		const { preamble, tree } = loadTree();
		const node = tree[id];
		if (!node || node.d === 1) return;
		console.log(`  think ${label} ${id}: ${node.s.slice(0, 100)}…`);
		try {
			const raw = await llm_think([{ role: 'user', content: think_prompt(preamble, node.s) }]);
			const bullets = parse_bullets(raw);
			if (!bullets.length) { errors.push(`${id}: no bullets`); log(`${id} no bullets raw=${raw.slice(0,120)}`); return; }
			results.push({ id, bullets, raw });
		} catch (e: unknown) { errors.push(`${id}: ${(e as Error).message}`); }
	})));

	// merge in original order
	results.sort((a, b) => a.id.localeCompare(b.id));
	let existing = existsSync(concFile) ? readFileSync(concFile, 'utf8') : '';
	for (const r of results) {
		r.bullets.forEach(b => console.log(`    ${b}`));
		existing = append_dedup(existing, r.bullets) + `<!-- done: ${r.id} -->\n`;
		write_atomic(concFile, existing);
		const { preamble, tree } = loadTree();
		if (tree[r.id]) { tree[r.id].d = 1; saveTree(preamble, tree); }
		doneLeaves.add(r.id);
		(state[doneKey] as unknown as string[]) = [...doneLeaves];
		write_atomic(resolve(wd, 'state.json'), JSON.stringify(state, null, '\t') + '\n');
	}
	if (errors.length) errors.forEach(e => console.error(`  ! ${e}`));

	if (existsSync(concFile)) {
		const body = readFileSync(concFile, 'utf8');
		write_atomic(finalMd, `# ${slug} think ${label}\n\n` + body.replace(/^<!-- done: .+ -->\n/gm, ''));
		console.log(`think ${label} → ${finalMd} (${(body.match(/^- /gm) || []).length} bullets)`);
	}
	return existsSync(concFile) ? readFileSync(concFile, 'utf8') : '';
}

// ——— search helpers ———
async function extract_search_queries(preThinkText: string, question: string): Promise<string[]> {
	const prompt = `From pre-thinking about question, extract distinct web search queries covering the whole question. No duplicates. Output JSON array only.\n\nQuestion: ${question}\n\nPre-thinking:\n${preThinkText.slice(0, 24000)}\n\nReturn ONLY JSON: ["query1","query2",...]`;
	try {
		const raw = await llm(prompt);
		const m = raw.match(/\[[\s\S]*\]/);
		if (m) {
			const arr = JSON.parse(m[0]) as unknown;
			if (Array.isArray(arr) && arr.length) {
				const out = (arr as unknown[]).map(s => String(s).trim()).filter(Boolean).slice(0, MAX_ANGLES);
				if (out.length) return out;
			}
		}
	} catch {}
	return [question];
}

function parse_hits(raw: string): Hit[] {
	let d: unknown; try { d = JSON.parse(raw); } catch { return []; }
	const obj = d as Record<string, unknown>;
	const rows = Array.isArray(d) ? d as unknown[] : (obj.results as unknown[]) || (obj.data as Record<string, unknown>)?.web as unknown[] || (obj as Record<string, unknown>).web as unknown[] || [];
	if (!Array.isArray(rows)) return [];
	const out: Hit[] = [];
	for (const r of rows as Array<Record<string, unknown>>) {
		const url = String((r.url || r.link || '') as string);
		if (!url.startsWith('http')) continue;
		const excerpts = Array.isArray(r.excerpts) ? (r.excerpts as string[]).join('\n') : String((r.excerpt || r.description || r.snippet || '') as string);
		out.push({ url, title: String((r.title || url) as string), excerpt: String(excerpts) });
	}
	return out;
}
async function search_angle(angle: string, dest: string): Promise<Hit[]> {
	const r = await sh('firecrawl', ['search', angle, '--limit', '9', '--json', '-o', dest], 90000);
	if (!existsSync(dest)) { console.error(`  ! search failed: ${r.err.slice(0, 200) || r.out.slice(0, 200)}`); return []; }
	const raw = readFileSync(dest, 'utf8');
	return parse_hits(raw);
}
async function scrape_page(url: string, dest: string): Promise<string> {
	const r = await sh('firecrawl', ['scrape', url, '-o', dest], 90000);
	if (!existsSync(dest)) { console.error(`  ! scrape failed ${url}: ${r.err.slice(0, 160)}`); return ''; }
	return readFileSync(dest, 'utf8');
}
function extract_prompt(url: string, page: string): string {
	return `Extract quote-anchored claims from this ONE page. Invent nothing.\nReturn ONLY JSON, no markdown fence:\n{"source_url":"${url}","claims":[{"claim":"atomic sentence with scope","quote":"verbatim ≤40 words from the page","cited_primary":null}]}\nRules: quote verbatim from the page; every number/date in claim must sit in quote; one number per claim; one idea per claim; empty claims array is valid.\n\nPAGE:\n${page.slice(0, 24000)}`;
}
function parse_extract(raw: string, url: string): Claim[] {
	const m = raw.match(/\{[\s\S]*\}/); if (!m) return [];
	try {
		const d = JSON.parse(m[0]) as { claims?: Array<{ claim?: unknown; quote?: unknown; cited_primary?: unknown }>; source_url?: string };
		const claims = Array.isArray(d.claims) ? d.claims : [];
		return claims.filter(c => c && typeof c.claim === 'string' && typeof c.quote === 'string').map(c => ({
			claim: String(c.claim).trim(), quote: String(c.quote).trim(), cited_primary: (c.cited_primary as string) || null, source_url: d.source_url || url
		}));
	} catch { return []; }
}
async function cnd(args: string[]): Promise<string> {
	const isTs = CND.endsWith('.ts');
	const tries: Array<[string, string[]]> = isTs
		? [['bun', [CND, ...args]], ['npx', ['--yes', 'tsx', CND, ...args]]]
		: [['python3', [CND, ...args]]];
	if (isTs && existsSync(CND_PY)) tries.push(['python3', [CND_PY, ...args]]);
	let last = '';
	for (const [cmd, a] of tries) {
		const r = await sh(cmd, a, 30000);
		if (r.ok) return r.out;
		last = r.err || r.out;
	}
	die(`cnd ${args[0]} failed: ${last.slice(0, 400)}`);
}

// ——— main run ———
async function run(question: string, slug: string, explicitAngles: string[], enableThink: boolean) {
	const wd = resolve(ROOT, slug);
	mkdirSync(wd, { recursive: true });
	const state_path = resolve(wd, 'state.json');
	let state: State = existsSync(state_path) ? JSON.parse(readFileSync(state_path, 'utf8')) as State : { question, slug, done: [], phase: 'pre' };
	state.question = question; state.slug = slug;
	write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');

	if (!existsSync(resolve(wd, 'meta.json'))) {
		await cnd(['init', question, '--slug', slug, '--question', question]);
	}

	console.log(`research: ${slug}`);
	console.log(`model: ${CFG?.model} reasoning=${CFG?.reasoning || 'off'} think=${enableThink ? 'on' : 'off'}`);

	// PHASE 1: pre-think (optional)
	let preText = '';
	if (enableThink) {
		if (!state.done.includes('phase:pre-think')) {
			const preAngles = explicitAngles.length ? explicitAngles.slice(0, MAX_PRE_ANGLES) : await genPreAngles(question);
			preText = await run_thinking_phase(slug, question, 'pre', preAngles, wd, state);
			state.done.push('phase:pre-think');
			write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
		} else {
			const concFile = resolve(THINK, `${slug}-research-pre.conclusions.md`);
			preText = existsSync(concFile) ? readFileSync(concFile, 'utf8') : '';
			console.log(`skip pre-think, ${preText.length} chars cached`);
		}
	}

	// Decide search angles
	let angles: string[];
	if (explicitAngles.length) { angles = explicitAngles.slice(0, MAX_ANGLES); console.log(`using explicit ${angles.length} angles`); }
	else if (enableThink && preText) {
		if (!state.angles || !state.angles.length) {
			console.log(`\n=== deriving search queries from pre-thinking ===`);
			angles = await extract_search_queries(preText, question);
			console.log(`derived ${angles.length} queries:`); angles.forEach((a, i) => console.log(`  ${i + 1}. ${a}`));
			state.angles = angles;
			write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
		} else { angles = state.angles; console.log(`using cached ${angles.length} queries`); }
	} else if (state.angles?.length) { angles = state.angles; console.log(`using cached ${angles.length} angles`); }
	else {
		// no think: derive directly from question via LLM (1 call) or fallback to question
		console.log(`\n=== deriving search queries ===`);
		angles = await extract_search_queries('', question);
		if (angles.length === 1 && angles[0] === question) {
			// expand slightly: ask LLM for 5-8 variants
			const prompt = `Generate up to 8 distinct web search queries covering: "${question}". Return ONLY JSON array.`;
			try {
				const raw = await llm(prompt);
				const m = raw.match(/\[[\s\S]*\]/);
				if (m) {
					const arr = JSON.parse(m[0]) as unknown;
					if (Array.isArray(arr) && arr.length > 1) angles = (arr as unknown[]).map(s => String(s).trim()).filter(Boolean).slice(0, MAX_ANGLES);
				}
			} catch {}
		}
		console.log(`queries (${angles.length}):`); angles.forEach((a, i) => console.log(`  ${i + 1}. ${a}`));
		state.angles = angles;
		write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	}
	angles = angles.slice(0, MAX_ANGLES);

	// PHASE 2: search (parallel, concurrency 5)
	const kept = new Map<string, Hit>();
	const limit = pLimit(CONCURRENCY);
	const searchTasks = angles.map((angle, i) => ({ angle, id: `a${String(i + 1).padStart(2, '0')}` }));
	// run pending searches in parallel
	await Promise.all(searchTasks.map(({ angle, id }) => limit(async () => {
		if (state.done.includes('search:' + id)) { log(`skip search ${id}`); return; }
		console.log(`\n── search ${id} ── ${angle}`);
		const dest = resolve(wd, `search-${id}.json`);
		const hits = await search_angle(angle, dest);
		console.log(`  ${hits.length} hits`);
		for (const h of hits) if (!kept.has(h.url)) kept.set(h.url, h);
		state.done.push('search:' + id);
		write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	})));
	// reconcile all files on disk (covers resumed runs)
	for (let i = 0; i < angles.length; i++) {
		const dest = resolve(wd, `search-a${String(i + 1).padStart(2, '0')}.json`);
		if (existsSync(dest)) for (const h of parse_hits(readFileSync(dest, 'utf8'))) if (!kept.has(h.url)) kept.set(h.url, h);
	}
	const urls = [...kept.values()];
	console.log(`\n${urls.length} unique urls`);

	// PHASE 3: pages — scrape + extract (parallel, concurrency 5)
	const pageLimit = pLimit(CONCURRENCY);
	await Promise.all(urls.map(h => pageLimit(async () => {
		const pid = pid_of(h.url);
		if (state.done.includes('page:' + pid)) { log(`skip ${h.url}`); return; }
		console.log(`\n── page ${h.url} ──`);
		const txt_path = resolve(wd, 'pages', `${pid}.txt`);
		let text = existsSync(txt_path) ? readFileSync(txt_path, 'utf8') : '';
		if (!text) {
			const scraped = await scrape_page(h.url, resolve(wd, `scrape-${pid}.md`));
			text = scraped || h.excerpt || '';
			if (text) write_atomic(txt_path, text);
		}
		if (!text.trim()) {
			console.log('  empty, skip');
			state.done.push('page:' + pid);
			write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
			return;
		}
		await cnd(['add-source', slug, '--url', h.url, '--title', h.title, '--file', txt_path]);
		console.log('  → extract');
		const raw = await llm(extract_prompt(h.url, text));
		const claims = parse_extract(raw, h.url);
		const ext = resolve(wd, 'extracts', `${pid}.json`);
		write_atomic(ext, JSON.stringify({ source_url: h.url, claims }, null, '\t') + '\n');
		console.log(`  ← ${claims.length} claims`);
		state.done.push('page:' + pid);
		write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	})));

	const extracts = urls.map(h => resolve(wd, 'extracts', `${pid_of(h.url)}.json`)).filter(existsSync);
	if (!extracts.length) die('incomplete — no extracts');
	await cnd(['ingest-extract', slug, ...extracts]);
	await cnd(['gate', slug]);

	// PHASE 4: post-think → synthesis.md (separate, unverified) — only if --think
	if (enableThink) {
		if (!state.done.includes('phase:post-think')) {
			let excerpt = '';
			try { excerpt = extracts.slice(0, 3).map(f => readFileSync(f, 'utf8').slice(0, 2000)).join('\n').slice(0, 8000); } catch {}
			const postAngles = await genPostAngles(question, excerpt);
			await run_thinking_phase(slug, question, 'post', postAngles, wd, state);
			state.done.push('phase:post-think');
			write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
		}
		const postConc = resolve(THINK, `${slug}-research-post.conclusions.md`);
		if (existsSync(postConc)) {
			const synth = readFileSync(postConc, 'utf8').replace(/^<!-- done: .+ -->\n/gm, '').slice(0, 12000);
			const out = resolve(wd, 'synthesis.md');
			const banner = `> ⚠️ UNVERIFIED synthesis — not quote-gated. Read the ledger for audited claims.\n\n`;
			write_atomic(out, `# ${slug} synthesis (unverified)\n\n${banner}${synth}\n`);
			console.log(`synthesis → ${out} (UNVERIFIED, not appended to ledger)`);
		}
	}

	await cnd(['write', slug, '--question', question]);
	const pub = resolve(ROOT, slug + '.md');
	if (!existsSync(pub)) die('incomplete — no ledger');
	console.log(`\nwrite → ${pub}`);
	if (enableThink && existsSync(resolve(wd, 'synthesis.md'))) console.log(`synthesis → ${resolve(wd, 'synthesis.md')}`);
	console.log('0 — done');
}

async function main() {
	const args = process.argv.slice(2);
	if (!args.length || args.includes('-h') || args.includes('--help')) {
		console.log(`research "<question>" [--think] [--model provider/id] [--reasoning high] [--angle "q"] [--slug s] [--resume slug] [--verbose] [--quiet]\n  --think     enable pre/post thinking + synthesis.md (costly, gated ledger unchanged)\n  --resume s  resume existing slug\n  --slug s    force slug for new question`);
		process.exit(0);
	}
	const angles: string[] = [];
	let spec = process.env.RESEARCH_MODEL || 'openrouter/z-ai/glm-5.3-flash';
	let reasoning = process.env.RESEARCH_REASONING || '';
	let explicitSlug: string | null = null;
	let resumeSlug: string | null = null;
	let enableThink = false;
	const rest: string[] = [];
	for (let i = 0; i < args.length; i++) {
		const a = args[i];
		if (a === '--angle') { const v = args[++i]; if (!v) die('--angle needs text'); angles.push(v); }
		else if (a === '--model') { spec = args[++i] || die('--model needs provider/id'); }
		else if (a === '--reasoning') { reasoning = args[++i] || die('--reasoning needs a level'); }
		else if (a === '--think') { enableThink = true; }
		else if (a === '--slug') { explicitSlug = args[++i] || die('--slug needs value'); }
		else if (a === '--resume') { resumeSlug = args[++i] || die('--resume needs slug'); }
		else if (a === '--verbose' || a === '--quiet' || a === '--no-verbose') { /* handled via env/VERBOSE */ }
		else if (a === '--fast') { /* ignored, compat */ }
		else if (a.startsWith('--')) { die(`unknown flag ${a}`); }
		else rest.push(a);
	}
	CFG = make_cfg(spec, reasoning);

	// resume mode: explicit --resume takes precedence, else bare slug compat
	if (resumeSlug) {
		const wd = resolve(ROOT, resumeSlug);
		if (!existsSync(resolve(wd, 'state.json')) && !existsSync(resolve(wd, 'meta.json'))) die(`no workspace for --resume ${resumeSlug}`);
		const st = JSON.parse(readFileSync(resolve(wd, 'state.json'), 'utf8')) as State;
		const q = st.question || resumeSlug;
		const saved: string[] = st.angles || [];
		if (!angles.length && saved.length) angles.push(...saved);
		await run(q, resumeSlug, angles, enableThink || (st.done.includes('phase:pre-think') || st.done.includes('phase:post-think')));
		return;
	}

	const first = rest[0] || die('need <question> or --resume <slug>');
	// bare slug compat: if first arg is an existing slug and no other rest, treat as resume with warning
	const maybeSlugWd = resolve(ROOT, first);
	const isExistingSlug = rest.length === 1 && (existsSync(resolve(maybeSlugWd, 'state.json')) || existsSync(resolve(maybeSlugWd, 'meta.json')));
	if (isExistingSlug && !explicitSlug) {
		console.error(`note: "${first}" looks like an existing slug — resuming. Use --resume for explicit resume.`);
		const st = JSON.parse(readFileSync(resolve(maybeSlugWd, 'state.json'), 'utf8')) as State;
		const q = st.question || first;
		const saved: string[] = st.angles || [];
		if (!angles.length && saved.length) angles.push(...saved);
		await run(q, first, angles, enableThink || (st.done.includes('phase:pre-think') || st.done.includes('phase:post-think')));
		return;
	}

	const question = rest.join(' ').trim() || first;
	const slug = explicitSlug || slugify(question);
	await run(question, slug, angles, enableThink);
}

main().catch(e => { console.error((e as Error).stack || (e as Error).message); process.exit(1); });
