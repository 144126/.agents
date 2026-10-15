---
name: root
description: Peel any question to the indivisible first-principles reason. Use when the user wants the root, core, fundamental, first-source, or "why all the way down" answer. Do not stop at the first good story.
---

# root

Do not stop at a use, a correlate, or a popular mechanism. Peel until one more "why" is a different question.

1. Name the thing exactly. Split lookalikes (behaviour vs preference, cause vs use).
2. Write the current answer in one line. Ask "why that?" If the answer still sits inside the same object, peel.
3. Search the web for empirical claims. Read the pages, not just the snippets.
   PMC pages show a captcha. Open-access full text: `curl -s https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/fullTextXML | sed 's/<[^>]*>//g'`. Others (abstract only): `curl -s 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<pmid>&format=json&resultType=core'`.
   Reddit and most pages: `curl -sL -A 'Mozilla/5.0' '<url>' -o raw.html`, then `sed 's/<[^>]*>/ /g' raw.html > page.txt`. Quote only from raw text saved to a file, never from WebFetch output (a model rewrites it). Record 404s, 403 blocks and password gates as they are.
4. Write `~/search/<slug>.md`. Each round: keep only what the pages say; cut what they kill.
5. Stop only when the remaining "why" changes the subject (e.g. "why sex" after "why same-sex behaviour").
6. Answer is the floor, then the layers you peeled, shortest first.

Do not invent a deeper layer. If evidence ends, say so and stop.

# Traps (root research fan-out)
- Seed arXiv IDs from memory were wrong 4 times in one run. Before dispatch, check each: `curl -s https://arxiv.org/abs/<id> | grep -o '<title>[^<]*</title>'`. Authors: `grep -o 'citation_author" content="[^"]*"'`.
- Subagents share one WebSearch budget (200 calls). Thirteen workers used it up. Give each worker about 12 searches, and send curl-to-arXiv checks in Bash instead.
- A brief file path from an old session can vanish. Before dispatch, `ls` the path. Workers that cannot read it stop with BLOCKED and produce nothing.
- Check cited numbers against the abstract (`citation_abstract` meta). Mark any number found only in a snippet as UNVERIFIED.
