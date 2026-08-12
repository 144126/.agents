# condense

Offline fact extractor for a single text block or file. Every claim is
quote-anchored to the source and gated (verbatim quote required, numbers must
sit in the quote, polarity must match).

```bash
export PATH="$HOME/.agents/skills/condense/bin:$PATH"
condense extract --file source.txt          # print the extract prompt
condense gate --source source.txt --claims facts.json --out facts.md
```

- Skill driver: `SKILL.md`
- Extract prompt: `references/extract_prompt.md`
- No API keys, no network.

For merging web search results into an audited ledger, use `condense-search`.
