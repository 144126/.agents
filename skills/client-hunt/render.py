#!/usr/bin/env python3
# render.py <id>... -> $CLIENT_HUNT_SITE/<id>/index.html, sets u in the lead
# page keys the agent adds to a lead: g headline, l lede, v services, b about, h accent hex (dark enough for white text)
import html, json, os, pathlib, sys

H = pathlib.Path.home() / '.client-hunt'
F = H / '.env'
NAME = {**(dict(l.split('=', 1) for l in F.read_text().splitlines() if '=' in l) if F.exists() else {}), **os.environ}.get('FROM_NAME', 'Gold Hogan')
SITE = pathlib.Path(os.environ.get('CLIENT_HUNT_SITE', pathlib.Path.home() / 'i/dump/static'))
BASE = os.environ.get('CLIENT_HUNT_URL', 'https://draft.apexlinks.org')
CSS = '''*{box-sizing:border-box;margin:0}body{font:17px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;color:#111;background:#fff}
.note{background:#111;color:#fff;font-size:13px;text-align:center;padding:8px 16px}.w{max-width:1040px;margin:0 auto;padding:0 20px}
header{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 0}.logo{font-weight:700;font-size:19px;letter-spacing:-.01em}
.btn{display:inline-block;background:var(--a);color:#fff;text-decoration:none;font-weight:600;padding:12px 20px;border-radius:10px;white-space:nowrap}
.ghost{background:none;color:#111;box-shadow:inset 0 0 0 1.5px #ddd}.hero{padding:72px 0 88px}
h1{font-size:clamp(38px,6vw,64px);line-height:1.05;letter-spacing:-.03em;max-width:15ch}.lede{font-size:20px;color:#555;max-width:42ch;margin:20px 0 32px}
.row{display:flex;gap:12px;flex-wrap:wrap}section{padding:72px 0;border-top:1px solid #eee}h2{font-size:28px;letter-spacing:-.02em;margin-bottom:28px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}.card{background:#f5f5f4;border-radius:14px;padding:22px;font-weight:600}
.card:before{content:"";display:block;width:28px;height:4px;border-radius:2px;background:var(--a);margin-bottom:14px}p{max-width:62ch;color:#333}
.info{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:24px}.info b{display:block;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#777;margin-bottom:6px}
.info a{color:#111}footer{padding:32px 0;color:#777;font-size:14px;border-top:1px solid #eee}'''

for i in sys.argv[1:]:
    f = H / 'leads' / f'{i}.json'
    l = json.loads(f.read_text())
    e = {k: html.escape(str(v)) for k, v in l.items() if isinstance(v, str)}
    tel = ''.join(c for c in l.get('p', '') if c.isdigit() or c == '+')
    call = f'<a class="btn" href="tel:{tel}">Call {e["p"]}</a>' if tel else f'<a class="btn" href="mailto:{e["e"]}">Email us</a>'
    info = [('Phone', f'<a href="tel:{tel}">{e["p"]}</a>' if tel else ''), ('Email', f'<a href="mailto:{e["e"]}">{e["e"]}</a>'),
            ('Address', e.get('a', '')), ('Hours', e.get('o', ''))]
    out = SITE / i / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>{e["n"]}</title><style>:root{{--a:{e.get("h", "#1d4ed8")}}}{CSS}</style></head><body>
<div class="note">Free homepage draft made by {NAME} for {e["n"]}. Not the official site.</div>
<div class="w"><header><div class="logo">{e["n"]}</div>{call}</header>
<div class="hero"><h1>{e["g"]}</h1><p class="lede">{e["l"]}</p><div class="row">{call}<a class="btn ghost" href="#contact">Hours and location</a></div></div>
{'<section><h2>What we offer</h2><div class="grid">' + ''.join(f'<div class="card">{html.escape(s)}</div>' for s in l['v']) + '</div></section>' if l.get('v') else ''}
{f'<section><h2>About</h2><p>{e["b"]}</p></section>' if l.get('b') else ''}
<section id="contact"><h2>Visit or get in touch</h2><div class="info">{''.join(f'<div><b>{k}</b>{v}</div>' for k, v in info if v)}</div></section>
<footer>© 2026 {e["n"]}</footer></div></body></html>
''')
    l['u'] = f'{BASE}/{i}'
    f.write_text(json.dumps(l, indent=1))
    print(l['u'])
