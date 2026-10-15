---
name: web-build
description: Build Ed's websites and webapps with SvelteKit, TypeScript, pnpm, and Cloudflare. Use Qdrant when a database is needed. Use for new sites, landing pages, and webapps, or when Ed asks to use his usual web stack.
---

# Web build

- Always read the `feel` skill (`~/.claude/skills/feel/SKILL.md`) before building any website or interaction. Install: `git clone https://github.com/diip3sh/feel ~/.claude/skills/feel`.
- Build only what the request needs. Keep an existing project's stack unless asked to change it.
- Before product, naming, or design choices, read `~/ed.md` if present. Only on Ed's personal machine, read `~/me.md` if present for project names, paths, lowercase UI text, Svelte runes, Tailwind, fonts, and auth defaults. Else use the user's or team's conventions.
- Use SvelteKit, TypeScript, and pnpm. Start new projects with `pnpm dlx sv create <path> --template minimal --types ts --install pnpm`. Add prettier, eslint, playwright, tailwindcss, and the Cloudflare adapter through `pnpm dlx sv add`.
- `sv` 1.x scaffolds SvelteKit 3 (`#lib`, declared env vars; `$env/dynamic/private` is deprecated). For SvelteKit 2 one-shot: `pnpm dlx sv@0.17.1 create <path> --template minimal --types ts --add prettier eslint playwright tailwindcss="plugins:forms" sveltekit-adapter="adapter:cloudflare+cfTarget:workers" --install pnpm < /dev/null`.
- Paystack: checkout.paystack.com shows a Cloudflare check to headless Chrome. Test payments in test mode with `POST /charge` (card 4084084084084081, cvv 408, pin 0000) and your own `reference`. Starter businesses can't `POST /transfer` (`transfer_unavailable`).
- Cloudflare adapter dev: `$env/dynamic/private` reads `.env` and the shell, not `.dev.vars` (only `platform.env` reads that). One-off local override: `ADMIN=x pnpm dev`.
- Web push with text needs the subscription's `p256dh` + `auth` keys and an RFC 8291 `aes128gcm` body; check it with `http_ece` decrypt. Android Chrome files each site's notes at default importance: status-bar icon, no pop-up, and the site can't change it. Tell users: long-press a note, Settings, Pop on screen.
- Use `@sveltejs/adapter-cloudflare` for Cloudflare hosting. Follow the current [SvelteKit Cloudflare setup](https://svelte.dev/docs/kit/adapter-cloudflare); use the existing Workers or Pages target when present.
- Add Qdrant only when the app needs a database. Keep Qdrant calls and credentials on the server. Use an existing instance when available; follow the current [Qdrant docs](https://qdrant.tech/documentation/). Add search by meaning only when the request needs it.
- Keep database access in `src/lib/server/`. Keep each business rule in one owning module; routes call it and components display its results. Validate input and check access on the server.
- Follow the repo's design system and code rules. Use `creative` and `ui-ux` for design choices when available.
- Keep secrets out of browser code and git. Ignore `.env` and `.dev.vars`.
- Reuse a running dev server. If `.log` exists, check it before diagnosing server problems and after changes. Run the project's type check, build, and tests relevant to the change. View UI changes with an available browser tool before saying done; prefer `agent-browser` when installed.
- Ask before deployment or irreversible remote data changes unless already authorized. Commit and push only when requested.
