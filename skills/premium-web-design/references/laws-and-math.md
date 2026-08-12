# Laws and Math — the quantitative system

Contents: 1. Typography · 2. Space and grid · 3. Color and texture · 4. Motion · 5. Scroll physics · 6. Interaction math · 7. Noise and shaders · 8. Performance budget · 9. Typeface sourcing

Everything here is a number or a formula. These are the defaults of the premium genre — the concept (Phase 2) decides where within each range to sit, and may deliberately break a law *once* it has been established. Breaking a law you never established just looks like a mistake.

**One family, not the whole map.** These defaults encode one lineage: dark/editorial, motion-heavy, huge display type, grain, smooth scroll. That is *a* premium look, not *the* premium look. Restrained/light/Swiss and product-UI premium (Apple, Stripe, Linear, clean corporate) are equally award-tier and invert half of this: light field, near-native scroll, minimal motion, tighter type contrast, no grain, system-grade sans at high craft. Let the concept pick the family first; then read the numbers below as the settings for *this* concept, inverting the ones that fight it. The constant across both families is craft, restraint, and one idea executed totally — not the specific values.

## 1. Typography

**Modular scale.** Every font size on the page sits on the ladder `size(n) = base × ratio^n`, base 16–18px. Ratios (musical intervals):

| Ratio | Name | Character |
|---|---|---|
| 1.2 | minor third | calm, editorial |
| 1.25 | major third | balanced default |
| 1.333 | perfect fourth | confident |
| 1.414 | augmented fourth | dramatic |
| 1.5 | perfect fifth | very dramatic |
| 1.618 | golden ratio | extreme, use sparingly |

**Scale contrast.** Premium sites run display-to-body ratios of 10:1 to 30:1 (template sites: ~3:1). Hero display = 8–14vw. This violence of contrast is itself the statement.

**Fluid type (exact formula).** For a size that is `minF` px at viewport `minV` px and `maxF` at `maxV`:
`slope = (maxF − minF) / (maxV − minV) × 100` (in vw), `intercept = minF − slope × minV / 100` (px), then
`font-size: clamp(minFpx, {slope}vw + {intercept}px, maxFpx)`.
Worked example — 40px @ 375 → 160px @ 1440: slope ≈ 11.27vw, intercept ≈ −2.3px → `clamp(40px, 11.27vw - 2.3px, 160px)`.

