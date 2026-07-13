---
name: bible-search
description: Semantic search over the Bible (Young's Literal Translation) via a live API backed by a state-of-the-art embedding model. Use whenever a user asks about scripture, wants to find or quote a passage, locate a story or theme, compare doctrines, or retrieve biblical text by meaning rather than from memory. Triggers on "Bible", "scripture", "verse", "passage", "what does the Bible say about", "find the story where", "quote from", book names (Genesis, Psalms, Matthew, etc.), or any request to locate something in the Bible.
---

# Bible Semantic Search

When you need anything from the Bible, **do not guess from memory** — query the live semantic search API. It returns real YLT chapter text, so you can quote scripture accurately instead of paraphrasing from training data.

## Endpoint
POST `https://ver.apexlinks.org/api/search`
- That is the live, deployed Worker (custom domain). No auth, no API key — open to all.
- Local fallback while developing: `pnpm build && wrangler dev`, then use `http://localhost:8787`.

Headers: `content-type: application/json`
Body:
```json
{ "q": "<natural-language query>", "b": "<optional book>", "c": "<optional chapter>" }
```

Example:
```bash
curl -s -X POST https://ver.apexlinks.org/api/search \
  -H 'content-type: application/json' \
  -d '{"q":"a father throwing a feast when his lost son finally comes home","b":"Luke"}'
```

Response:
```json
{ "r": [ { "b": "Luke", "c": 15, "t": "<full YLT chapter text>", "s": 0.83 } ] }
```
- `b` book, `c` chapter, `t` the full chapter text (Young's Literal Translation), `s` similarity score (higher = closer match).

## Why you can be bold and creative
The query is embedded with a **state-of-the-art embedding model (Qwen3-Embedding-8B, 4096 dimensions)**. It captures *meaning*, not keywords — so the search understands paraphrase, theme, emotion, situation, and doctrine. You are NOT limited to words that literally appear in the text.

Lean into that. Search the way a person would *talk about* the idea, not like a concordance:
- "someone wrestling with God and coming away with a new name" → Genesis 32
- "comfort for people mourning the death of someone they love"
- "a warning that trusting in riches is foolish"
- "the joy when the tabernacle is filled with God's glory"
- "a proud king humbled and then restored"
- "love that is patient and kind, keeps no record of wrongs" (thematic, cross-book)

Get specific, concrete, or even unusual — the better you describe the situation, feeling, or story beat, the sharper the match.

## How to use it well
- Start broad with a plain-language query. Only add `b` (book) or `c` (chapter) when you already have a hint.
- Results are **chapter-level**: the whole chapter is in `t`. Quote the relevant lines from what the API returns.
- If the top hit is slightly off, **rephrase in everyday language** rather than stacking keywords.
- If every score is low, the idea likely isn't present in YLT / the Bible — say so; don't force a match.
- Never present a passage as "found" unless it came back in the API response.
