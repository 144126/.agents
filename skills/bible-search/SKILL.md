---
name: bible-search
description: Semantic search over the Bible (Young's Literal Translation) via a live API backed by a state-of-the-art embedding model. Use whenever a user asks about scripture, wants to find or quote a passage, locate a story or theme, compare doctrines, or retrieve biblical text by meaning rather than from memory. Triggers on "Bible", "scripture", "verse", "passage", "what does the Bible say about", "find the story where", "quote from", book names (Genesis, Psalms, Matthew, etc.), or any request to locate something in the Bible.
---

# Bible semantic search

When you need anything from the Bible, **do not quote from memory**. Query the live API. It
returns real YLT text, so you can quote scripture exactly instead of paraphrasing.

## The endpoint

`GET https://ver.apexlinks.org/api/search` — no auth, no key.

| param | meaning |
|---|---|
| `q` | required. The natural-language query. |
| `v` | flag. Return single verses. **This is the default and the one to use.** |
| `c` | flag. Return the whole chapter each hit sits in. |
| `b` | optional. Restrict to a book, e.g. `b=Psalms`. |
| `x` | optional. Restrict to a chapter number, e.g. `x=3`. |

Pass at most one of `c` or `v`. Passing both is a 400. Passing neither gives verses.
Flag values are ignored, so `?v` and `?v=` are the same.

```bash
# verses (use this)
curl -s -G 'https://ver.apexlinks.org/api/search' \
  --data-urlencode 'q=a righteous man persecuted for doing good' --data-urlencode 'v='

# whole chapters, for when the user wants the story around the hit
curl -s -G 'https://ver.apexlinks.org/api/search' \
  --data-urlencode 'q=the guy who went to heaven on horses' --data-urlencode 'c='
```

Response, both modes: `{ "r": [ { "b": "Psalms", "c": 34, "v": 19, "t": "…", "s": 0.83 } ] }`

- `b` book, `c` chapter, `v` verse, `t` the text, `s` similarity.
- Verse mode: `t` is one verse. Cite it as `Book c:v`.
- Chapter mode: `t` is the whole chapter, joined. `v` is still the verse that matched, so
  cite that verse and use the rest for context.
- Ten hits maximum. There is no limit parameter.

## Use verse mode

Both modes rank by the same verse search. Chapter mode only widens the text it returns.
Verse mode measured 9/10 top-1 on vague story queries where chapter-level embeddings
managed 7/10, so nothing is gained by reaching for `?c` unless you want the surrounding
narrative to read.

## Why you can be creative with the query

The query is embedded with a state-of-the-art model. It captures meaning, not keywords, so
you are not limited to words that appear in the text. Search the way a person would talk
about the idea:

- "someone wrestling with God and coming away with a new name" → Genesis 32
- "a proud king humbled and then restored" → Daniel 4
- "comfort for people mourning the death of someone they love"
- "love that is patient and kind, keeps no record of wrongs"

The sharper you describe the situation, feeling, or story beat, the better the match.

## How to use it well

- Start broad and plain. Add `b` or `x` only when you already have a hint.
- If the top hit is close but wrong, rephrase in everyday language. Do not stack keywords.
- If every score is low, the idea probably is not in the Bible. Say so. Do not force a match.
- Never present a passage as found unless it came back from the API.

## Careful: YLT is not the King James

The wording you remember is probably KJV, and YLT often differs enough to change an
argument. Genesis 22:1 reads "God hath **tried** Abraham", not tempted. 2 Samuel 24:1 reads
"an **adversary** moveth David", not the LORD. Always quote what the API returned.

## Related

For a long-running hunt for internal contradictions, use the `bible-contra` skill. It keeps
a full local copy of YLT and checks every quote against it.
