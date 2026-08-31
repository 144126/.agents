#!/usr/bin/env node
// rethink <topic> <n> [--fast] [--angle "s"]...
// rethink <file.r> [--fast]   # resume
import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { homedir } from 'node:os';

type Node = { s: string; d?: 0 | 1; c?: Record<string, Node> };
type Tree = Record<string, Node>;
type Cfg = { baseUrl: string; apiKey: string; model: string; timeout: number; max_tokens: number; api: 'chat' | 'responses' };

const usages: any[] = [];

function add_usage(a: any, b: any): any {
	if (typeof b === 'number' && Number.isFinite(b)) {
		return (typeof a === 'number' && Number.isFinite(a) ? a : 0) + b;
	}
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
	} else {
		console.log('usage: (none in response)');
	}
}

function dump_usage() {
	if (!usages.length) return;
	const total = usages.reduce((a, u) => add_usage(a, u), {});
	console.log(`usage calls: ${usages.length}`);
	usages.forEach((u, i) => console.log(`usage ${i + 1}: ${JSON.stringify(u)}`));
	console.log(`usage total: ${JSON.stringify(total)}`);
}

const die = (m: string): never => {
	dump_usage();
	console.error(m);
	process.exit(1);
};

const OPENROUTER = process.env.OPENROUTER_BASE || 'https://openrouter.ai/api/v1';
const GLM = 'z-ai/glm-5.3-flash';
const THINK = resolve(homedir(), 'think');

function slug(s: string): string {
	const t = s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48);
	return t || 'topic';
}

function glm_cfg(): Cfg | null {
	const apiKey = process.env.OPENROUTER_API_KEY || '';
	if (!apiKey) return null;
	return { baseUrl: OPENROUTER.replace(/\/+$/, ''), apiKey, model: GLM, timeout: 300000, max_tokens: 4096, api: 'chat' as const };
}

function leaves(t: Tree, prefix: string[] = []): { path: string[]; node: Node }[] {
	const out: { path: string[]; node: Node }[] = [];
	for (const [name, node] of Object.entries(t)) {
		const p = [...prefix, name];
		if (node.c) out.push(...leaves(node.c as Tree, p));
		else out.push({ path: p, node });
	}
	return out;
}

function complete(n: Node): boolean {
	return !!(n.c ? Object.values(n.c).every(complete) : n.d === 1);
}

function normalize(t: Tree): Tree {
	const out: Tree = {};
	for (const [k, v] of Object.entries(t)) {
		const n: Node = { s: v.s, d: complete(v) ? 1 : 0 };
		if (v.c) n.c = normalize(v.c as Tree);
		out[k] = n;
	}
	return out;
}

function load(file: string): { preamble: string | null; tree: Tree } {
	if (!existsSync(file)) die(`cannot read ${file}`);
	let tree: any;
	try {
		tree = JSON.parse(readFileSync(file, 'utf8'));
	} catch (e: any) {
		die(`${file} is not valid json: ${e.message}`);
	}
	const preamble = typeof tree._ === 'string' ? tree._ : null;
	delete tree._;
	return { preamble, tree };
}

function save(file: string, preamble: string | null, tree: Tree) {
	const body: any = preamble === null ? {} : { _: preamble };
	Object.assign(body, normalize(tree));
	const tmp = file + '.tmp';
	writeFileSync(tmp, JSON.stringify(body, null, '\t') + '\n');
	renameSync(tmp, file);
}

function write_atomic(path: string, text: string) {
	const tmp = path + '.tmp';
	writeFileSync(tmp, text);
	renameSync(tmp, path);
}

function parse_bullets(raw: string): string[] {
	const lines = raw.split('\n').map((l) => l.trim()).filter(Boolean);
	const bullets = lines.filter((l) => /^[-*•]\s+/.test(l)).map((l) => l.replace(/^[-*•]\s+/, '').trim()).filter(Boolean);
	if (bullets.length) return bullets.map((b) => `- ${b}`);
	return lines.filter((l) => l.length > 10).map((l) => (l.startsWith('-') ? l : `- ${l}`));
}

function norm_key(b: string): string {
	return b.toLowerCase().replace(/^[-*•]\s+/, '').replace(/[^a-z0-9]+/g, ' ').trim();
}

