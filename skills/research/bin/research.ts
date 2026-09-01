#!/usr/bin/env bun
// search -> scrape -> extract -> gate -> ~/search/<slug>.md
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, resolve } from 'node:path';

type Cfg = { baseUrl: string; apiKey: string; model: string; timeout: number; max_tokens: number };
type Hit = { url: string; title: string; excerpt: string };
type State = { question: string; slug: string; done: string[]; angles?: string[] };

const PROVIDERS: Record<string, { baseUrl: () => string; apiKey: () => string }> = {
	'openrouter': { baseUrl: () => (process.env.OPENROUTER_BASE || 'https://openrouter.ai/api/v1').replace(/\/+$/, ''), apiKey: () => process.env.OPENROUTER_API_KEY || '' },
	'amazon-bedrock-mantle': { baseUrl: () => (process.env.AMAZON_BEDROCK_MANTLE_OPENAI_COMPATIBLE_URL || 'https://bedrock-mantle.us-west-2.api.aws/openai/v1').replace(/\/+$/, ''), apiKey: () => process.env.AMAZON_BEDROCK_MANTLE_API_KEY || '' },
};
let CFG: Cfg | null = null;
const ROOT = resolve(homedir(), 'search');
const N = 5, MAX_Q = 6, MAX_PAGES = 10;

const die = (m: string): never => { console.error(m); process.exit(1); };
const slugify = (s: string) => (s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'topic').slice(0, 64);
const sha1 = (s: string) => createHash('sha1').update(s).digest('hex');
const pid_of = (url: string) => sha1(url.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '')).slice(0, 16);
const write_atomic = (p: string, t: string) => { mkdirSync(dirname(p), { recursive: true }); const tmp = p + '.tmp'; writeFileSync(tmp, t); renameSync(tmp, p); };

function sh(cmd: string, args: string[], ms = 90000): Promise<{ ok: boolean; out: string; err: string }> {
	return new Promise(res => {
		const c = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
		let out = '', err = '', to = false;
		const t = setTimeout(() => { to = true; c.kill('SIGTERM'); }, ms);
		c.stdout.on('data', d => { out += d.toString(); if (out.length > 20 * 1024 * 1024) c.kill('SIGTERM'); });
		c.stderr.on('data', d => { err += d.toString(); });
		c.on('error', e => { clearTimeout(t); res({ ok: false, out, err: e.message }); });
		c.on('close', code => { clearTimeout(t); res({ ok: code === 0 && !to, out, err: to ? err + ' timeout' : err }); });
	});
}
function pLimit(n: number) {
	let a = 0; const q: Array<() => void> = [];
	return async <T>(fn: () => Promise<T>): Promise<T> => {
		if (a >= n) await new Promise<void>(r => q.push(r));
		a++; try { return await fn(); } finally { a--; const f = q.shift(); if (f) f(); }
	};
}

