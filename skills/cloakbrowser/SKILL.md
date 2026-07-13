---
name: cloakbrowser
description: Use CloakBrowser with Stagehand to automate browser tasks behind bot detection (Cloudflare, reCAPTCHA, DataDome). CloakBrowser provides the stealth Chromium binary; Stagehand provides the AI-powered automation layer (act/extract/observe/agent). No raw Playwright calls.
references:
  - nodejs
---

# CloakBrowser + Stagehand

## Overview

[CloakBrowser](https://cloakbrowser.dev) provides a patched Chromium binary (58+ C++ patches) that passes bot detection. [Stagehand](https://stagehand.dev) provides AI browser automation (act/extract/observe/agent).

Shared boilerplate at `~/.cloakbrowser/index.js` — imports once, used by all agent scripts. Each agent writes its own runner to `/tmp/opencode/cloakbrowser/`.

## Shared Module (`~/.cloakbrowser/index.js`)

Exports `createStagehand(opts)` and `z` (zod). Available to all agents:

```javascript
import { createStagehand, z, writeAgentScript } from '/home/ed/.cloakbrowser/index.js';
```

### Options

| Option | Type | Default | Description |
|---|---|---|---|
| `headless` | bool | `false` | Run headless |
| `proxy` | string | — | `http://user:pass@host:port` |
| `userDataDir` | string | — | Persistent profile path |
| `fingerprint` | string | — | Pin fingerprint seed |
| `model` | string | `openai/gpt-4o` | LLM model |
| `selfHeal` | bool | `true` | Auto-retry failed actions |
| `args` | string[] | `[]` | Extra Chrome args |

### Returns `{ stagehand, page, z }`

## Per-Agent Script Pattern

```javascript
import { createStagehand } from '/home/ed/.cloakbrowser/index.js';
import { writeFileSync } from 'fs';

const script = `
import { createStagehand } from '/home/ed/.cloakbrowser/index.js';

const { stagehand, page, z } = await createStagehand({ proxy: 'http://...' });
await page.goto('https://target-site.com');
await stagehand.act('click the login button');
const data = await stagehand.extract('extract the title', z.object({ title: z.string() }));
console.log(data);
await stagehand.close();
`;

const fp = '/tmp/opencode/cloakbrowser/agent-123.mjs';
writeFileSync(fp, script, 'utf-8');
// Then: await import(fp) or pnpm exec node fp
```

## Stagehand Primitives

All operate on the stagehand instance against the active page.

### act()

```javascript
await stagehand.act('click the submit button');
await stagehand.act('fill the password field with %pw%', {
  variables: { pw: process.env.PASSWORD },
});
```

### extract()

```javascript
const data = await stagehand.extract(
  'extract the title and description',
  z.object({ title: z.string(), description: z.string().optional() }),
);
```

### observe()

```javascript
const actions = await stagehand.observe('find all navigation links');
if (actions.length) await stagehand.act(actions[0]);
```

### agent()

```javascript
const agent = stagehand.agent({
  model: 'google/gemini-3-flash-preview',
  mode: 'cua',
  systemPrompt: 'You are a helpful assistant.',
});
const result = await agent.execute({ instruction: '...', maxSteps: 15 });
```

## Stealth Best Practices

1. **Residential proxies** — datacenter IPs get blocked regardless of fingerprint.
2. **`headless: false`** — some detectors flag headless even with C++ patches.
3. **15+ seconds on reCAPTCHA pages** — solving too fast is detectable.
4. **Persistent profiles** (`userDataDir`) — incognito is detectable by BrowserScan.
5. **Pin fingerprint** with `fingerprint: '42069'` for repeatable identity.
6. **`observe()` before `act()`** on safety-critical flows.

## Gotchas

| Situation | Action |
|---|---|
| Binary download (~200 MB) | Pre-download: `pnpm exec cloakbrowser install` |
| Binary blocked (corp proxy) | Set `HTTP_PROXY` env var or place binary in `~/.cloakbrowser/` |
| LLM API key missing | Set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` env var |
| act() fails | `observe()` first, pass returned Action to act() |
| Self-healing | Enabled by default (`selfHeal: true`) |
| macOS arm64 | Fewer patches. Prefer Linux for production |