**The three registers** (the genre's signature type system):
1. Display: 8–14vw, line-height 0.9–1.05, letter-spacing −0.02 to −0.04em, tightest at largest sizes.
2. Body: 16–18px, line-height 1.5–1.7, measure 55–75 characters, letter-spacing 0 to −0.01em.
3. Micro-labels: 10–12px, uppercase or monospace, letter-spacing +0.08 to +0.15em, often with index numbers ("01 — Work").

**Micro-typography laws.** Real quotes and apostrophes (" " '), never straight ones. `text-wrap: balance` on headlines you're *not* splitting for animation (splitting into lines freezes the wrap, so balance no-ops — hand-balance those breaks instead). `font-feature-settings` for tabular numerals in data, ligatures on in display. Hanging punctuation where possible. No orphans in headlines (manual breaks or `&nbsp;`). Italic reserved for one editorial voice, not emphasis spam. `font-display: swap` with size-matched fallback metrics to kill layout shift.

**Pairing law.** Default premium pairing = one neutral grotesque sans (structure) + one editorial serif (a single elegant voice, often italic, used in ≤2 places). Never two similar sans faces. A mono third voice only for labels/data.

## 2. Space and grid

- Spacing scale: 8px base, but at luxury multiples — the working set is 8 / 16 / 24 / 32 / 48 / 64 / 96 / 128 / 160 / 200 / 240. Section vertical padding: 120–240px desktop (or 10–18vh), 64–96px mobile.
- Negative-space ratio: 70–90% of any given viewport is empty. Density signals cheap; emptiness signals confidence (a Chanel ad vs a supermarket flyer). If a view feels empty, it is probably almost right.
- Grid: 12 columns, gutter 24–40px, outer margins 5–8vw. Use it *asymmetrically*: text col 2–7, image col 8–12 shifted vertically to overlap the previous section.
- Establish-then-break: align rigorously long enough that one deliberate violation per few viewports (an element crossing a section boundary, a caption floating in the void) creates tension, not mess. Tension without chaos ≈ the definition of exquisite.
- Vertical rhythm: consistent per-page; adjacent sections may share edges (0 gap, hard cut) or breathe (240px) — but pick a rhythm and repeat it, then break once.
- One dominant element per viewport. Two competing focal points halves the perceived cost of both.

## 3. Color and texture

- Palette size: 2–3 colors total is the genre norm; photography/3D supplies the rest.
- Never pure: off-black `#0A0A0A`–`#141414`, warm off-white `#F4F1EC` / `#EFEDE8` / `#FAF9F6`. Pure #000-on-#FFF reads harsh and digital.
- One accent, used with extreme scarcity (sometimes zero times above the fold). Scarcity is what makes it expensive.
- Grain layer: animated noise over everything at 3–6% opacity (SVG `feTurbulence` baseFrequency ≈ 0.6–0.9, or a tiling noise PNG re-positioned per frame). It kills sterile flatness the way film grain makes video into cinema.
- Gradients: only if the concept calls for them, always noise-dithered to prevent banding (banding = amateur tell). Two stops, same hue family, subtle.
- Dark-room case-study pattern: near-black field, high-contrast type, images as the only luminance events.
- Semantic scarcity: link/hover/selection colors all drawn from the same tiny palette — no rogue blues.

## 4. Motion

Lineage: Disney's principles (slow-in/slow-out, follow-through, staging, secondary action, anticipation) expressed as two numeric objects — easing curves and interpolation constants. Choose ONE motion personality from the concept and apply it everywhere; mixed easings read as unedited.

**Easing functions (the premium family — long deceleration tails):**
- expo.out: `y = 1 − 2^(−10x)`, normalized so `y(1) = 1` exactly (the raw form lands at 0.999 — snap the end) — CSS ≈ `cubic-bezier(0.16, 1, 0.3, 1)` or classic `cubic-bezier(0.19, 1, 0.22, 1)`. Reaches ~90% of distance in ~30% of time; the tail is the expensive feel.
- power4.out: `y = 1 − (1−x)^4`. power3.out: `y = 1 − (1−x)^3` (slightly snappier).
- inOut for position swaps/transitions: quint `cubic-bezier(0.83, 0, 0.17, 1)` or quart `cubic-bezier(0.76, 0, 0.24, 1)`.
- Banned by default: `linear` (except marquees/spinners), CSS `ease`/`ease-in-out` defaults, and any bounce/elastic unless the concept is explicitly playful.

**Duration bands.** Hovers/micro: 250–400ms. Content reveals: 800–1200ms. Page transitions: 1000–1600ms. Ambient loops: 2000ms+. Cinematic > utilitarian: err slower than app-UI instincts, but never make the user wait for meaning — content must be readable before its animation finishes settling.

**Stagger.** Siblings never appear together: `delay(i) = i × Δ`, Δ = 30–80ms (30–40 technical/fast, 60–80 editorial/heavy). Cap total cascade ≤ ~1s; for long lists, ease the stagger distribution so late items compress.

**The masked reveal (signature move).** Split headline into lines → wrap each line in `overflow: hidden` → child starts at `translateY(100%)` (fully below its own mask) → animate to 0 with expo.out, 60ms stagger. Words rise out of invisible slots.

**Choreography laws.** One thing at a time, or one deliberate cascade — never simultaneous unrelated motion. Entrances and exits are designed together. Reveal threshold: start when element is 10–20% into viewport, play once (don't re-trigger on scroll-up unless the concept is a machine). Transform origins chosen consciously (text reveals from baseline, images scale from 1.15→1.0 on entry, not 0.8→1.0 which reads bouncy-cheap).

## 5. Scroll physics

**The lerp (one signature option, not a requirement).** Smoothed scroll is a strong tool *and* a liability — it fights native physics, can hurt accessibility, and reads dated when overdone. Native scroll is a fully valid premium choice; use the lerp only when the concept's *mass* wants it (heavy/liquid/cinematic), and keep it light. Per frame: `position += (target − position) × k`, k = 0.075–0.1. Frame-rate independent: `k_dt = 1 − e^(−λ·dt)` with λ ≈ 6–10 (lower = heavier/more liquid). The page exponentially approaches the scroll target — always decelerating, never arriving abruptly. Implement via Lenis (default: expo ease, ~1.2s settle) or hand-rolled. Whichever you pick, anchors, keyboard, find-in-page, and the back button must keep working.

- Parallax: `offsetY = scrollProgress × (1 − depth) × range`, depth ∈ 0.7–1.3 across 2–3 layers. Backgrounds slower, foregrounds faster; ±10–20% relative speed is plenty.
- Scrub: tie animation progress directly to scroll progress (GSAP ScrollTrigger `scrub: true` or 0.5–1 for slight smoothing) — the user drives the film.
- Velocity skew (inertia illusion): `skewY = clamp(scrollVelocity × c, −5°, +5°)`, lerped back to 0 each frame.
- Pinned sections: pin a viewport-height stage while inner timeline scrubs across 100–300vh of scroll distance. Horizontal-scroll sections: translateX mapped to vertical scroll progress; keep total horizontal distance ≤ ~3 viewport widths.
- Scroll progress indicator (thin bar or counter) only if the concept is a "document/film" — otherwise omit.
- Always: native scroll restored for `prefers-reduced-motion`, keyboard/anchor navigation still functional under the lerp.

## 6. Interaction math

- Magnetic elements: inside radius r (≈ 80–120px), `offset = (cursor − center) × s`, s = 0.2–0.4 (inner label moves at ~s/2 for depth); lerp home on leave.
- Custom cursor: dot follows pointer via lerp k ≈ 0.15–0.25 (trails slightly); scales 2–4× over interactive targets; `mix-blend-mode: difference` for the inversion trick. Keep the native cursor functional or a visible equivalent — never strand the user.
- Hover states: every interactive element has one, 250–400ms, expo/power-out. Underline wipe: `scaleX 0→1`, `transform-origin: left` on enter; flip origin to `right` on leave so it exits the far side.
- Image hover: scale 1→1.04–1.08 inside an overflow-hidden frame (≈600ms), optionally with 2–4% brightness/filter shift.
- Buttons: fills that sweep (a translating pseudo-element behind the label), arrows that rotate 45° or swap-slide, label roll (duplicate label slides in from below its mask).
- Drag surfaces (galleries): same lerp physics; momentum decay via the exponential factor; cursor communicates "drag".

## 7. Noise and shaders (the WebGL ceiling)

- Stack: Three.js / OGL / react-three-fiber; DOM-synced image planes (mesh position/size mirrors the `<img>` rect each frame).
- Organic motion source: simplex noise; fractal Brownian motion `fbm(p) = Σᵢ noise(p·2^i) / 2^i` (4–6 octaves).
- Image distortion on hover/scroll: displace UVs by noise or a displacement texture, amplitude 0.02–0.08, animated by time and/or scroll velocity.
- RGB shift / chromatic aberration during fast scroll: per-channel UV offset proportional to velocity (max ~0.005–0.01 UV).
- Post stack (subtle or nothing): film grain, faint vignette, restrained bloom. If an effect is noticeable as an effect, halve it.
- Fallback law: the site must be fully coherent with WebGL off; the canvas is seasoning, not the meal.

## 8. Performance budget (fluidity is a luxury metric)

- 60fps = 16.67ms/frame. Animate only `transform` and `opacity`; never top/left/width/height/margin. One stutter reads cheaper than no animation at all.
- `will-change` only on elements about to animate; remove after. Avoid layout thrash: batch reads/writes, use ResizeObserver/IntersectionObserver over scroll-handler math.
- Images: modern formats, exact-size responsive sources, lazy below the fold, dominant-color or blurred placeholder (never a white flash). Fonts: preloaded, subset, swap with tuned fallbacks — zero visible reflow.
- Preloader only if the load genuinely needs cover; if used, make it the concept's overture, and never fake-delay more than ~300ms.
- Budget guide: LCP < 2.5s on 4G, CLS ≈ 0, total JS for a marketing site ideally < 300KB gz before the WebGL layer.

## 9. Typeface sourcing

- The look is largely licensed foundry type: Klim (Söhne, Founders Grotesk, Tiempos), Grilli Type (GT America, GT Sectra), Dinamo (ABC Diatype, Whyte), Commercial Type (Graphik, Canela), Displaay, Pangram Pangram (Neue Montreal, Editorial New). If the user owns licenses, use them — it's half the premium signal.
- No budget: Fontshare (free, foundry-grade — e.g. General Sans, Cabinet Grotesk, Clash Display, Sentient, Zodiak) and Pangram Pangram's free tier beat Google defaults. Caveat: the popular free faces (Clash Display, General Sans, Cabinet Grotesk) are now their own tell — used untransformed they read "AI landing page" as fast as Playfair does. Dig past the top of the list, or earn originality through treatment. On Google Fonts, avoid the exhausted set (Inter/Poppins/Montserrat/Playfair as hero display reads template) — dig for less-circulated grotesques/editorials, or make an ordinary face extraordinary through scale, tracking, and pairing.
- Whatever the face: the treatment (three registers, scale violence, micro-typography) carries more premium signal than the font file itself.