function parse_model(raw: string) { const i = raw.indexOf('/'); if (i < 1) die('model must be provider/id'); return { provider: raw.slice(0, i), model: raw.slice(i + 1) }; }
function make_cfg(spec: string): Cfg {
	const { provider, model } = parse_model(spec);
	const p = PROVIDERS[provider]; if (!p) die(`unknown provider ${provider}`);
	const k = p.apiKey(); if (!k) die(`no api key for ${provider}`);
	return { baseUrl: p.baseUrl(), apiKey: k, model, timeout: 600000, max_tokens: 6000 };
}
async function llm(prompt: string): Promise<string> {
	if (!CFG) die('no cfg');
	const url = CFG.baseUrl + '/chat/completions';
	const body = { model: CFG.model, messages: [{ role: 'user', content: prompt }], max_tokens: CFG.max_tokens, temperature: 0.2 };
	for (let i = 1; i <= 3; i++) {
		const ac = new AbortController(); const t = setTimeout(() => ac.abort(), CFG!.timeout);
		try {
			const r = await fetch(url, { method: 'POST', headers: { Authorization: `Bearer ${CFG.apiKey}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: ac.signal });
			const txt = await r.text(); let j: unknown = null; try { j = JSON.parse(txt); } catch {}
			if (!r.ok) { if (i < 3 && (r.status === 429 || r.status >= 500)) { await new Promise(r => setTimeout(r, i * 2000)); continue; } throw new Error(txt.slice(0, 800)); }
			const ch = (j as { choices?: Array<{ message?: { content?: unknown } }> })?.choices?.[0]?.message?.content;
			const out = typeof ch === 'string' ? ch.trim() : Array.isArray(ch) ? (ch as Array<{ text?: string }>).map(x => x.text || '').join('\n').trim() : '';
			if (!out) throw new Error('empty LLM response');
			return out;
		} catch (e: unknown) { if (i === 3) throw e; await new Promise(r => setTimeout(r, i * 2000)); } finally { clearTimeout(t); }
	}
	throw new Error('unreachable');
}

function parse_hits(raw: string): Hit[] {
	let d: unknown; try { d = JSON.parse(raw); } catch { return []; }
	const o = d as Record<string, unknown>;
	const rows = Array.isArray(d) ? d as unknown[] : (o.results as unknown[]) || (o.data as Record<string, unknown>)?.web as unknown[] || [];
	if (!Array.isArray(rows)) return [];
	const out: Hit[] = [];
	for (const r of rows as Array<Record<string, unknown>>) {
		const url = String(r.url || r.link || ''); if (!url.startsWith('http')) continue;
		const ex = Array.isArray(r.excerpts) ? (r.excerpts as string[]).join('\n') : String(r.excerpt || r.description || r.snippet || '');
		out.push({ url, title: String(r.title || url), excerpt: String(ex) });
	}
	return out;
}
async function search_angle(q: string, dest: string): Promise<Hit[]> {
	const r = await sh('firecrawl', ['search', q, '--limit', '9', '--json', '-o', dest], 90000);
	if (!existsSync(dest)) { console.error(`  ! search failed: ${r.err.slice(0, 120) || r.out.slice(0, 120)}`); return []; }
	return parse_hits(readFileSync(dest, 'utf8'));
}
async function scrape_page(url: string, dest: string): Promise<string> {
	const r = await sh('firecrawl', ['scrape', url, '-o', dest], 90000);
	if (!existsSync(dest)) return '';
	return readFileSync(dest, 'utf8');
}

function extract_prompt(url: string, page: string): string {
	return `Extract quote-anchored claims from this ONE page. Invent nothing.\nReturn ONLY JSON: {"source_url":"${url}","claims":[{"claim":"atomic sentence","quote":"verbatim ≤40 words","cited_primary":null}]}\nRules: quote verbatim; every number/date in claim must be in quote; one number per claim; empty array valid.\n\nPAGE:\n${page.slice(0, 24000)}`;
}
function parse_extract(raw: string, url: string) {
	const m = raw.match(/\{[\s\S]*\}/); if (!m) return [];
	try {
		const d = JSON.parse(m[0]) as { claims?: Array<{ claim?: unknown; quote?: unknown; cited_primary?: unknown }>; source_url?: string };
		const cs = Array.isArray(d.claims) ? d.claims : [];
		return cs.filter(c => typeof c.claim === 'string' && typeof c.quote === 'string').map(c => ({ claim: String(c.claim).trim(), quote: String(c.quote).trim(), cited_primary: (c.cited_primary as string) || null, source_url: d.source_url || url }));
	} catch { return []; }
}

const NUM_RE = /\d[\d,]*(?:\.\d+)?\s?(?:%|x|×)?/g;
function norm_ws(s: string) { return (s || '').replace(/\s+/g, ' ').trim(); }
function norm_key(s: string) { return norm_ws(s).toLowerCase().replace(/[^a-z0-9]+/g, ''); }
function normalize_url(url: string) { try { const u = new URL(url.trim()); let h = u.hostname.toLowerCase().replace(/^www\./, ''); const q = [...u.searchParams.entries()].filter(([k]) => !['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref', 'fbclid', 'gclid'].includes(k.toLowerCase())); q.sort((a, b) => a[0] === b[0] ? a[1].localeCompare(b[1]) : a[0].localeCompare(b[0])); const qs = q.map(([k, v]) => v ? `${k}=${v}` : k).join('&'); const path = (u.pathname || '').replace(/\/+$/, ''); return `${h}${path}${qs ? `?${qs}` : ''}`; } catch { return url.trim().toLowerCase(); } }
function domain_of(url: string) { try { return new URL(url).hostname.toLowerCase().replace(/^www\./, ''); } catch { return ''; } }
function registrable_domain(url: string) { const h = domain_of(url).split('.'); return h.length >= 2 ? h.slice(-2).join('.') : domain_of(url); }
function quote_in_text(q: string, t: string) { if (!q?.trim() || !t) return false; if (t.includes(q)) return true; const qk = norm_key(q); return !!qk && norm_key(t).includes(qk); }
function parse_nums(s: string) { const out = new Set<string>(); if (!s) return out; NUM_RE.lastIndex = 0; let m: RegExpExecArray | null; while ((m = NUM_RE.exec(s)) !== null) { const tok = m[0].replace(/\s+/g, '').replace(/,/g, '').replace(/×/g, 'x').toLowerCase(); if (/\d/.test(tok)) out.add(tok); } return out; }
function gate_claim(c: Record<string, unknown>, text: string) {
	const g: Record<string, unknown> = { ...c }; const q = String(g.quote || '');
	const found = quote_in_text(q, text); (g as Record<string, unknown>).quote_found = found;
	const need = parse_nums(String(g.claim || '')); const have = found ? parse_nums(q) : new Set<string>();
	(g as Record<string, unknown>).missing_numbers = [...need].filter(x => !have.has(x));
	(g as Record<string, unknown>).verified = !!(found && (g as { missing_numbers: string[] }).missing_numbers.length === 0);
	const qk = norm_key(q); (g as Record<string, unknown>).echo_key = qk.length >= 24 ? 'qk:' + qk.slice(0, 48) : 'h:' + sha1(norm_key(String(g.claim || '')) + String(g.source_url || '')).slice(0, 12);
	(g as Record<string, unknown>).unit = registrable_domain(String(g.source_url || '')) || 'u:' + sha1(String(g.source_url || '?')).slice(0, 10);
	return g;
}
function assign_status(gated: Record<string, unknown>[]) {
	const byEcho = new Map<string, Set<string>>(); for (const g of gated) if (g.verified) { const k = String(g.echo_key); if (!byEcho.has(k)) byEcho.set(k, new Set()); byEcho.get(k)!.add(String(g.unit)); }
	const byClaim = new Map<string, Set<string>>(); for (const g of gated) if (g.verified) { const copied = (byEcho.get(String(g.echo_key))?.size || 0) >= 2; (g as Record<string, unknown>).origin = copied ? 'copy:' + g.echo_key : 'dom:' + g.unit; const k = norm_key(String(g.claim || '')); if (!byClaim.has(k)) byClaim.set(k, new Set()); byClaim.get(k)!.add(String((g as Record<string, unknown>).origin)); }
	for (const g of gated) { const n = g.verified ? (byClaim.get(norm_key(String(g.claim || '')))?.size || 0) : 0; (g as Record<string, unknown>).indep_count = n; (g as Record<string, unknown>).status = n >= 2 ? 'CORROBORATED' : g.verified ? 'SINGLE' : 'UNCHECKED'; }
	return gated;
}
function render_ledger(meta: { slug: string; subject: string; question: string }, gated: Record<string, unknown>[], sources: Array<{ url: string; title: string }>) {
	const ORDER: Record<string, number> = { CORROBORATED: 0, SINGLE: 1, UNCHECKED: 2 };
	const TITLES: Record<string, string> = { CORROBORATED: 'Corroborated (≥2 independent origins)', SINGLE: 'Single-source', UNCHECKED: 'Unchecked (quote or figure check failed)' };
	const shown = new Set<string>(); const sec: Record<string, string[]> = { CORROBORATED: [], SINGLE: [], UNCHECKED: [] };
	const sorted = [...gated].sort((a, b) => (ORDER[String(a.status)] - ORDER[String(b.status)]) || (Number(b.indep_count) - Number(a.indep_count)));
	for (const g of sorted) { const k = String(g.echo_key); if (shown.has(k)) continue; shown.add(k); const peers = gated.filter(r => r.echo_key === g.echo_key); const st = peers.reduce((m, r) => ORDER[String(r.status)] < ORDER[String(m.status)] ? r : m, peers[0]).status as string; const indep = Math.max(...peers.map(r => Number(r.indep_count))); const urls = [...new Set(peers.map(r => String(r.source_url)))].slice(0, 6).map(u => `[${u}]`).join(' '); const rep = peers.reduce((a, b) => String(a.claim).length >= String(b.claim).length ? a : b); sec[st].push(`- ${rep.claim} — indep=${indep} — ${urls}`.replace(/ — $/, '')); }
	const src_lines = ['## Sources', '', '| title | url |', '|---|---|']; for (const s of sources) src_lines.push(`| ${(s.title || '').replace(/\|/g, '/').slice(0, 48)} | ${s.url} |`);
	const rej = gated.filter(g => !g.quote_found).length; const bad = gated.filter(g => g.quote_found && (g as { missing_numbers: string[] }).missing_numbers.length).length; const units = new Set(gated.filter(g => g.verified).map(g => String(g.unit)));
	const body = Object.keys(ORDER).map(st => `## ${TITLES[st]}\n\n` + (sec[st].length ? sec[st].join('\n') : 'None.')).join('\n\n');
	return `# ${meta.subject}\n\n- Question: ${meta.question || meta.subject}\n- Generated: ${new Date().toISOString().slice(0, 10)}\n- Limits: proves quotation and number containment only; corroboration is byte-identical wording on ≥2 domains.\n\n${body}\n\n## Process audit\n\n- Claims: ${gated.length}; quote rejects: ${rej}; figure rejects: ${bad}\n- Distinct verified domains: ${units.size}\n\n${src_lines.join('\n')}\n`;
}

function load_jsonl(p: string): Record<string, unknown>[] { if (!existsSync(p)) return []; const t = readFileSync(p, 'utf8'); const out: Record<string, unknown>[] = []; for (const ln of t.split('\n')) if (ln.trim()) try { out.push(JSON.parse(ln)); } catch {} return out; }
function write_jsonl(p: string, rows: Record<string, unknown>[]) { mkdirSync(dirname(p), { recursive: true }); writeFileSync(p, rows.map(r => JSON.stringify(r)).join('\n') + (rows.length ? '\n' : '')); }

async function run(question: string, slug: string, explicitAngles: string[]) {
	const wd = resolve(ROOT, slug); mkdirSync(wd, { recursive: true });
	const state_path = resolve(wd, 'state.json');
	let state: State = existsSync(state_path) ? JSON.parse(readFileSync(state_path, 'utf8')) as State : { question, slug, done: [] };
	state.question = question; state.slug = slug; write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	const meta_path = resolve(wd, 'meta.json');
	if (!existsSync(meta_path)) write_atomic(meta_path, JSON.stringify({ slug, subject: question, question, created: new Date().toISOString(), updated: new Date().toISOString() }, null, '\t'));
	else { const m = JSON.parse(readFileSync(meta_path, 'utf8')); m.question = question; m.updated = new Date().toISOString(); write_atomic(meta_path, JSON.stringify(m, null, '\t')); }

	console.log(`research: ${slug}`);

	let angles: string[];
	if (explicitAngles.length) { angles = explicitAngles.slice(0, MAX_Q); }
	else if (state.angles?.length) { angles = state.angles; }
	else {
		angles = [question];
		try {
			const raw = await llm(`Generate up to ${MAX_Q} distinct web search queries covering: "${question}". Return ONLY JSON array.`);
			const m = raw.match(/\[[\s\S]*\]/);
			if (m) { const a = JSON.parse(m[0]) as unknown; if (Array.isArray(a) && a.length > 1) angles = (a as unknown[]).map(s => String(s).trim()).filter(Boolean).slice(0, MAX_Q); }
		} catch {}
		state.angles = angles; write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	}
	angles = angles.slice(0, MAX_Q);

	const kept = new Map<string, Hit>();
	const lim = pLimit(N);
	await Promise.all(angles.map((q, i) => lim(async () => {
		const id = `a${String(i + 1).padStart(2, '0')}`; if (state.done.includes('search:' + id)) return;
		const dest = resolve(wd, `search-${id}.json`); const hits = await search_angle(q, dest);
		for (const h of hits) if (!kept.has(h.url)) kept.set(h.url, h);
		state.done.push('search:' + id); write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	})));
	for (let i = 0; i < angles.length; i++) { const p = resolve(wd, `search-a${String(i + 1).padStart(2, '0')}.json`); if (existsSync(p)) for (const h of parse_hits(readFileSync(p, 'utf8'))) if (!kept.has(h.url)) kept.set(h.url, h); }
	const capped = [...kept.values()].slice(0, MAX_PAGES);

	const plim = pLimit(N);
	const sources: Array<{ url: string; title: string }> = [];
	await Promise.all(capped.map(h => plim(async () => {
		const pid = pid_of(h.url); if (state.done.includes('page:' + pid)) { sources.push({ url: h.url, title: h.title }); return; }
		const txt_path = resolve(wd, 'pages', `${pid}.txt`);
		let text = existsSync(txt_path) ? readFileSync(txt_path, 'utf8') : '';
		if (!text) { const s = await scrape_page(h.url, resolve(wd, `scrape-${pid}.md`)); text = s || h.excerpt || ''; if (text) write_atomic(txt_path, text); }
		if (!text.trim()) { state.done.push('page:' + pid); write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n'); return; }
		sources.push({ url: h.url, title: h.title });
		const raw = await llm(extract_prompt(h.url, text));
		const claims = parse_extract(raw, h.url);
		write_atomic(resolve(wd, 'extracts', `${pid}.json`), JSON.stringify({ source_url: h.url, claims }, null, '\t') + '\n');
		state.done.push('page:' + pid); write_atomic(state_path, JSON.stringify(state, null, '\t') + '\n');
	})));

	const srcSet = new Map<string, { url: string; title: string }>();
	for (const h of capped) srcSet.set(h.url, { url: h.url, title: h.title });
	const allSources = [...srcSet.values()];

	const extracts = capped.map(h => resolve(wd, 'extracts', `${pid_of(h.url)}.json`)).filter(existsSync);
	if (!extracts.length) die('no extracts');
	const raw_path = resolve(wd, 'claims.raw.jsonl'); const existing = load_jsonl(raw_path);
	for (const p of extracts) {
		const d = JSON.parse(readFileSync(p, 'utf8')) as { claims?: unknown[]; source_url?: string };
		const cs = Array.isArray(d.claims) ? d.claims as Record<string, unknown>[] : [];
		if (existing.some(r => r.source_url === d.source_url)) continue;
		for (let i = 0; i < cs.length; i++) { const c = cs[i] as Record<string, unknown>; if (!c.source_url) c.source_url = d.source_url; if (!c.id) c.id = `${pid_of(String(c.source_url))}_${i}`; existing.push(c); }
	}
	write_jsonl(raw_path, existing);

	const cache: Record<string, string> = {};
	function text_for(url: string) { const k = normalize_url(url); if (k in cache) return cache[k]; const p = resolve(wd, 'pages', `${pid_of(url)}.txt`); const t = existsSync(p) ? readFileSync(p, 'utf8') : ''; cache[k] = t; return t; }
	const gated = assign_status(existing.map(c => gate_claim(c as Record<string, unknown>, text_for(String(c.source_url || '')))));
	write_jsonl(resolve(wd, 'claims.gated.jsonl'), gated);

	const meta = JSON.parse(readFileSync(meta_path, 'utf8'));
	const md = render_ledger(meta, gated, allSources);
	write_atomic(resolve(ROOT, `${slug}.md`), md);
	console.log(`write → ${resolve(ROOT, `${slug}.md`)}\n0 — done`);
}

async function main() {
	const args = process.argv.slice(2);
	if (!args.length || args.includes('-h') || args.includes('--help')) {
		console.log(`research "<question>" [--angle q] [--slug s] [--resume s] [--model p/id]`);
		process.exit(0);
	}
	const angles: string[] = []; let spec = process.env.RESEARCH_MODEL || 'openrouter/z-ai/glm-5.3-flash';
	let explicitSlug: string | null = null; let resumeSlug: string | null = null; const rest: string[] = [];
	for (let i = 0; i < args.length; i++) {
		const a = args[i];
		if (a === '--angle') { const v = args[++i]; if (!v) die('--angle needs text'); angles.push(v); }
		else if (a === '--model') spec = args[++i] || die('--model needs p/id');
		else if (a === '--slug') explicitSlug = args[++i] || die('--slug needs value');
		else if (a === '--resume') resumeSlug = args[++i] || die('--resume needs slug');
		else if (a.startsWith('--')) die(`unknown flag ${a}`);
		else rest.push(a);
	}
	CFG = make_cfg(spec);
	if (resumeSlug) {
		const wd = resolve(ROOT, resumeSlug); if (!existsSync(resolve(wd, 'state.json')) && !existsSync(resolve(wd, 'meta.json'))) die(`no workspace for --resume ${resumeSlug}`);
		const st = JSON.parse(readFileSync(resolve(wd, 'state.json'), 'utf8')) as State;
		const q = st.question || resumeSlug; if (!angles.length && st.angles?.length) angles.push(...st.angles);
		await run(q, resumeSlug, angles); return;
	}
	const first = rest[0] || die('need <question> or --resume <slug>');
	const maybeWd = resolve(ROOT, first);
	if (rest.length === 1 && !explicitSlug && (existsSync(resolve(maybeWd, 'state.json')) || existsSync(resolve(maybeWd, 'meta.json')))) {
		const st = JSON.parse(readFileSync(resolve(maybeWd, 'state.json'), 'utf8')) as State;
		const q = st.question || first; if (!angles.length && st.angles?.length) angles.push(...st.angles);
		await run(q, first, angles); return;
	}
	const question = rest.join(' ').trim() || first;
	const slug = explicitSlug || slugify(question);
	await run(question, slug, angles);
}
main().catch(e => { console.error((e as Error).stack || (e as Error).message); process.exit(1); });