function append_dedup(existing: string, neu: string[]): string {
	const have = new Set(
		existing
			.split('\n')
			.filter((s) => s.trim().startsWith('-'))
			.map(norm_key),
	);
	const add = neu.filter((b) => {
		const k = norm_key(b);
		if (!k || have.has(k)) return false;
		have.add(k);
		return true;
	});
	const head = existing.trim();
	return (head ? head + '\n' : '') + (add.length ? add.join('\n') + '\n' : head ? '\n' : '');
}

function done_set(existing: string): Set<string> {
	const s = new Set<string>();
	for (const line of existing.split('\n')) {
		const m = line.match(/^<!-- done: (.+) -->$/);
		if (m) s.add(m[1]);
	}
	return s;
}

function text_of(cfg: Cfg, json: any): string {
	if (cfg.api === 'responses') {
		const from = json?.output_text;
		if (typeof from === 'string' && from.trim()) return from.trim();
		const parts: string[] = [];
		for (const item of json?.output || []) {
			for (const c of item?.content || []) {
				if (typeof c?.text === 'string') parts.push(c.text);
			}
		}
		return parts.join('\n').trim();
	}
	const c = json?.choices?.[0]?.message?.content ?? json?.choices?.[0]?.text ?? '';
	if (typeof c === 'string') return c.trim();
	if (Array.isArray(c)) return c.map((x: any) => x.text || x.content || '').join('\n').trim();
	return '';
}

