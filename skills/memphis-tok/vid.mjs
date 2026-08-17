#!/usr/bin/env node
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const [cmd, spec_path] = process.argv.slice(2);
const key = process.env.OPENROUTER_API_KEY;
if (!key) die('OPENROUTER_API_KEY is not set');
if (!cmd || !spec_path) die('usage: vid.mjs key|gen|burn <spec.json>');

const spec = JSON.parse(readFileSync(spec_path, 'utf8'));
const brand = JSON.parse(readFileSync(join(here, 'brand', `${spec.brand}.json`), 'utf8'));
const out = resolve(dirname(spec_path), 'out');
mkdirSync(out, { recursive: true });
const p = (suffix) => join(out, `${spec.id}${suffix}`);

const dur = spec.dur ?? 9;
const hexes = brand.palette.join(', ');

const STYLE = `flat vector motion graphic, corporate memphis illustration, strictly 2D.
figures: tiny heads, no facial features, long noodle limbs with rounded bends, oversized hands, blocky torsos, skin filled with a flat brand colour, never a human tone.
fills: solid flat colour only. no gradient, no shading, no texture, no outline, no drop shadow, no ambient occlusion, no lens flare, no depth of field.
background: one flat colour plus large geometric shapes running off canvas, circles, arcs, quarter rounds, thick bars.
palette, use only these and nothing else: ${hexes}.
absolutely no text, no letters, no numbers, no signage, no logo anywhere in frame.`;

const MOTION = `motion: shapes cut and slide on hard eases, figures hold two or three poses, no realistic in-betweens, no camera dolly, no parallax, no zoom. 24fps, seamless loop, the final frame returns to the opening frame.`;

const NEG = `photoreal, 3d render, cinematic lighting, film grain, human skin tone, faces, eyes, text, letters, numbers, watermark, live action, gradient, drop shadow`;

const api = async (path, init = {}) => {
	const r = await fetch(`https://openrouter.ai/api/v1${path}`, {
		...init,
		headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', ...init.headers }
	});
	const t = await r.text();
	let j;
	try {
		j = JSON.parse(t);
	} catch {
		die(`${path} -> ${r.status} ${t.slice(0, 300)}`);
	}
	if (j.error) die(`${path} -> ${JSON.stringify(j.error).slice(0, 400)}`);
	return j;
};

if (cmd === 'key') {
	const prompt = `${STYLE}\n\nvertical 9:16 poster frame. ${spec.shot}\n\nthis is a single still, the opening frame of a looping animation. leave the upper third and lower quarter visually calm so captions can sit there. do not draw any text.`;
	const j = await api('/chat/completions', {
		method: 'POST',
		body: JSON.stringify({
			model: brand.image_model ?? 'google/gemini-3-pro-image',
			messages: [{ role: 'user', content: prompt }],
			modalities: ['image', 'text']
		})
	});
	const url = j.choices?.[0]?.message?.images?.[0]?.image_url?.url;
	if (!url) die(`no image returned: ${JSON.stringify(j).slice(0, 400)}`);
	writeFileSync(p('-key.png'), Buffer.from(url.split(',')[1], 'base64'));
	console.log(p('-key.png'));
}

if (cmd === 'gen') {
	const kf = p('-key.png');
	const model = spec.model ?? brand.video_model ?? 'alibaba/wan-2.7';
	const body = {
		model,
		prompt: `${STYLE}\n\n${spec.shot}\n\n${MOTION}\n\naudio: ${spec.audio}`,
		duration: dur,
		aspect_ratio: '9:16',
		resolution: spec.resolution ?? '720p',
		generate_audio: true
	};
	if (spec.seed !== undefined) body.seed = spec.seed;
	if (model.startsWith('alibaba/wan'))
		body.provider = {
			options: {
				'atlas-cloud': { parameters: { negative_prompt: NEG, prompt_extend: false, audio: true } }
			}
		};
	else body.prompt += `\n\navoid: ${NEG}`;
	if (existsSync(kf)) {
		const u = `data:image/png;base64,${readFileSync(kf).toString('base64')}`;
		body.frame_images = [
			{ type: 'image_url', image_url: { url: u }, frame_type: 'first_frame' },
			{ type: 'image_url', image_url: { url: u }, frame_type: 'last_frame' }
		];
	}
	const bal = (await api('/key')).data.limit_remaining;
	console.error(`${body.model} ${dur}s ${body.resolution} — balance $${bal}`);
	const job = await api('/videos', { method: 'POST', body: JSON.stringify(body) });
	console.error(`job ${job.id}`);
	for (;;) {
		await new Promise((r) => setTimeout(r, 15000));
		const s = await api(`/videos/${job.id}`);
		console.error(`  ${s.status}`);
		if (s.status === 'completed') break;
		if (['failed', 'cancelled', 'expired'].includes(s.status))
			die(`${s.status}: ${JSON.stringify(s.error ?? {})}`);
	}
	const r = await fetch(`https://openrouter.ai/api/v1/videos/${job.id}/content?index=0`, {
		headers: { Authorization: `Bearer ${key}` }
	});
	writeFileSync(p('-raw.mp4'), Buffer.from(await r.arrayBuffer()));
	console.log(p('-raw.mp4'));
}

