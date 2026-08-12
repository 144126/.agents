# Final pass — the things that actually get forgotten

This is short on purpose. It's a one-shot build; you won't run a 180-item audit, so this is only the high-leverage stuff: the details that break the premium feel when missed, and the floor you never ship without. The *numbers* live in `laws-and-math.md` — this list is just "did you remember to."

Walk it once before delivering. Fix what's cheap; note anything you deliberately skipped and why.

## Does it trace to the concept
- [ ] A one-sentence concept existed before code, and every major choice traces to it.
- [ ] The strangest thing the user gave you is visibly alive somewhere.
- [ ] It doesn't resemble the banned defaults (cream+serif+terracotta, dark+acid accent, gradient-blob SaaS hero) unless the user asked.
- [ ] One signature element carries the boldness; everything around it stays quiet.

## The premium tells (cheap to get wrong, obvious when wrong)
- [ ] Curly quotes and apostrophes — no straight-quote leaks.
- [ ] Off-black and off-white, never pure `#000` on `#FFF`.
- [ ] No default easings anywhere (no CSS `ease`/`ease-in-out`; `linear` only for marquees/spinners).
- [ ] Only `transform` and `opacity` animate; nothing drops frames.
- [ ] Hero type isn't the exhausted set (Inter/Poppins/Montserrat/Playfair-as-display) used untouched.
- [ ] Every interactive element has a designed hover **and** a matching focus state.
- [ ] Nothing shifts layout on hover; nothing shifts on load (reserve media space, metric-match fonts).
- [ ] Images enter with intent (mask/clip/scale-settle) behind a color/blur placeholder — never a white pop.
- [ ] Copy is terse and in-voice: no "Welcome to", no lorem; buttons say what they do.
- [ ] `::selection`, focus rings, scrollbar, 404, favicon, OG image — themed, not defaulted.

## The floor (never shipped without)
- [ ] `prefers-reduced-motion` gives a complete, good static site — not a broken or stripped one.
- [ ] Responsive down to 360px; no horizontal overflow at 320px; tap targets ≥44px.
- [ ] Semantic HTML: one `h1`, logical heading order, real `alt` text, real form labels.
- [ ] Full keyboard path with visible focus; overlay menus trap and restore focus.
- [ ] Body text ≥16px with adequate contrast, even where display type takes risks.
- [ ] Legible, navigable content with JS/WebGL off.
- [ ] LCP < 2.5s on 4G; smooth-scroll/custom-cursor don't break anchors, find-in-page, or the back button.

## Kill test
- [ ] "Could a template have made this?" — if yes anywhere, push those parts further.
- [ ] Name the one thing a visitor describes to a friend. Can't name it → there's no signature yet.
- [ ] Rapid clicks, fast flicks, resize mid-animation, refresh mid-transition — nothing breaks.
- [ ] You'd sign it.