async function fetch_with_cfg(cfg: Cfg, messages: { role: string; content: string }[]): Promise<string> {
	const url = cfg.baseUrl + (cfg.api === 'responses' ? '/responses' : '/chat/completions');
	const body =
		cfg.api === 'responses'
			? { model: cfg.model, input: messages.map((m) => m.content).join('\n\n'), max_output_tokens: cfg.max_tokens, usage: { include: true } }
			: { model: cfg.model, messages, max_tokens: cfg.max_tokens, temperature: 0.7, usage: { include: true } };
	let last = '';
	for (let i = 1; i <= 3; i++) {
		const ac = new AbortController();
		const t = setTimeout(() => ac.abort(), cfg.timeout);
		try {
			const res = await fetch(url, {
				method: 'POST',
				headers: { Authorization: `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json', 'HTTP-Referer': 'https://pi.dev', 'X-OpenRouter-Title': 'pi', 'X-OpenRouter-Categories': 'cli-agent' },
				body: JSON.stringify(body),
				signal: ac.signal,
			});
			const text = await res.text();
			let json: any = null;
			try { json = JSON.parse(text); } catch {}
			if (!res.ok) {
				last = text.slice(0, 400);
				if (i < 3 && (res.status === 429 || res.status >= 500)) {
					await new Promise((r) => setTimeout(r, i * 2000));
					continue;
				}
				throw new Error(`LLM ${text.slice(0, 800)} (model=${cfg.model})`);
			}
			const out = text_of(cfg, json);
			if (!out) throw new Error(`empty LLM response: ${JSON.stringify(json).slice(0, 400)}`);
			record_usage(json);
			return out;
		} catch (e: any) {
			last = e.message || String(e);
			if (i < 3) await new Promise((r) => setTimeout(r, i * 2000));
			else throw new Error(last);
		} finally { clearTimeout(t); }
	}
	throw new Error(last);
}

async function post(messages: { role: string; content: string }[]): Promise<string> {
	const cfg = glm_cfg();
	if (!cfg) die('no OPENROUTER_API_KEY');
	return await fetch_with_cfg(cfg, messages);
}

function think_prompt(preamble: string | null, leaf_s: string): string {
	return `Think extremely deeply about this ONE angle. Do not look at prior conclusions.

Global context:
${preamble || '(none)'}

Angle:
${leaf_s}

From first principles. Steelman both sides. Look for contradictions. Prefer concrete.
3–8 atomic conclusions from this angle only.
Output ONLY markdown bullets: "- <sentence>"`;
}

function make_tree(topic: string, angles: string[]): { preamble: string; tree: Tree } {
	if (angles.length < 1 || angles.length > 200) die('n must be 1..200');
	const tree: Tree = {};
	angles.forEach((s, i) => {
		tree[`a${String(i + 1).padStart(2, '0')}`] = { s, d: 0 };
	});
	return { preamble: topic, tree };
}

function write_tree(file: string, preamble: string, tree: Tree) {
	mkdirSync(dirname(file), { recursive: true });
	save(file, preamble, tree);
}

async function run(file: string) {
	console.log(`rethink: ${file}`);
	console.log(`model: ${GLM}`);

	const conc = file.replace(/\.r$/, '') + '.conclusions.md';
	let n = 0;
	while (true) {
		const { preamble, tree } = load(file);
		const flat = leaves(tree);
		if (!flat.length) die(`${file} has no steps`);
		const existing = existsSync(conc) ? readFileSync(conc, 'utf8') : '';
		const already = done_set(existing);
		const i = flat.findIndex((l) => l.node.d !== 1 && !already.has(l.path.join('.')));
		if (i === -1) {
			// repair: any unmarked leaf already in conclusions
			let repaired = false;
			for (const l of flat) {
				if (l.node.d !== 1 && already.has(l.path.join('.'))) {
					l.node.d = 1;
					repaired = true;
				}
			}
			if (repaired) save(file, preamble, tree);
			if (flat.every((l) => l.node.d === 1 || already.has(l.path.join('.')))) {
				console.log('0 — all steps done');
				break;
			}
			console.log('0 — all steps done');
			break;
		}
		const leaf = flat[i];
		const label = leaf.path.join('.');
		console.log(`\n── ${i + 1}/${flat.length} ${label} ──`);
		console.log(`s: ${leaf.node.s.slice(0, 160)}${leaf.node.s.length > 160 ? '…' : ''}`);
		console.log(`  → think ${label}`);
		const neu = parse_bullets(await post([{ role: 'user', content: think_prompt(preamble, leaf.node.s) }]));
		if (!neu.length) die(`no conclusions from ${label}`);
		neu.forEach((b) => console.log(`    ${b}`));

		const now = existsSync(conc) ? readFileSync(conc, 'utf8') : '';
		const merged = append_dedup(now, neu) + `<!-- done: ${label} -->\n`;
		write_atomic(conc, merged);
		leaf.node.d = 1;
		save(file, preamble, tree);
		n++;
		const after = leaves(load(file).tree);
		console.log(`  ← ${(merged.match(/^- /gm) || []).length} bullets, ${after.filter((l) => l.node.d === 1).length}/${after.length} done`);
	}

	if (!existsSync(conc)) die('incomplete — no conclusions file');
	const body = readFileSync(conc, 'utf8');
	const bullets = (body.match(/^- /gm) || []).length;
	const { tree } = load(file);
	const undone = leaves(tree).filter((l) => l.node.d !== 1);
	if (undone.length) die(`incomplete — ${undone.length} leaf(s) left`);
	const out = file.replace(/\.r$/, '') + '.md';
	write_atomic(out, `# ${basename(file, '.r')}\n\n` + body.replace(/^<!-- done: .+ -->\n/gm, ''));
	console.log(`\nwrite → ${out} (${bullets} conclusions)`);
	console.log(`\ndone. ${n} step(s).`);
	dump_usage();
}

async function main() {
	const args = process.argv.slice(2);
	if (!args.length || args.includes('-h') || args.includes('--help')) {
		console.log(`rethink <topic> <n> [--fast] [--angle "s"]...
rethink <file.r> [--fast]`);
		process.exit(0);
	}

	const angles: string[] = [];
	const rest: string[] = [];
	let fast = false;
	for (let i = 0; i < args.length; i++) {
		const a = args[i];
		if (a === '--fast') fast = true;
		else if (a === '--angle') angles.push(args[++i] || die('--angle needs text'));
		else rest.push(a);
	}

	const first = rest[0];
	if (!first) die('need <topic> <n> or <file.r>');

	if (first.endsWith('.r') || existsSync(resolve(first))) {
		await run(resolve(first));
		return;
	}

	const topic = first;
	const n = parseInt(rest[1] || '', 10);
	if (!n) die('need <topic> <n>');
	if (angles.length && angles.length !== n) die(`got ${angles.length} --angle, expected ${n}`);
	const list = angles.length ? angles : Array.from({ length: n }, (_, i) => `angle ${i + 1} of ${n} on: ${topic}`);
	const file = resolve(THINK, slug(topic) + '.r');
	if (existsSync(file)) {
		console.log(`resume ${file}`);
		await run(file);
		return;
	}
	const { preamble, tree } = make_tree(topic, list);
	write_tree(file, preamble, tree);
	console.log(`init → ${file} (${n} leaves)`);
	await run(file);
}

main().catch((e) => {
	dump_usage();
	console.error(e.stack || e.message);
	process.exit(1);
});
