---
name: premium-web-design
description: Design and build websites with award-tier ("Awwwards"-level) craft — concept-driven direction, editorial typography, choreographed motion, custom scroll feel, and obsessive detail. Use this skill whenever the user asks for a website, landing page, portfolio, hero, case study, or marketing page that should feel premium, high-end, luxury, exquisite, cinematic, unique, creative, "expensive", "not generic", "not like a template", or award-worthy — and even when they simply ask for a "really good", "beautiful", or "stunning" site without naming a standard. Also use it when the user complains an existing design looks generic, default, boring, cheap, or AI-generated and wants it elevated to studio quality.
---

# Premium Web Design

Build websites at the level of the world's best creative studios (Locomotive, Exo Ape, Obys, Active Theory, Basement, Hello Monday, Resn, Immersive Garden, Darkroom, Unseen). The kind that win Site of the Day: they look expensive, move like they have mass, and could not be mistaken for anyone else's work.

Premium is not one look. The studios above are one lineage — dark, editorial, motion-heavy — and this skill's default numbers lean that way, but restrained/light/Swiss and product-grade UI (Apple, Stripe, Linear, clean corporate) are equally award-tier and invert half those defaults. The concept decides which family; the constant across all of them is craft, restraint, and one idea executed totally. Read the numbers in `references/laws-and-math.md` as settings for the chosen concept, not as the definition of premium.

## The core equation: seed × system

Award-tier work = a unique creative seed multiplied by a rigorous craft system. Both are mandatory; neither is sufficient.

- The **system** is the long checklist of laws, math, and techniques in this skill. Follow only the system with no seed and you produce a fluent imitation of the genre — technically premium, creatively generic. A checklist executed without direction converges on the default.
- The **seed** is unique information extracted from the user. Their answers, obsessions, contradictions, and specifics are the only source of originality available to you. The user is the creativity seat. A seed without the system is an interesting mess.

So the process is always: interrogate deeply → synthesize one concept → execute the system in service of that concept → detail pass → kill test. Never skip the interrogation to get to the fun part. The interrogation *is* the fun part.

Important stance on the seed: the user's answers are raw material, not a spec. Do not transcribe answers into the design literally. Transform them. Amplify the strangest, most specific detail they give you. If they say the brand "feels like a cold morning swim," you don't put a photo of a lake in the hero — you make the palette glacial, the easing sharp then numb, the copy terse and bracing. Translate feelings into physics.

## Phase 1 — Interrogate the user (the seed extraction)

Read `references/interrogation.md` before asking anything — it holds the question bank, the "core eight" to cover, and the answers→parameters translation table. The build is one-shot, so keep seed extraction light: **if the request already carries a seed** (a feeling, subject, reference, constraint), take it and skip the interview. **If it doesn't**, ask a *few* high-leverage questions (3–6, batched by theme, forced choices — "museum at night or workshop at noon?" out-seeds "what vibe do you want?"), not a long questionnaire. **Never stall for a seed** — if the user gives little or declines ("just make it good"), self-seed from the subject's own world in a deliberate, non-obvious direction, state it in one paragraph, and build. A stated seed the user can react to beats questions they abandon.

## Phase 2 — Synthesize one concept

Compress everything learned into a single written concept before touching code:

1. **The sentence.** One sentence: "A site for [subject] that feels like [three adjectives], behaves like [metaphor], and will be remembered for [signature element]."
2. **Derive tokens from the sentence.** Palette (3–5 named hex values, near-neutrals not pure), two or three typefaces with roles, spacing scale, motion personality (fast+sharp / slow+heavy / liquid / mechanical), texture (grain? paper? glass? none?). Every token needs a one-line justification tracing back to the sentence. If you can't justify it from the concept, it's a default — replace it.
3. **The banned-defaults check.** AI-generated design clusters into recognizable defaults: cream background + high-contrast serif + terracotta accent; near-black + single acid-green/vermilion accent; broadsheet hairlines with dense columns; and the generic SaaS hero (big number, gradient blob, three-card feature row). These are only acceptable if the user explicitly asked. Otherwise, if your plan resembles any of them — or resembles what you'd produce for any similar brief — revise before building. Run the mental test: "would I have arrived here without this user's answers?" If yes, the seed isn't in the work yet.
4. **One signature.** Choose the single memorable element (an interaction, a type treatment, a transition, an object) and spend your boldness there. Keep everything around it disciplined. One loud thing in a quiet room reads expensive; five loud things read like a template store.

