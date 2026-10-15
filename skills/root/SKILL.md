---
name: root
description: Peel any question to its floor - the layer where one more "why" changes the subject. Use when the user wants the root, core, fundamental, first-source, first-principles or "why all the way down" answer, or asks what any method must satisfy to work. Builds a ladder of layers, names the kind of floor it lands on, and kills a rival explanation at every layer. Do not stop at the first good story.
---

# root

Evidence machinery (search, fetch, pinpoint cites, grades, kill rounds, fallbacks) belongs to the `research` skill. Read it and use it. This skill owns only what research does not: the why-ladder, the floor test, and the rival at every layer.

Output: `~/search/<2-6 hyphenated words>-root.md`. Scratch: `/tmp/root-<slug>/`.

## 1. Frame

Write, in one line each:
- **Question** the exact thing, with each ambiguous word defined. Split lookalikes: behaviour vs preference, cause vs use, the trait vs the name of the trait.
- **Scope** which population, place, time, version. A root with no scope slides between "why humans" and "why this human".
- **Axis** which "why" is being asked. Tinbergen's four are different questions with different floors:
  `mechanism` (what makes it happen now) · `ontogeny` (how it develops in one life) · `function` (what it is selected for) · `phylogeny` (what it descends from).
  Peeling across axes without saying so is the most common false floor. Pick one, note the others under Open, or run one ladder per axis.
- **Kind** empirical ("why does X happen") or design ("what makes X work"). Design questions have a different floor - see §4.
- **Decision** what the user does with the answer, and which floor would change that.

## 2. Ladder

L0 is the observation as stated. Each rung answers "why that?" about the rung above. One rung = one line.

```
## Ladder
L0 <the observation>
L1 <why L0> — <grade> — rival: <named rival> — split by: <evidence that separates them>
L2 <why L1> — ...
```

Rules:
- A rung must be **inside a different object** from the rung above. If L2 is still a fact about the same thing as L1, it is a restatement, not a rung. Peel again.
- Every rung carries a **rival**: another explanation that predicts L0 just as well. Name it, then name the observation that would differ between them, then search for that observation. A rung with no rival has not been tested, only told.
- Every rung carries a `research` grade and pinned cites. No rung on plausibility alone.
- Build **two or more ladders from different starting observations** of the same phenomenon. Convergence on one floor is the strongest root evidence there is. Divergence means you are not at the floor yet - keep the divergence visible, do not pick a favourite.

## 3. False floors

Stop and peel again if the rung is any of these:

| False floor | Looks like | Why it is not a floor |
|---|---|---|
| Label | "it is evolution / culture / trauma" | names a source, states no mechanism |
| Tautology | "because it is adaptive / because people like it" | restates L0 with praise |
| Homunculus | "the brain decides", "the self wants" | moves the question into a box and leaves it there |
| Popular mechanism | dopamine, cortisol, oxytocin, polyvagal, mirror neurons, "the amygdala" | a molecule or region is a site, not a reason; nearly always a correlate measured downstream |
| Reification | naming a trait, then using the name as its cause | "she discloses because she is open" |
| Correlate as cause | the thing that co-occurs and was easiest to measure | no intervention or counterfactual behind it |
| Use as cause | what it is good for, offered as why it exists | function answers a different Tinbergen question |
| Single study | one lab, no preregistration, small n | `weak` in research's grades; never a floor |

## 4. The floor

Stop only when the next "why" **changes the subject** - it leaves the Scope, or crosses to a different Tinbergen axis.

Then name which **kind** of floor it is. A root answer that does not name its kind is not finished.

- `physical` a conservation law, thermodynamics, information limits, signal and noise
- `analytic` true by what the words mean; the question dissolves
- `selection` a reproductive or survival differential, with the selective environment stated
- `mathematical` a limit any system of this shape must obey (channel capacity, search cost, game equilibrium)
- `constraint` the floor is a **set** of conditions, not one reason - see below
- `contingent` a historical accident with no deeper reason; the honest floor for much of culture and language
- `absent` evidence runs out here. Say so and stop. Never invent a deeper layer.

**The floor may be plural.** Most behaviour is overdetermined: several causes each sufficient, or a conjunction where every part is needed. Do not force one indivisible reason - that fabricates. When the floor is a set, list the parts and mark which are **load-bearing**: remove it in reality or in a study and the phenomenon goes away. Cite the removal.

**Design questions** ("what makes X work", "how do I get Y") have an invariant floor, not a causal one: the constraint every working method satisfies and every failing method violates. Test it both ways:
- every known method that works satisfies it (name at least three, from different traditions)
- every known method that fails violates it (name at least two, including one that looks like it should work)
A constraint that nothing violates is vacuous. Cut it.

**Dual-use flag.** When the floor of a trust, persuasion or influence question is found, it is also the manual for faking the thing. Write one line naming the difference between meeting the need and simulating the signal of meeting it, and what gives the fake away over time. Required, not optional.

## 5. Report

```
# <question>
Scope / Axis / Kind / Decision
Floor: <one line> — kind: <physical|analytic|selection|mathematical|constraint|contingent|absent> — <grade>
Load-bearing: <the part that, removed, kills the phenomenon>
Fake vs real: <one line>
## Ladder A / Ladder B  (shortest first, floor at the bottom)
## Rivals killed  <rival — what killed it — cite>
## Rivals standing  <rival — what would split it — next query>
## Open
```

Checks before finishing:
- `grep -c '^L' <file>` equals the number of rungs that also match ` — rival: `
- at least two ladders, and one line saying whether they converge
- the floor's kind is one of the seven words
- `research`'s cite and grade checks pass on every rung
