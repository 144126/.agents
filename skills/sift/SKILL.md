---
name: sift
description: Trim a pile of search-result URLs down to the pages worth reading. The agent searches with its own native web search, hands every URL to sift, and local Julia-1 judges each page (relevant, worth reading, primary, citable). Sift prints only the URLs that pass. Use when the user says sift or julia research, or when a search returns more pages than the agent should read.
---

# sift

1. Search with your native web search tool. Collect every result URL (many queries, many hits).
2. Run sift on all of them:

```
sift "<research question>" URL1 URL2 ...
printf '%s\n' URL1 URL2 ... | sift "<research question>"
```

3. Read only the URLs it prints, with your native fetch tool. Output is best first, one URL per line. Logs go to stderr.

## Flags

```
--max N      print at most N urls
--scores     print julia scores after each url (tab separated)
```

Sift fetches pages itself over plain HTTP and drops pages with under 250 chars of text. Pages that block bots or need JavaScript come back empty and are dropped; if a URL you know matters is missing, fetch it yourself.

If `sift` is not on PATH: `python3 ~/.agents/skills/sift/sift.py`.

Julia needs the decision-julia venv (`~/work/decision-julia/.venv-julia/bin/python`). Override with `JULIA_PYTHON`. Model dir is `~/models/julia-1` (`JULIA_DIR`). Julia loads on CPU, so expect a few seconds per page.
