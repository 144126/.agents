#!/usr/bin/env python3
# find.py "<city, state>" -> new leads in ~/.client-hunt/leads/<i>.json, printed best first
# lead keys: i id, n name, e email, w website, p phone, a address, o hours, r city, c category,
#   f problem codes, s score, t site text, k status
# f: d site down, s built in Flash, o only a social page, h no https, m not phone friendly, y old copyright year
# k: n new, q drafted, o approved, s sent, 1 follow-up 1 sent, 2 follow-up 2 sent, r replied, x dead
import json, pathlib, re, socket, ssl, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

D = pathlib.Path.home() / '.client-hunt' / 'leads'
UA = {'User-Agent': 'client-hunt/1 (+https://ed.apexlinks.org)'}
BROWSER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
SOCIAL = ('facebook.com', 'instagram.com', 'yelp.com', 'linktr.ee', 'business.site', 'business.page', 'nextdoor.com')
PARKED = ('domain is for sale', 'buy this domain', 'domain may be for sale', 'parked free', 'account suspended', 'account has been suspended', 'this site is currently unavailable', 'hugedomains', 'sedoparking', 'site not found', 'location.href="/lander"', '<title>nexcess</title>', 'welcome to nginx', 'apache2 default page', 'future home of something quite cool', '<title>index of /')
POINTS = {'d': 3, 's': 3, 'o': 3, 'h': 2, 'm': 2, 'y': 1}
AMENITY = {'dentist', 'veterinary', 'restaurant', 'cafe', 'car_wash', 'driving_school', 'doctors', 'clinic', 'childcare', 'bar', 'fast_food'}
OFFICE = {'lawyer', 'accountant', 'estate_agent', 'insurance', 'architect', 'consulting', 'tax_advisor', 'financial', 'financial_advisor', 'surveyor', 'therapist', 'moving_company', 'company', 'it', 'photographer', 'travel_agent', 'notary'}


def doh(host, *a, **k):
    if re.fullmatch(r'[\d.]+', str(host)):
        return GAI(host, *a, **k)
    r = json.loads(urllib.request.urlopen(urllib.request.Request(f'https://1.1.1.1/dns-query?name={host}&type=A', headers={'accept': 'application/dns-json'}), timeout=15).read())
    ips = [x['data'] for x in r.get('Answer', []) if x['type'] == 1]
    if not ips:
        raise socket.gaierror(socket.EAI_NONAME if r['Status'] == 3 else socket.EAI_AGAIN, host)
    return GAI(ips[0], *a, **k)


GAI, socket.getaddrinfo = socket.getaddrinfo, doh


def get(url, data=None, h=UA, t=120):
    return urllib.request.urlopen(urllib.request.Request(url, data, h), timeout=t).read()


def category(g):
    for k in ('craft', 'shop', 'office', 'healthcare', 'amenity', 'leisure'):
        v = g.get(k)
        if v and (k in ('craft', 'shop') or (k == 'office' and v in OFFICE) or (k == 'healthcare' and v != 'hospital')
                  or (k == 'amenity' and v in AMENITY) or (k == 'leisure' and v == 'fitness_centre')):
            return v


def fetch(url):
    try:
        return 'ok', get(url, h=BROWSER, t=20)[:400000].decode('utf-8', 'ignore')
    except HTTPError as e:
        return ('gone' if e.code in (404, 410) else '?'), ''
    except Exception as e:
        r = getattr(e, 'reason', e)
        if isinstance(r, (ssl.SSLCertVerificationError, ConnectionRefusedError)) or (isinstance(r, ssl.SSLError) and 'ALERT' in str(r)):
            return 'nohttps', ''
        if isinstance(r, socket.gaierror) and r.errno == socket.EAI_NONAME:
            return 'nx', ''
        return '?', ''