if (cmd === 'burn') {
	const font = (f) => `data:font/woff2;base64,${readFileSync(f).toString('base64')}`;
	const cards = [...spec.captions.map((c) => card(c)), endcard()];
	const pngs = cards.map((html, i) => {
		const h = p(`-c${i}.html`);
		const g = p(`-c${i}.png`);
		writeFileSync(h, html);
		execFileSync(brand.chromium ?? 'chromium', [
			'--headless=new',
			'--disable-gpu',
			'--hide-scrollbars',
			'--force-device-scale-factor=1',
			'--default-background-color=00000000',
			'--window-size=1080,1920',
			`--screenshot=${g}`,
			`file://${h}`
		]);
		return g;
	});

	const times = [...spec.captions.map((c) => c.t), [dur - 1.6, dur]];
	const inputs = pngs.flatMap((g) => ['-i', g]);
	let chain = `[0:v]scale=1080:1920:flags=lanczos,setsar=1[v0];`;
	times.forEach(([a, b], i) => {
		chain += `[v${i}][${i + 1}:v]overlay=0:0:enable='between(t,${a},${b})'[v${i + 1}];`;
	});
	chain = chain.slice(0, -1);

	execFileSync(
		'ffmpeg',
		[
			'-y',
			'-i',
			p('-raw.mp4'),
			...inputs,
			'-filter_complex',
			chain,
			'-map',
			`[v${times.length}]`,
			'-map',
			'0:a?',
			'-t',
			String(dur),
			'-c:v',
			'libx264',
			'-crf',
			'18',
			'-preset',
			'slow',
			'-pix_fmt',
			'yuv420p',
			'-c:a',
			'aac',
			'-b:a',
			'192k',
			'-movflags',
			'+faststart',
			p('.mp4')
		],
		{ stdio: 'inherit' }
	);
	console.log(p('.mp4'));

	function shell(body) {
		return `<meta charset="utf-8"><style>
@font-face{font-family:d;src:url('${font(brand.fonts.display)}') format('woff2-variations');font-weight:200 800}
@font-face{font-family:s;src:url('${font(brand.fonts.sans)}') format('woff2-variations');font-weight:400 700}
@font-face{font-family:m;src:url('${font(brand.fonts.mono)}') format('woff2')}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:transparent}
body{display:flex;flex-direction:column;justify-content:flex-start;padding:156px 56px 0;font-family:s}
.slab{background:${brand.paper};padding:36px 40px 40px;border:1px solid ${brand.rule};border-top:8px solid ${brand.seal}}
.lbl{font-family:m;font-size:23px;letter-spacing:.16em;text-transform:uppercase;color:${brand.muted};margin-bottom:22px}
.big{font-size:74px;line-height:1.08;letter-spacing:-.03em;font-weight:700;color:${brand.ink};white-space:pre-line}
.mark{color:${brand.seal}}
</style>${body}`;
	}
	function card(c) {
		return shell(
			`<div class="slab">${c.label ? `<div class="lbl">${c.label}</div>` : ''}<div class="big">${c.line.replace(/\*(.+?)\*/gs, '<span class="mark">$1</span>')}</div></div>`
		);
	}
	function endcard() {
		return shell(`<div class="slab" style="text-align:center">
<div class="lbl">${brand.endcard_label}</div>
<div style="font-family:d;font-size:72px;line-height:1.04;letter-spacing:-.025em;color:${brand.ink}">${spec.endcard}</div>
<div class="lbl" style="margin:22px 0 0">${brand.endcard_sub}</div></div>`);
	}
}

function die(m) {
	console.error(m);
	process.exit(1);
}
