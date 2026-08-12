# The Interrogation — extracting the creative seed

The purpose of this interview is not requirements gathering. It is seed extraction: pulling enough specific, strange, emotionally true material out of the user that the design could only belong to them. Generic questions produce generic answers produce generic sites. So the questions below are engineered to bypass "clean and modern" answers and reach imagery, memory, contradiction, and taste.

## How to run it

1. **Take the seed that's already there first.** If the request already carries a feeling, subject, reference, or constraint ("a portfolio for my ceramics studio, cold and clinical") — that *is* the seed. Don't turn around and interview them; go build. Only ask for what's genuinely missing and load-bearing.
2. **When you must ask, ask few.** This is a one-shot build with a live user — a short exchange is fine, a long questionnaire is friction before they've seen anything. Pick 3–6 high-leverage questions (the core eight minus whatever's answered). One sharp forced-choice out-seeds five open blanks. Never dump the bank.
3. **Batch conversationally.** Deliver in one or two turns, grouped with a sentence of framing ("First, the feeling. Then the world it lives in."). Number them so answers are easy.
4. **Prefer forced choices.** Either/or provocations produce sharper seeds than open blanks, and they're easier for the user to answer. Mix ~half forced-choice, half open.
5. **Chase specifics.** When an answer contains a proper noun, a memory, a texture, a place, or an emotion — follow up on that one thing. One vivid specific outranks ten adjectives.
6. **Welcome contradictions.** "Warm but intimidating," "ancient but digital" — contradictions are the best seeds because resolving them forces an original design. Never smooth them out; design the tension.
7. **Record everything verbatim** before translating. The user's exact words often contain the copy voice for free.
8. **Self-seed rather than stall.** If the user gives little, declines ("just make it good"), or clearly wants output over an interview — don't block the build. Answer the core eight yourself from the subject's own world (its materials, tools, era, vernacular), state your direction in one paragraph, and proceed. A stated seed the user can react to beats a questionnaire they abandon. To keep a self-seed from defaulting: pull the concept from *outside* web design (a film's title sequence, a print layout, an architecture, a machine) and stack one arbitrary constraint (type only / one color / visible grid) — distance and constraint are what make an invented seed read as intentional instead of generic.

## The core eight (always cover these, by asking or inferring)

1. In one sentence: what is this, and what is the single job of this site?
2. Three adjectives it must feel like — and one adjective it must never feel like.
3. "This site behaves like a ___." (a film, a machine, a gallery at night, a printed book, an instrument, a storefront, a laboratory, a stage...)
4. Two references you love (any medium — sites, films, spaces, objects) and one anti-reference you'd be embarrassed to resemble.
5. Who is the one specific person this must impress, and what do they need to feel in the first five seconds?
6. Risk appetite: on a scale from "quietly perfect" to "genuinely strange," where should this sit?
7. What is the one thing a visitor should remember and describe to someone else?
8. Hard constraints: brand colors/fonts/logos that are fixed, content that exists, tech limits, deadline.

## The full question bank

### Feeling and atmosphere
- Is it loud or quiet? Fast or slow? Heavy or weightless? Warm or cold? (ask as pairs)
- What temperature is the brand, in degrees? (people answer this surprisingly precisely)
- If the site were lighting, is it noon sun, golden hour, museum spots, neon, or candlelight?
- What should a visitor's heart rate do: calm down, or speed up?
- Should it feel like being welcomed in, or like being allowed in?
- Dense like a workshop or empty like a chapel?
- Polished machine or human hand? Where exactly on that line?

### The world and its materials
- If the brand were a material, which: raw concrete, brushed steel, vellum, silk, glass, walnut, wet ink, static?
- What era does it secretly belong to? (1968 studio, 1994 terminal, 2050 lab, timeless...)
- What city, and what part of that city, at what hour?
- What sound plays in the background? What music genre is it, specifically?
- If it were printed, is it a broadsheet, a fashion magazine, a scientific paper, a zine, a hardcover novel, or a gallery catalog?
- What's the weather on this site?
- Name an object that embodies the brand. Describe why.

### Metaphor and behavior
- "The site behaves like a ___" — push for a second, weirder answer after the first.
- When the visitor scrolls, are they walking through a space, turning pages, operating a machine, or falling?
- Is the site a monologue, a conversation, or an exhibition?
- Should navigation feel like a menu, a map, a table of contents, or a control panel?
- If the homepage were a single camera shot, what's the shot? (wide establishing, macro close-up, slow dolly, hard cuts)

### Taste, references, and anti-taste
- Two things in any medium — film title sequence, album cover, building, garment, game — that feel right. Why?
- One competitor or common style that would embarrass you to resemble.
- A designer, artist, director, or studio whose taste you trust.
- What's the most beautiful website you've ever used — and the most annoying?
- Is there any visual cliché of your industry we should burn on sight? (Almost every industry has one; naming it is liberating.)

### Audience and occasion
- Who arrives here, from where, in what mood, on what device?
- Are they buying, judging, learning, or being seduced?
- What do they already believe about you that we must confirm — or destroy?
- What would make *them* screenshot it and send it to someone?

### Provocations and forced choices (pick a few — these are seed dynamite)
- Museum at night or workshop at noon?
- Scalpel or paintbrush? Ink or light? Stone or smoke?
- A whisper in a huge room, or a shout in a small one?
- Swiss precision or Italian drama?
- Would you rather visitors say "beautiful" or "how did they do that"?
- Should the site feel finished, or alive and slightly in motion?
- If forced: black site or white site? Then — what's the one color that interrupts it?
- Serif or sans for the voice? Now: what's the accent — mono, script, stencil, nothing?
- Does the visitor control the site, or does the site perform for the visitor?
- Kill one: photography, illustration, 3D, pure typography. Which survives till last?
- One word appears for a moment before anything else loads. What is the word?

### Memory and story (deepest seeds live here)
- What's the origin story detail nobody puts on the about page but everyone remembers when told?
- What did the founder's first workspace look like?
- What's a detail about the product/craft that only insiders notice?
- What's the most specific compliment you've ever received?
- If this company died tomorrow, what would the obituary's first line be?

### Constraints and pragmatics
- Fixed brand assets? Existing type licenses? Accessibility requirements beyond the floor?
- How much content actually exists (real copy, real photography) versus needs inventing?
- Update frequency — is this a living site or a monument?
- Performance/device realities of the audience?

## The translation table — answers → parameters

Never let a seed die as an adjective. Convert answers into concrete system values (see `laws-and-math.md` for the parameter definitions). Examples of the mapping logic — extend it, don't limit to it:

| Seed signal | Type | Space | Motion | Color/texture |
|---|---|---|---|---|
| Heavy, monumental, serious | Crushed leading (0.9), huge display (12–14vw), tight tracking (−0.04em) | Vast sections (200px+), few elements per view | Slow durations (1.2–1.6s), deep expo-out, low lerp k (~0.06) | Near-black field, one cold accent, heavy grain |
| Airy, light, optimistic | Lighter weights, generous leading (1.1 display), open tracking | Wide margins, floating elements, more sky than ground | Springy but soft, mid durations (0.8s), higher lerp k (~0.12) | Warm off-white, pale accents, faint grain |
| Precise, technical, engineered | Grotesque + mono labels, tabular numerals, visible grid lines | Strict 12-col alignment, exposed structure, crosshair marks | Short durations (0.3–0.6s), sharp power2/power3, tiny staggers (30ms) | Monochrome + one signal color, no texture |
| Human, crafted, warm | Editorial serif moments, optical quirks, hanging punctuation | Asymmetric, overlapping, imperfect-on-purpose | Eased like breathing, follow-through, 60–80ms staggers | Paper tones, ink black, tactile grain |
| Strange, artistic, avant-garde | Extreme scale jumps (30:1), experimental face for display only | Broken grid after establishing it, collisions as composition | Unexpected choreography, scroll-driven surprises, velocity skew | Unnatural pairing done twice (so it reads intentional) |
| Cold, exclusive, luxury | Thin/regular weights at huge sizes, wide-tracked tiny caps labels | 80–90% negative space, one element per viewport | Very slow reveals (1.4s+), long expo tails, no bounce ever | Deep neutrals, no accent or a metallic-adjacent one, silk-subtle motion |
| Fast, energetic, loud | Ultra-bold condensed display, tight everything | Denser rhythm, full-bleed alternating with tight columns | Quick cuts (0.25–0.4s), hard easings, marquees, kinetic type | High contrast, saturated accent used bravely, RGB-shift moments |

Two final translation rules: (1) the *anti-adjective* is as load-bearing as the adjectives — audit every decision against it; (2) whatever the strangest concrete detail was (the letterpress shop, the cold swim, the word before load), it must survive into the shipped site in a form the user can point at.