def check(w):
    host = urllib.parse.urlsplit(w if '://' in w else 'http://' + w).hostname or ''
    if host.removeprefix('www.').endswith(SOCIAL):
        return host, 'o', ''
    st, html = fetch(f'https://{host}/')
    f = ''
    if st == 'nohttps':
        st, html = fetch(f'http://{host}/')
        f = 'h'
    if st in ('gone', 'nx'):
        return host, 'd', ''
    if st != 'ok':
        return host, None, ''
    low = html.lower()
    if any(p in low for p in PARKED):
        return host, 'd', ''
    if any(p in low for p in ('captcha', 'just a moment', 'cf-chl', 'sucuri', 'javascript is required')) or sum(ch < ' ' and ch not in '\t\n\r' for ch in html[:2000]) > 40:
        return host, None, ''
    if 'shockwave-flash' in low or '.swf"' in low:
        return host, 's', ''
    if not re.search(r'<meta[^>]+viewport', low):
        f += 'm'
    years = [int(y) for s in re.findall(r'(?:©|&copy;|&#169;|copyright)[^<]{0,40}', low) for y in re.findall(r'(?:19|20)\d\d', s)]
    if years and max(years) < 2020:
        f += 'y'
    text = re.sub(r'<(script|style|noscript|svg)[\s\S]*?</\1>', ' ', html, flags=re.I)
    return host, f, re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()[:2500]


def lead(x, city):
    g = x.get('tags', {})
    e = (g.get('email') or g.get('contact:email') or '').split(';')[0].strip().removeprefix('mailto:')
    w = g.get('website') or g.get('contact:website') or g.get('url') or ''
    c = category(g)
    if not (c and re.fullmatch(r'[^@\s]+@[^@\s]+\.\w+', e) and w):
        return None
    try:
        host, f, t = check(w)
    except Exception:
        return None
    if f is None or ('d' in f and e.split('@')[1].lower().removeprefix('www.') in host):
        return None
    s = sum(POINTS[k] for k in f)
    if s < 2:
        return None
    a = ' '.join(filter(None, [g.get('addr:housenumber'), g.get('addr:street'), g.get('addr:unit')]))
    a = ', '.join(filter(None, [a, g.get('addr:city'), ' '.join(filter(None, [g.get('addr:state'), g.get('addr:postcode')]))]))
    return {'n': g['name'], 'e': e, 'w': w, 'p': g.get('phone') or g.get('contact:phone') or '', 'a': a,
            'o': g.get('opening_hours', ''), 'r': city, 'c': c, 'f': f, 's': s, 't': t or g.get('description', ''), 'k': 'n'}


def main(city):
    D.mkdir(parents=True, exist_ok=True)
    old = [json.loads(p.read_text()) for p in D.glob('*.json')]
    seen = {v.lower() for l in old for v in (l['e'], l['w'])}
    cache = D.parent / f"osm-{re.sub(r'[^a-z0-9]+', '-', city.lower())}.json"
    found = json.loads(cache.read_text()) if cache.exists() else None
    if found is None:
        place = next(p for p in json.loads(get('https://nominatim.openstreetmap.org/search?format=json&limit=5&q=' + urllib.parse.quote(city))) if p['osm_type'] == 'relation')
        q = f'''[out:json][timeout:180];area(id:{3600000000 + int(place['osm_id'])})->.a;
    (nwr(area.a)[name][email][website][!brand];nwr(area.a)[name]["contact:email"]["contact:website"][!brand];);out tags center;'''
    for m in () if found else ('maps.mail.ru/osm/tools/overpass/api', 'overpass-api.de/api', 'overpass.kumi.systems/api', 'overpass.private.coffee/api') * 3:
        try:
            found = json.loads(get(f'https://{m}/interpreter', urllib.parse.urlencode({'data': q}).encode(), t=200))['elements']
            cache.write_text(json.dumps(found))
            break
        except Exception as e:
            print(m, e, file=sys.stderr)
    if found is None:
        sys.exit('every overpass mirror failed, retry later')
    todo = [x for x in found if not {(x['tags'].get('email') or '').lower(), (x['tags'].get('website') or '').lower()} & seen]
    with ThreadPoolExecutor(8) as pool:
        new = [l for l in pool.map(lambda x: lead(x, city), todo) if l]
    ids = {p.stem for p in D.glob('*.json')}
    for l in sorted(new, key=lambda l: -l['s']):
        if l['e'].lower() in seen:
            continue
        seen.add(l['e'].lower())
        base = re.sub(r'[^a-z0-9]+', '-', l['n'].lower()).strip('-')[:40] or 'lead'
        l['i'] = next(f'{base}-{n}' if n else base for n in range(99) if (f'{base}-{n}' if n else base) not in ids)
        ids.add(l['i'])
        (D / f"{l['i']}.json").write_text(json.dumps(l, indent=1))
        print(l['s'], l['f'], l['c'], l['i'], l['e'], l['w'])
    print(f'{len(found)} places, {len(todo)} unseen, {len(new)} leads', file=sys.stderr)


main(sys.argv[1])
