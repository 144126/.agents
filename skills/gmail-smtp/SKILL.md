---
name: gmail-smtp
description: Send email from Ed's 1440ir Gmail (1440ir@gmail.com) over SMTP from the CLI, using the app password in ~/.client-hunt/.env. Use when Ed asks to email from 1440ir, or a task needs a Gmail send.
---

# Gmail SMTP (1440ir)

Creds live in `~/.client-hunt/.env` (`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `FROM_NAME`). Never copy them into this skill or any repo.

```python
import os, smtplib, pathlib
from email.message import EmailMessage
env = dict(l.split('=', 1) for l in pathlib.Path('~/.client-hunt/.env').expanduser().read_text().splitlines() if '=' in l)
m = EmailMessage()
m['From'], m['To'], m['Subject'] = f"{env['FROM_NAME']} <{env['GMAIL_USER']}>", 'to@example.com', 'subject'
m.set_content('body')
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
    s.login(env['GMAIL_USER'], env['GMAIL_APP_PASSWORD'])
    s.send_message(m)
```

- Send only the exact email Ed approved. Sending is outward-facing.
- Gmail caps at 500 a day. Mass sends get the account blocked.
- Login fails (535): the app password is wrong or revoked. Make a new one at myaccount.google.com/apppasswords (needs 2-Step Verification).
