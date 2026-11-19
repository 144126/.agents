---
name: split
description: Break a problem into smaller subproblems, one level deeper each time the user asks ("split", "split more", "deeper", "split 3"). Keeps a tree file and never says a problem is done, too small, or unsplittable. Use when the user wants a task, goal, question or bug decomposed, or invokes /split.
---

# split

Hard problems become easy once each part tracks one thing (Duncan, Neuron 2013: "It is trivial once effectively divided into component subproblems"). This skill does only the splitting. It never solves, ranks or plans unless asked.

## File

`~/search/split-<2-4 hyphenated words>.md`. One tree, nested `-` bullets, 2 spaces per level. Re-read it before every split. Keep editing the same file across the whole conversation.

## Each request

1. Find the **leaves** (bullets with no children). If the user names a branch, only its leaves.
2. Split every leaf into **2-5 children**. Each child must be:
   - one thing to do, check or answer, small enough to start today
   - inside the parent (doing all children = doing the parent, nothing missing, no overlap)
   - concrete: a verb plus an object, no "think about" or "consider"
3. `split N` repeats step 2 N times.
4. Reply: line 1 is the leaf count and depth (`41 leaves, depth 4`). Then show only the new level. Then the file link.

## Never stop

The user decides when splitting ends. You never do. When a leaf looks atomic, split along a different axis instead:

| Axis | Example: "send the email" |
|---|---|
| steps in time | open draft · write subject · write body · send |
| what can go wrong | wrong recipient · typo in name · missing attachment |
| inputs needed | address · facts to state · the ask |
| checks | reread aloud · confirm attachment · check tone |
| who / where | me now · reply from them · follow-up date |
| physical motions | open laptop · click compose · type `To:` |

Physical motions and single checks can always split further (finger, key, glance, confirm). So "can't split further" is never true. Never say it, never ask whether to continue, never add a "this is granular enough" note.

## Don't

- Re-split a level the user didn't ask for.
- Pad with near-duplicate children to hit a count. 2 real children beats 5 fake ones.
- Change existing bullets, unless the user asks.
