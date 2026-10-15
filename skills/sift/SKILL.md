---
name: sift
description: Deep web research where Grok 4.6 on Amazon Bedrock Mantle plans, a bulk fetcher hauls hundreds of pages, and local Julia-1 judges every page. Grok never reads a page unless Julia says it must. Use when the user says sift, julia research, grok research, or wants source-triaged research.
---

# sift

Do not run the loop by hand. Do not dump page HTML into chat.

```
sift "<research question>"
sift --resume <slug>
```

Writes `~/search/<slug>.md` and `~/search/<slug>/state.json`. Resume is the same command with `--resume`. Ctrl-C finishes the current step and writes.

Grok states a premise and search queries. The fetcher searches many pages of each query and fetches every hit. Local Julia-1 answers, for each page: relevant? stance on the premise? must Grok read it? follow its links? primary? usable claim? Code uses those answers. Grok only sees Julia's cards plus the pages Julia marked `read`. Then Grok updates the report or asks for more searches.

## Flags

```
--premise TEXT     claim under test (else grok states one)
--slug NAME
--pages N          search pages per query (default 10)
--queries N        new queries per round (default 6)
--rounds N         plan/search rounds (default 6)
--max-sources N    unique url cap (default 360)
--read-limit N     full pages grok sees per turn (default 9)
--follow N         outbound links queued when julia says explore (default 6)
--no-follow
--infinite         ignore grok enough / round cap
--resume SLUG
```

If `sift` is not on PATH: `python3 ~/.agents/skills/sift/sift.py`.

Julia needs the decision-julia venv (`~/work/decision-julia/.venv-julia/bin/python`). Override with `JULIA_PYTHON`. Model dir is `~/models/julia-1` (`JULIA_DIR`).

Thin pages (<250 chars) and login/home URLs are dropped in code, not sent to Grok. Julia still misfires on stance; Grok should treat stance as a hint and only quote `read_pages`.

After a run, tell Ed search turns and sources fetched. Those numbers are in the markdown file. Do not read past `~/search`.
