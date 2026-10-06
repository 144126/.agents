#!/usr/bin/env python3
# send.py review   print drafted leads (k=q) for the user to approve
# send.py          email approved leads (k=o), 1-3 minutes apart, CAP emails a day in total
# send.py follow   mark replies (r) and bounces (x), then follow up on day 3 and day 7
# ~/.client-hunt/.env: GMAIL_USER, GMAIL_APP_PASSWORD, FROM_NAME, ADDRESS
# keys added here: d first send date, z message id; agent writes j subject, m body (no sign-off)
import datetime, imaplib, json, os, pathlib, random, smtplib, sys, time
from email.message import EmailMessage
from email.utils import make_msgid

H = pathlib.Path.home() / '.client-hunt'
CAP = 30
F = H / '.env'
env = {**(dict(l.split('=', 1) for l in F.read_text().splitlines() if '=' in l) if F.exists() else {}), **os.environ}
FOOT = f"\n\n{env.get('FROM_NAME', 'Ed Hogan')}\ned.apexlinks.org\n{env.get('ADDRESS', '<ADDRESS>')}\nIf you'd rather not hear from me, just reply \"no\"."
FOLLOW = {'s': (3, '1', 'Just bumping this in case it got buried. The draft is still up: {u}'),
          '1': (7, '2', 'Last note from me. If now is not the right time, no problem. The draft stays up for another week: {u}')}
today = datetime.date.today()
log = H / 'sent.log'


def leads(k):
    for p in sorted((H / 'leads').glob('*.json')):
        l = json.loads(p.read_text())
        if l['k'] in k:
            yield p, l


def send(l, subject, body, reply=False):
    if sum(1 for x in (log.read_text().splitlines() if log.exists() else []) if x.startswith(str(today))) >= CAP:
        sys.exit(f'cap {CAP} reached today')
    m = EmailMessage()
    m['From'], m['To'], m['Subject'] = f"{env.get('FROM_NAME', 'Ed Hogan')} <{env['GMAIL_USER']}>", l['e'], subject
    if reply:
        m['In-Reply-To'] = m['References'] = l['z']
    else:
        l['z'] = m['Message-ID'] = make_msgid(domain='gmail.com')
    m.set_content(body + FOOT)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(env['GMAIL_USER'], env['GMAIL_APP_PASSWORD'])
        s.send_message(m)
    with log.open('a') as f:
        f.write(f"{today} {l['i']} {l['k']}\n")
    print(today, l['k'], l['i'], l['e'], flush=True)


mode = sys.argv[1] if len(sys.argv) > 1 else 'send'
if mode == 'review':
    for p, l in leads('q'):
        print(f"## {l['i']}\nTo: {l['e']}\nSubject: {l['j']}\nDraft page: {l['u']}\nWhy: {l['f']} {l['w']}\n\n{l['m']}{FOOT}\n")
elif mode == 'send':
    for n, (p, l) in enumerate(leads('o')):
        if n:
            time.sleep(random.randint(60, 180))
        send(l, l['j'], l['m'])
        l['k'], l['d'] = 's', str(today)
        p.write_text(json.dumps(l, indent=1))
elif mode == 'follow':
    im = imaplib.IMAP4_SSL('imap.gmail.com')
    im.login(env['GMAIL_USER'], env['GMAIL_APP_PASSWORD'])
    im.select('"[Gmail]/All Mail"', readonly=True)
    found = lambda q: bool(im.search(None, 'X-GM-RAW', f'"{q}"')[1][0].split())
    for p, l in leads('s1'):
        after = l['d'].replace('-', '/')
        if found(f"from:{l['e']} after:{after}"):
            l['k'] = 'r'
        elif found(f"from:mailer-daemon {l['e']} after:{after}"):
            l['k'] = 'x'
        elif (today - datetime.date.fromisoformat(l['d'])).days >= FOLLOW[l['k']][0]:
            send(l, 'Re: ' + l['j'], FOLLOW[l['k']][2].format(u=l['u']), reply=True)
            l['k'] = FOLLOW[l['k']][1]
            time.sleep(random.randint(60, 180))
        p.write_text(json.dumps(l, indent=1))
        print(l['k'], l['i'])
