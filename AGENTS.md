# General

- never markdown format links

- global AGENTS.md: this file at ~/.agents/AGENTS.md — ~/.config/opencode/AGENTS.md is a symlink here. always edit this one, not the symlink target.
- commands: ~/.config/opencode/commands/
- skills: ~/.agents/skills/*/SKILL.md — all skills live here
- SEARCH NET FIRST — at ANY unexpected outcome, error, warning, or even the slightest issue, stop and search the net for the best way forward before taking any action
- whenever necessary run `source ~/.bashrc` to pick up new aliases/config
- always code with extreme simplicity; be minimalist
- speak extremely concisely; explain things like i'm 9 years old
- never run `npm run build`
- always use `pnpm` over npm/npx; never use npx directly
- portfolio: ed.apexlinks.org
- resume: https://registry.jsonresume.org/144126?theme=developer-mono
- resume source: GitHub Gist (id 70cba709) with file resume.json. Edit/view via `gh gist view 70cba709 --filename resume.json` and `gh gist edit 70cba709 <file>`

# Rules for software/web dev projects/folders

##  Code Style

- Naming: always snake_case for vars/functions; make db payload, type defs, request JSON and page load return value keys always single letters.
- DB/Qdrant: Multi-tenancy, single collection 'i'; tenant-id on payload field `s`
- Conciseness: no vars for single-use; code minimally
- never start the dev server
- for nodejs projects: if `.dev-logs/server.log` exists, read it (tail) before diagnosing any server-related issue — it contains the live dev server output
- after every code change on a nodejs project, always check `.dev-logs/server.log` for any new SSR/compile/runtime errors before declaring done
- always perfectly follow the design system outlined in the repo's DESIGN.md and/or src/app.css.
- if there is a src/app.css, never, ever use raw css values. always use the variables described in src/app.css, to keep styles consistent with the repo's design system
- where necessary (e.g for non-trivial updates), always write failing unit and e2e tests before implementing a feature/fix and then run tests after implementing
- fonts go in static/fonts

## Tailwind v4 + SvelteKit

1. `deno add npm:tailwindcss npm:@tailwindcss/vite`
2. In `vite.config.ts`, add `import tailwindcss from '@tailwindcss/vite'` and prepend `tailwindcss()` to plugins array
3. Create `src/app.css` with `@import "tailwindcss"`
4. In `src/routes/+layout.svelte`, add `import '../app.css'`
5. Customize theme via `@theme` in `app.css` (no tailwind.config.js needed)
6. For dark mode, add `@custom-variant dark (&:is(.dark *));` to `app.css`
7. In `<style>` blocks, use `@reference "tailwindcss";` to access theme tokens

## Git Workflow

- before every code change turn: `git add .; git commit -m"before AI agent {short_update_name} update. agent: {your name}"; git push`
  - short update name ≤3 words; don't worry if this push fails, the commit is what matters
- after every edit turn: `git add .` and make a long commit exhaustively explaining every change in detail, then run `git push`

<!-- codebase-memory-mcp:start -->
# Codebase Knowledge Graph (codebase-memory-mcp)

This project uses codebase-memory-mcp to maintain a knowledge graph of the codebase.
ALWAYS prefer MCP graph tools over grep/glob/file-search for file/function/class discovery.

If the current project dir isn't indexed yet, index it first via `codebase-memory-mcp index_repository(repo_path="<path>")`.

## Priority Order
1. `search_graph` — find functions, classes, routes, variables by pattern
2. `trace_path` — trace who calls a function or what it calls
3. `get_code_snippet` — read specific function/class source code
4. `query_graph` — run Cypher queries for complex patterns
5. `get_architecture` — high-level project summary

## When to fall back to grep/glob
- Searching for string literals, error messages, config values
- Searching non-code files (Dockerfiles, shell scripts, configs)
- When MCP tools return insufficient results

## Examples
- Find a handler: `search_graph(name_pattern=".*OrderHandler.*")`
- Who calls it: `trace_path(function_name="OrderHandler", direction="inbound")`
- Read source: `get_code_snippet(qualified_name="pkg/orders.OrderHandler")`
<!-- codebase-memory-mcp:end -->

## Cloudflare / Wrangler secrets store

- Read secrets/var bindings ONLY via SvelteKit's `$env/dynamic/private`, exactly like this:
  ```ts
  import { env } from '$env/dynamic/private';
  const id = env.GOOGLE_ID;            // plain [vars] / per-Worker secrets: sync string
  const sk = await env.SECRET.get();   // Secrets Store bindings: async object
  ```
- Secrets Store bindings (declared under `secrets_store_secrets`) are **async**: always `await env.KEY.get()`. Plain `[vars]` and per-Worker secrets are synchronous `env.KEY`. NEVER wrap in a helper, NEVER fall back to `event.platform?.env`, NEVER keep a local `env_val(env, 'KEY')` shim.
- Local dev: remote Secrets Store secrets are NOT readable locally. To test the API locally use `wrangler dev` with local secrets created via `wrangler secrets-store secret create <store_id> --name KEY --scopes workers` (no `--remote`); plain `[vars]` still load from `.dev.vars`/`.env`.
- Declare production secrets in `wrangler.toml`/`wrangler.jsonc` under `secrets_store_secrets: [{ binding, store_id, secret_name }]`; plain non-secret config goes under `[vars]`.
- SvelteKit → Cloudflare first deploy: `pnpm install` fails with "packages field missing or empty" when `pnpm-workspace.yaml` has `allowBuilds` but no `packages`. Always put `packages: ['.']` in `pnpm-workspace.yaml` next to the `allowBuilds` block (esbuild/workerd/sharp) — without it pnpm aborts install and (in v10/v11) also blocks the native build scripts the build needs.
- SvelteKit → Cloudflare: **never put `wrangler types` in the `build` script** (`package.json`). Keep `build` as `vite build` only. `wrangler types --check` falsely flags the generated `worker-configuration.d.ts` as out of date in Cloudflare Workers Builds (no `.dev.vars`, different wrangler/workerd version than local) and `wrangler types` alone also breaks builds. If you ever see `wrangler types` / `wrangler types --check` in a SvelteKit Cloudflare project's `build` script, remove it; also remove it if the user reports ANY deployment issue that may involve wrangler types.

# Clone Convention

When cloning a GitHub repository, always place it at `~/i/<org-or-user>/<repo-name>`.

Examples:
- `gh repo clone obsidianmd/obsidian-releases` → `~/i/obsidianmd/obsidian-releases`
- `gh repo clone user/project` → `~/i/user/project`
