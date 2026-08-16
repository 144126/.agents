---
name: bible-contra
description: Hunt internal contradictions in the Bible, forever, one gated pass at a time. Every quote is machine-checked against a local Young's Literal Translation, so a made-up verse cannot enter the list. Findings are refined, attacked, and hardened over time, not just piled up. Use when the user wants to find contradictions, conflicts, discrepancies, or errors in the Bible, wants to continue or resume the hunt, names a pass or a finding id like c042, or says "bcon". Works with any agent that can run bash.
---

# Bible contradiction hunter

You find places where the Bible contradicts itself. Only the obvious ones.

**One invocation = one pass.** A pass is small and finishes. The caller loops it. The
list gets better every pass, not only longer.

## Start every pass with this

```bash
bcon brief
```

It tells you the pass number, the mode, and the exact job. Do that job. Then:

```bash
bcon done
```

Never pick your own job. Never skip `brief`. Never skip `done`.

Set up once with `bcon init`. If `bcon` is not on your path, call
`python3 ~/.agents/skills/bible-contra/bcon.py` instead. Work lives in `~/i/me/bcon`,
or wherever `BCON_DIR` points.

The whole corpus is local, so the hunt never depends on the network. Search gets better
when the live index is up, and still works when it is not.

## The bar

A finding must be obvious to someone who is not clever and not interested. If you have
to explain it, it is not a finding.

**Internal only.** The two sides must both be Bible text. History, archaeology, science,
manuscript families, and "the original Greek" are all out of bounds. Nothing outside the
Bible enters the argument, on either side.

Strength, and the tier it lands in:

| | | |
|---|---|---|
| **5** | Two plain statements, same subject, one denies the other. Zero setup. | findings |
| **4** | One short sentence of setup. "Same king, two ages." | findings |
| **3** | Needs a few verses of context or a short chain. | candidates |
| **2** | Needs an actual argument. | candidates |
| **1** | Needs a paragraph, or an assumption. | not a finding, drop it |

Categories: `num` numbers that differ · `who` different actor or object · `when` dates and
ages · `where` different place · `order` order of events · `law` command against command ·
`claim` a general statement denied by another general statement.

### What is not a finding

- Two different events that merely resemble each other. Two cleansings of the temple are
  two cleansings, not a contradiction.
- One account being shorter. Silence is not denial.
- A general rule and a stated exception, when the text itself gives the exception.
- A number that is round in one place and exact in another.
- Poetry read as a claim about the world.
- Anything you can only argue from a translation other than the one in front of you.

## Never quote from memory

You will remember the King James wording. The corpus is Young's Literal Translation and it
is different. `bcon add` refuses any quote that is not really in the text, and prints the
real verse. That check is the point of this tool. Do not fight it — read the verse first.

Real example: 2 Samuel 24:1 in YLT says *an adversary moveth David*, not *the LORD moved
David*. The famous contradiction is not there in this translation. Check, always.

## Reading the text

```bash
bcon ref "2 Samuel 24:9"          # one verse, exact
bcon ref "Genesis 1:26-27"        # a range
bcon chapter 2 Kings 24           # a whole chapter, numbered
bcon grep "son of eight years"    # regex over all 31,102 verses, offline and free
bcon grep "reigned .* years" -b 2 Kings
bcon find "does God change his mind"           # semantic search, the whole Bible
bcon find "his age when he began to reign" -b "2 Chronicles" -x 36
```

`grep` is exhaustive and instant — use it for numbers, ages, names, and repeated formulas.
`find` understands meaning, not keywords, and returns 10 hits at most. Describe the idea the
way a person would say it. Use `find` to locate the *other side* of a conflict when you do
not know where it is.

### Two search engines, and why rows are labelled

The live index does not hold the whole Bible. `find` labels every row:

- `api` — the live semantic index. Real meaning matching. Covers only the books it holds.
- `local` — keyword search over the local corpus. Covers everything else, instantly.

`find` picks the right one per book and prints both blocks when a query spans the gap. Run
`bcon coverage` to re-probe which books the live index serves; the answer is cached in
`state.json`. `bcon local "<q>"` forces local search anywhere.

Local search is weaker — it matches words, not ideas. Give it the words that would actually
appear in the verse, not a paraphrase. "field of blood" beats "the place Judas' money bought".

