# General

- never markdown format links
- web search: always `exa_web_search_exa` with `textMaxCharacters: 9999`. If unavailable, Exa REST: `source ~/.agents/secrets/load-exa.sh` for `EXA_API_KEY` (key file `~/.agents/secrets/exa.env`, mode 600, gitignored via `secrets/`), then `POST https://api.exa.ai/search` / `POST https://api.exa.ai/contents`. Never print or commit the key.
- never condense web results in chat without `cnd gate` (condense-search skill); a single text/file goes through the `condense` skill, gate required.
- this file is the global AGENTS.md. Skills: `~/.agents/skills/*/SKILL.md` (all of them). Commands: `~/.agents/commands/`.
- unknown error or unexpected outcome that one attempt doesn't resolve: search the net before acting further
- `source ~/.bashrc` whenever new aliases/config are needed
- always code with extreme simplicity; be minimalist
- always speak in extremely concise telegraphic phrases (short, clipped, no filler); explain things like i'm 9 years old
- never run `npm run build`; always `pnpm` over npm/npx, never npx directly
- portfolio: ed.apexlinks.org
- resume: https://registry.jsonresume.org/144126?theme=developer-mono — source is GitHub Gist `70cba709`, file `resume.json` (`gh gist view 70cba709 --filename resume.json`, `gh gist edit 70cba709 <file>`)

# Plans

Any work too long for one session runs off a plan file, driven by `plan.ts` (global, on PATH; bare `plan` works too). Source: `~/.local/bin/plan.ts`.

`{plan_name}.json` in the repo root. One file, nothing beside it. Flat, ordered object:

```json
{
	"step-name": { "step_details": "the entire step", "done": 0 }
}
```

- one key per step; `done` is `0` or `1`; every step starts `0`
- step names kebab-case, never numeric — insertion order IS plan order, and V8 reorders numeric-looking keys
- to reorder, move the entry; never rename it
- **the json is the only artifact.** never write a plan anywhere else; delete it when the plan is done — it's a worklist, git history is the record
- **make every step extremely technically detailed, detailing every technical implementation, so the implementing agent never has to choose or guess anything for any detail.** the exact file and line region, the current code quoted, the root cause, the replacement code verbatim, why that choice over the alternatives, plus anything the repo's own `CLAUDE.md`/`AGENTS.md` doesn't already state (a trap that makes a wrong change look right, a convention, a shape). no "update the handler", no "add validation" — a step that leaves a decision to the implementer is unfinished. a fresh session with zero context must be able to do the step from that one string alone
- newlines and code blocks live in the string as `\n` escapes — fine, models read them

```bash
plan.ts <plan_name>              # next undone step: its name, then its json
plan.ts <plan_name> <step_name>  # mark that step done, then print the next undone step
```

Prints `0` when every step is done. Takes `foo` or `foo.json`. Resolves relative to cwd, so plans are per-project.

Write the steps only after reading the code — every file the work touches, the real flow. A plan written from the request alone is guesswork. Order by dependency, foundations first; each step must leave the repo green on its own.

One plan file per body of work — never split tests and implementation into two files kept in lockstep. Each step carries both as ordered phases, all four completed before it is marked done:

1. **write the tests** — exactly these, implement nothing yet
2. **watch them fail** — for the reason stated. a test that passes before you implement is testing nothing; rewrite it
3. **implement**
4. **watch them pass** — new tests green, every pre-existing test still green

Executing: ask `plan.ts <plan>` for the step, never open the json and pick one yourself. Do exactly that step, nothing else. Run the repo's gate (tests, check, lint) and only if green mark it done, then commit scoped to the step name — marking done is a claim, not a bookmark. One step at a time, never batch, never run ahead. If a step is wrong or blocked: stop, tell the user, fix the plan file. Never silently skip it or mark it done.

# Rules for software/web dev projects/folders

## Code Style

- Naming: always snake_case for vars/functions. Db payload, type defs, request JSON and page-load return value keys are always single letters.
- Stored enum/status values: single characters (e.g. `st`: `r`=pending, `s`=success, `f`=failed). Map to full labels only when displaying.
- Svelte: runes only (`$props`, `$state`, `$derived`, `$effect`, `$bindable`) — never `export let`.
- Forms submit on Ctrl/Cmd+Enter only, never plain Enter — Enter stays browser-default (newline in `<textarea>`, nothing in `<input>`). Use the `ctrlEnter` action from `$lib/actions` on the form container: `use:ctrlEnter={submit}`. Every user-input form; file-upload-only UIs are exempt.
- No comments in code (clean names + structure speak; comments are debt unless they explain a non-obvious WHY).
- No vars for single use.
- Never start the dev server.
- Node projects: if `.dev-logs/server.log` exists it holds live dev server output — tail it before diagnosing any server issue, and after every code change check it for new SSR/compile/runtime errors before declaring done.
- Python projects: always activate the venv in `./env`; never create a new virtualenv.
- Always follow the repo's design system exactly (`DESIGN.md` and/or `src/app.css`). If `src/app.css` exists, never use raw css values — always its variables.
- Prefer Tailwind utilities; no inline `style=` attributes or `<style>` blocks — design-system tokens/classes only.
- Tailwind v4 + SvelteKit: `pnpm dlx sv add tailwindcss` does the install and wiring. Theme via `@theme` in `app.css` (no `tailwind.config.js`); dark mode `@custom-variant dark (&:is(.dark *));`; `@reference "tailwindcss";` inside any `<style>` block that needs theme tokens.
- All UI-facing text (labels, buttons, microcopy) in lowercase.
- When a repo has example files, follow their patterns perfectly; when a new pattern is decided, update the example files so they stay canonical.
- Fonts go in `static/fonts`.
- Google auth callback URLs are always `/google` — never `/google/callback` or anything else.
- Image prompts follow `docs/images/prompt-guide.md`; always create images matching the site's design system and style.

