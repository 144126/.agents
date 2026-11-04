#!/usr/bin/env node
// prune: a decision model (Haiku) marks transcript entries the session no longer needs;
// they are stubbed in place (never deleted) so uuid chains and tool_use/tool_result pairs stay valid.
// Writes a new session file; the original is untouched. Usage: prune.ts [session.jsonl|id] [--dry] [--model m]
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { homedir } from 'node:os'
import { join, dirname, basename } from 'node:path'

const args = process.argv.slice(2)
const flag = (n: string) => { const i = args.indexOf(n); return i < 0 ? undefined : args.splice(i, 2)[1] }
const model = flag('--model') ?? 'claude-haiku-5-5'
const dry = args.includes('--dry') && (args.splice(args.indexOf('--dry'), 1), true)
const min_chars = 300
const keep_last = 12

const proj = join(homedir(), '.claude/projects', process.cwd().replace(/[^a-zA-Z0-9]/g, '-'))
const newest = () => readdirSync(proj).filter(f => f.endsWith('.jsonl'))
  .map(f => join(proj, f)).sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs)[0]
const src = !args[0] ? newest() : args[0].endsWith('.jsonl') ? args[0] : join(proj, args[0] + '.jsonl')

const lines = readFileSync(src, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l))
const last_boundary = lines.findLastIndex(e => e.type === 'system' && e.subtype === 'compact_boundary')
const tool_names = new Map<string, string>()
for (const e of lines) if (e.type === 'assistant' && Array.isArray(e.message?.content))
  for (const b of e.message.content) if (b.type === 'tool_use') tool_names.set(b.id, b.name)

const text_of = (v: unknown): string => typeof v === 'string' ? v
  : Array.isArray(v) ? v.map(x => x?.text ?? (x?.type === 'image' ? '[image]' : '')).join('\n') : JSON.stringify(v ?? '')
const big_strings = (o: any) => Object.entries(o ?? {}).filter(([, v]) => typeof v === 'string' && v.length > min_chars)

// item: {i: id, l: line index, b: block index, k: kind (r tool_result, u tool_use, t user text, a assistant text), n: tool, c: chars, h: preview}
type item = { i: number; l: number; b: number; k: string; n: string; c: number; h: string }
const items: item[] = []
const msg_lines = lines.map((e, l) => [e, l] as const).filter(([e, l]) => l > last_boundary
  && (e.type === 'user' || e.type === 'assistant') && !e.isSidechain
  && (Array.isArray(e.message?.content) || typeof e.message?.content === 'string'))
const protected_from = msg_lines.length - keep_last
const first_user = msg_lines.find(([e]) => e.type === 'user')?.[1]
msg_lines.forEach(([e, l], m) => {
  if (m >= protected_from || l === first_user) return
  if (typeof e.message.content === 'string') e.message.content = [{ type: 'text', text: e.message.content }]
  e.message.content.forEach((b: any, bi: number) => {
    const add = (k: string, n: string, s: string) => s.length > min_chars
      && items.push({ i: items.length, l, b: bi, k, n, c: s.length, h: s.length > 500 ? s.slice(0, 360) + ' … ' + s.slice(-120) : s })
    if (b.type === 'tool_result') add('r', tool_names.get(b.tool_use_id) ?? '?', text_of(b.content))
    else if (b.type === 'tool_use') add('u', b.name, big_strings(b.input).map(([k, v]) => `${k}: ${v}`).join('\n'))
    else if (b.type === 'text' && !e.isMeta) add(e.type === 'user' ? 't' : 'a', '', b.text)
  })
})
if (!items.length) { console.log('nothing to prune'); process.exit(0) }

const user_turns = msg_lines.filter(([e]) => e.type === 'user' && !e.isMeta)
  .map(([e]) => text_of(e.message.content)).filter(t => t.trim()).slice(-4)
const kinds: Record<string, string> = { r: 'tool output', u: 'tool input', t: 'user msg', a: 'assistant msg' }
const prompt = `You prune a coding agent's conversation so it fits in less context. The agent will continue the task after pruning.
For each numbered entry decide if the agent will still need its full text to finish the current task.
Prune (return its id) when: output already acted on or superseded, file reads of files later edited or re-read, exploration that led nowhere, verbose logs/listings, failed attempts already fixed, chit-chat, long inputs whose effect is on disk (Write/Edit bodies).
Keep when: it holds user requirements, decisions, constraints, unresolved errors, facts not stored anywhere else, or the current state of work.
When unsure, keep. Pruned entries are replaced by a short stub naming the tool, so the agent can re-run it.

Latest user messages (current goal):
${user_turns.map(t => '- ' + t.slice(0, 1500)).join('\n')}

Entries (id | kind | tool | chars | preview):
${items.map(x => `#${x.i} | ${kinds[x.k]} | ${x.n} | ${x.c}\n${x.h.replace(/\s+/g, ' ')}`).join('\n\n')}

Return {"p": [ids to prune]}.`

const schema = JSON.stringify({ type: 'object', properties: { p: { type: 'array', items: { type: 'integer' } } }, required: ['p'] })
const out = JSON.parse(execFileSync('claude', ['-p', '--model', model, '--effort', 'low', '--no-session-persistence',
  '--tools', '', '--output-format', 'json', '--json-schema', schema], { input: prompt, maxBuffer: 1 << 26, cwd: homedir() }).toString())
if (out.is_error || !out.structured_output) throw new Error('decision model failed: ' + (out.result ?? out.subtype))
const pick = new Set<number>(out.structured_output.p)

let freed = 0
for (const x of items.filter(x => pick.has(x.i))) {
  const e = lines[x.l], b = e.message.content[x.b]
  freed += x.c
  if (x.k === 'r') {
    b.content = `[pruned: ${x.n} output, ${x.c} chars. Re-run if needed.]`
    if (e.toolUseResult) e.toolUseResult = b.content
  } else if (x.k === 'u') for (const [k, v] of big_strings(b.input)) b.input[k] = `[pruned ${(v as string).length} chars]`
  else b.text = b.text.slice(0, 160) + ` … [pruned ${x.c} chars]`
}
const report = `${pick.size}/${items.length} entries pruned, ~${Math.round(freed / 4 / 1000)}k tokens freed ($${out.total_cost_usd.toFixed(4)})`
if (dry) {
  for (const x of items) console.log(pick.has(x.i) ? '-' : '+', `#${x.i}`, kinds[x.k], x.n, x.c, x.h.slice(0, 100).replace(/\s+/g, ' '))
  console.log(report, '(dry run, nothing written)')
  process.exit(0)
}
const id = randomUUID(), old = basename(src, '.jsonl')
writeFileSync(join(dirname(src), id + '.jsonl'),
  lines.map(e => JSON.stringify(e.sessionId === old ? { ...e, sessionId: id } : e)).join('\n') + '\n', { mode: 0o600 })
console.log(report)
console.log(`resume: claude --resume ${id}`)
