---
name: client-hunt
description: Find small businesses with a broken, insecure, or old website, build each one a free homepage draft, write a short cold email that links to it, and send the emails the user approves from Gmail, with follow-ups. Use when the user wants cold outreach, cold email, to find clients, leads, or customers for web or design work, to email businesses, or says "client-hunt".
---

# Client hunt

The email sells the draft page, so it must name a real problem you checked. Never blast. Gmail allows 500 a day; mass sends get the account blocked. `send.py` caps at 30 a day.

Data: `~/.client-hunt/leads/<id>.json`. Key legend at the top of each script.

## Setup, once

`~/.client-hunt/.env` (chmod 600; never in `~/.agents`):

```
GMAIL_USER=...
GMAIL_APP_PASSWORD=...    # https://myaccount.google.com/apppasswords (needs 2-Step Verification)
FROM_NAME=54
ADDRESS=...               # CAN-SPAM needs a postal address in every email
```

## Cycle

1. `python3 ~/.agents/skills/client-hunt/find.py "<city, state>"`. US cities only (US law allows cold email; Nigeria's NDPA expects consent). OpenStreetMap is slow: 3 to 10 minutes. Output: score, problem codes, category, id, email, site.
2. Take the top 10. Check each claim yourself: `curl -sI --doh-url https://1.1.1.1/dns-query https://<host>`, then the same with `-sL http://<host> | grep -i viewport`. The local resolver fails at random and fakes "site down", so always pass `--doh-url`. Set `k` to `x` on any lead you cannot confirm, that is a chain, or whose email is on a dead domain. Old ISP mailboxes bounce: 2 of 2 `att.net` did on 2026-10-06.
3. Fill the page keys from `t` (their own site text). Do not invent services, awards, or prices. If `t` is empty, keep the copy plain.
4. `python3 ~/.agents/skills/client-hunt/render.py <id>...`, then commit and push `~/i/dump` (it deploys on push). Open each `u` to check it.
5. Write `j` and `m`, and set `k` to `q`.
6. `python3 ~/.agents/skills/client-hunt/send.py review > ~/.client-hunt/review.md`. The user approves. Set approved leads to `k=o`.
7. `python3 ~/.agents/skills/client-hunt/send.py` in the background.
8. Every day: `python3 ~/.agents/skills/client-hunt/send.py follow`. Any reply stops the follow-ups. The user answers replies.

## Email

- Subject: lowercase, 2 to 4 words, the business name. Example: `soto homepage`.
- Body: 4 lines at most. Line 1 names the problem you saw, the way a visitor sees it. Line 2 gives the draft link. Line 3 gives the offer. Line 4 asks one yes/no question.
- Problem lines:
  - `h`: When I open <host> in Chrome, it shows a "Not secure" warning next to the address.
  - `m`: On a phone, <host> loads as a shrunken desktop page, so people have to pinch and zoom.
  - `d`: I tried <host> today and it doesn't load.
  - `s`: <host> is built in Flash, which no browser has played since 2021, so visitors see a blank page.
  - `o`: <name> sends people to a Facebook page instead of its own website.
  - `y`: The footer on <host> still says © <year>, which can make people think you've closed.
- Offer: `I can finish it and put it live on your domain this week for $360 flat. No monthly fees.`
- `send.py` adds the sign-off, address, and opt-out line.

## Payment

Ask for half up front before the work. Gumroad pays out to Nigeria.