## Git Workflow

- after every edit turn: `git add .`, commit with a long message exhaustively explaining every change, then `git push`. A failed push is fine, the commit is what matters.

## Cloudflare / Wrangler secrets store

- Read secrets/var bindings ONLY via `$env/dynamic/private`:
  ```ts
  import { env } from '$env/dynamic/private';
  const id = env.GOOGLE_ID;            // plain [vars] / per-Worker secrets: sync string
  const sk = await env.SECRET.get();   // Secrets Store bindings: async object
  ```
- Always go through the `SecretVal` abstraction sitewide: `type SecretVal = string | { get?: () => Promise<string> }`, read via the repo's `get_secret(v)` helper, so Secrets Store bindings and plain strings are interchangeable. Never read a secret binding as a raw string; never reintroduce raw `env.KEY` reads or per-call `.get()` unwrapping.
- Local dev: remote Secrets Store secrets are NOT readable locally. Test with `wrangler dev` plus local secrets from `wrangler secrets-store secret create <store_id> --name KEY --scopes workers` (no `--remote`); plain `[vars]` load from `.env`.
- **Always use `.env` for local env vars — NEVER `.dev.vars`.** Delete `.dev.vars` if it exists.
- Production: declare secrets in `wrangler.toml`/`wrangler.jsonc` under `secrets_store_secrets: [{ binding, store_id, secret_name }]`; non-secret config under `[vars]`.
- First deploy: `pnpm install` fails with "packages field missing or empty" when `pnpm-workspace.yaml` has `allowBuilds` but no `packages`. Always add `packages: ['.']` beside the `allowBuilds` block (esbuild/workerd/sharp) — without it pnpm aborts install and (v10/v11) blocks the native build scripts.
- **Never put `wrangler types` in the `build` script.** Keep `build` as `vite build` only. `wrangler types --check` falsely flags the generated `worker-configuration.d.ts` as stale in Cloudflare Workers Builds (no `.dev.vars`, different wrangler/workerd version than local), and bare `wrangler types` also breaks builds. Remove it on sight, and on ANY reported deployment issue that may involve wrangler types.

# Clone Convention

Clone GitHub repos to `~/i/<org-or-user>/<repo-name>` — e.g. `gh repo clone obsidianmd/obsidian-releases` → `~/i/obsidianmd/obsidian-releases`.

# New Webapp Project (SvelteKit)

1. **Location**: `~/i/` by default; `~/i/me/` if the user says "personal project".
2. **Name**: 2–4 characters, digital root 9 (sum letter positions a=1..z=26 plus any digits, reduce to one digit). Never reuse — list `~/i/` (and `~/i/me/`) to check.
3. **Create**: `cd` to target dir, then `pnpm dlx sv create <name>`
4. **`sv create` prompts** (in order):
   - Template → **SvelteKit minimal**
   - TypeScript → **Yes, using TypeScript syntax**
   - Add-ons → **prettier, eslint, vitest, playwright, sveltekit-adapter, experimental**
   - vitest → **unit testing, component testing**
   - sveltekit-adapter → **cloudflare**, then **Workers**
   - experimental → **@sveltejs/kit@next**, then **async, remote functions, explicit environment variables, rendering error boundaries, forked preloading**
5. **Git & GitHub**: `git init && git add . && git commit -m"initial setup"`, then
   - personal: `gh repo create 144126/<name> --public --source=. --remote=origin --push`
   - otherwise: `gh repo create angelwingscomms/<name> --public --source=. --remote=origin --push`

# Memory

Your memory is OptMem: tool `~/.optmem/memo`, memories in `~/.optmem/memory`. It outlives every session, compaction, model and vendor change. Without it you do not know who you are, or what was decided and tried. Never edit or delete anything under `~/.optmem/memory` — the tool manages it.

- **At startup (mandatory)**: run `~/.optmem/memo wake` before any other tool call, every session, then do exactly what it prints, to the end of its output.
- **While working (mandatory)**: `~/.optmem/memo note "<1 line, max 280 chars>"` whenever you learn something new or something worth keeping happens — a task worth real effort, a fact or insight the user teaches you, anything about their life (even indirectly), any event of lasting effect. No redundant memories. If `note` asks for a compression, do it before your next action.
- **Recalling**: `~/.optmem/memo recall <regex>` searches every memory word for word; `~/.optmem/memo zoom <a-b>` opens a `#a-b` summary node from `wake` into its two halves, down to the raw memories.
- **Subagents skip all of the above.** Parallel sessions on this machine are all you and may all write memories; a subagent is not, and must never run `memo` — it cannot judge what is already known, and its notes would arrive duplicated and incorrect. When you spawn one, write: `You are a subagent. Don't run memo.`