## Recording a finding

```bash
bcon add --cat num --strength 5 \
  --conflict "the same census gives two different totals" \
  --a-ref "2 Samuel 24:9"    --a-q "Israel is eight hundred thousand men of valour" \
  --b-ref "1 Chronicles 21:5" --b-q "all Israel is a thousand thousand and a hundred thousand"
```

- `--conflict` is under 12 words, plain, and says what clashes. Not "a discrepancy exists".
- Quote the shortest span that still shows the clash. Trim every word that is not doing work.
- `add` refuses an exact duplicate and warns when a chapter pair is already covered.

Then: `bcon show c001` · `bcon set c001 --strength 4 --conflict "..."` ·
`bcon promote c001` · `bcon demote c001` · `bcon merge c002 c001` ·
`bcon kill c001 --why "..."`.

A kill is permanent and the reason is stored, so no later pass wastes time on it again.
Always give a real reason.

## The eight modes

`brief` cycles these. Each one is a different way to make the list better.

1. **parallel** — the same event told twice. Diff the two accounts line by line. This is
   where most real findings are. The brief names the exact pair.
2. **number** — sweep one family of numbers with `grep` and cross-check every one.
3. **theme** — probe one general claim, then search its denial.
4. **sweep** — new ground, chapter by chapter, in yield order. Mark it with `bcon cover`.
5. **lead** — work the queue. Close each with `bcon lead done <n>`.
6. **deepen** — take the least-touched findings and sharpen them. Shorter quotes, sharper
   conflict line, better verse pair if one exists.
7. **attack** — try to destroy your own findings.
8. **tidy** — `verify`, `dupes`, review candidates, `stats`.

After three passes with nothing new, the cycle drops sweeping and spends itself on depth.
That is intended. A tighter list of 80 beats a sloppy list of 400.

## Attack mode is what makes this get deeper

For each finding, write the strongest harmonisation an intelligent believer would give.
Then judge it by one rule:

> **A harmonisation only counts if the Bible itself supplies it.**

If it needs outside history, a lost manuscript, a scribal-error theory, or an appeal to the
original language, it does not count and the finding survives. If another verse plainly
supplies the answer, the finding dies or drops a level.

```bash
bcon attack c001 \
  --harm "one total counts the standing army and the other does not" \
  --verdict survives \
  --why "both verses say all Israel and neither mentions such a split"
```

`survives` raises the hardened count. `demote` drops one strength level. `kill` removes it.
A finding that has survived five attacks is worth more than a new one, and the rendered
document says so.

## Leaving a trail

Anything you notice but cannot finish this pass becomes a lead. This is how the hunt keeps
momentum across sessions and across different agents.

```bash
bcon lead "check every reign length in 2 Kings against 2 Chronicles"
bcon note "YLT wording for ages is 'a son of N years', not 'N years old'"
```

## Rules that do not bend

1. One pass per invocation. `brief`, work, `done`.
2. Every quote comes from `bcon ref`, `bcon chapter`, `bcon grep`, or `bcon find`. Never from
   your own memory of the Bible.
3. Both sides must be Bible text. No outside information, ever, on either side.
4. If it needs explaining, it is a candidate at best.
5. Kills need a reason. Leads get queued, not forgotten.
6. Do not edit `findings.jsonl`, `candidates.jsonl`, `state.json`, `FINDINGS.md`, or
   `CANDIDATES.md` by hand. The tool owns them. `FINDINGS.md` is regenerated every pass and
   hand edits are lost.
7. Report contradictions in the text. Do not argue about faith, and do not editorialise in
   the `--conflict` line.

## Running it forever

Any agent, one pass at a time:

```
bcon brief   →   do the job   →   bcon done   →   repeat
```

Unattended, with whatever CLI agent you have:

```bash
~/.agents/skills/bible-contra/loop.sh 50        # 50 passes
BCON_AGENT="opencode run" ~/.agents/skills/bible-contra/loop.sh
```

In Claude Code: `/loop /bible-contra`.

Where things are: `FINDINGS.md` is the deliverable. `CANDIDATES.md` is the holding pen.
`rejected.jsonl` is the graveyard with reasons. `log.md` is the running notebook.
Every pass is a git commit, so the refinement history is the repo history.