## Phase 3 — Build the systems, in this order

Read `references/laws-and-math.md` for every number, ratio, formula, and value. Build in this sequence because each layer constrains the next:

1. **Typography first.** Set the modular scale, the three registers (huge display / body / tiny labels), tracking, and leading. Type carries most of the premium signal; if type is wrong nothing else can save it.
2. **Space and grid.** Establish the 12-column grid and luxury-scale section spacing, then plan the deliberate breaks. Whitespace is the primary luxury signal — density is what cheapness looks like.
3. **Color and texture.** Restricted palette, near-black/near-white, grain layer, dithered gradients if any.
4. **Motion system.** Choose the easing family, duration bands, stagger interval, and scroll physics (lerp constant) as a *system* — one personality applied everywhere, derived from the concept's feeling. Motion is where "expensive" actually lives; default easings are where it dies.
5. **Layout composition.** Compose sections with asymmetry, overlap, and tension against the established grid.

## Phase 4 — Implement the signature techniques

Read `references/techniques.md` for concise implementations: smooth-scroll (lerp), masked line reveals, scroll-scrubbed animation, parallax, velocity skew, magnetic elements, custom cursor, underline wipes, marquees, grain, preloader, page transitions, and the WebGL layer. Pick the ones the concept calls for — techniques are vocabulary, not a quota. Every effect must be justifiable by the concept; an effect that exists to show off breaks the spell.

## Phase 5 — The detail pass

Walk `references/checklist.md` once against the built site — it's a short list of the high-leverage tells and the accessibility floor, the things actually worth catching before delivery (not an exhaustive audit). Premium reads as the accumulation of many small correct decisions; humans detect the total care level at a glance even when they can't name a single item. Fix what's cheap; note anything you deliberately skip and why.

## Phase 6 — The kill test

Before delivering, answer honestly:

- Could a template or a default-mode AI have produced this? (If plausibly yes: identify which parts, and push them further.)
- Does every major element trace back to the concept sentence?
- What is the one thing a visitor will describe to a friend? (If you can't name it, there's no signature.)
- Does anything stutter, jump, or use a default ease anywhere? One dropped frame or one `ease-in-out` default undoes the illusion.
- Squint test: does the hierarchy survive blurring? Contrast test: is there one dominant scale relationship per view?
- Is the strangest thing the user told you visibly alive somewhere in the work?

If the design fails the kill test, iterate before presenting. Presenting a generic draft of a premium brief is the one unrecoverable move.

## Quality floor (never traded away for aesthetics)

Respect `prefers-reduced-motion` (wrap all non-essential animation; provide a working static experience). Keep 60fps: animate only `transform` and `opacity`, never layout properties. Fully responsive to 360px — the mobile experience is designed, not shrunk. Visible keyboard focus states, styled to match the direction. Real `alt` text, semantic HTML under the flash. Legible body text (≥16px, adequate contrast) even when display type takes risks. Graceful degradation when JS/WebGL is unavailable. The floor is invisible until it's missing — and when it's missing, "premium" collapses into "fragile".

## Scope notes

- For elevating an existing design rather than building new: run the interrogation about what it *should* feel like, diagnose against the checklist, then apply Phases 2–6 to the delta.
- For single components (a hero, a nav, a footer): same process, compressed — a three-question micro-interrogation, one concept sentence, then build with the full system.
- Match ambition to context: a quick prototype gets the type/space/motion laws and a light detail pass; a flagship build gets everything including the WebGL layer.
