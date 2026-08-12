# Signature Techniques — concise implementations

Contents: 1. Reduced-motion wrapper · 2. Lerp smooth scroll · 3. Masked line reveal · 4. Scroll-scrubbed animation and parallax · 5. Velocity skew · 6. Pinned and horizontal sections · 7. Magnetic elements · 8. Custom cursor · 9. Underline wipe and label roll · 10. Image hover zoom · 11. Marquee · 12. Grain overlay · 13. Preloader counter · 14. Page transitions · 15. Text scramble · 16. WebGL image distortion · 17. Detail one-liners

These are vocabulary, not a quota. Implement only what the concept justifies. All motion goes through the reduced-motion gate (§1). Numbers reference `laws-and-math.md`.

## 1. Reduced-motion (snap to final, don't strand)

`prefers-reduced-motion: reduce` means remove *motion*, not remove *feedback* — the site must still feel complete and intentional, just still. Deleting every transition globally (`transition: none`) leaves elements stuck in their start state and kills hover/focus feedback — its own accessibility problem. Instead: gate the big scroll/reveal motion in JS, and let CSS neutralize *duration* so everything else snaps to its end state instantly.

```js
const motionOK = matchMedia('(prefers-reduced-motion: no-preference)').matches;
// if (!motionOK): native scroll (no lerp), skip scroll-scrub/parallax/velocity/WebGL motion,
// set every reveal target to its FINAL state (no translate/clip), keep hovers as instant opacity/color.
```
```css
/* canonical pattern: neutralize duration instead of deleting rules — no stuck or janky states */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; scroll-behavior: auto !important;
  }
}
```
Hover, focus rings, and state changes still fire — just instantly. That's a designed still site, not a disabled one.

## 2. Lerp smooth scroll

Library route (Lenis):
```js
import Lenis from 'lenis';
const lenis = new Lenis({ duration: 1.2, easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)) });
function raf(t){ lenis.raf(t); requestAnimationFrame(raf); } requestAnimationFrame(raf);
// GSAP sync: lenis.on('scroll', ScrollTrigger.update);
```
Hand-rolled core (the whole secret in four lines):
```js
let current = 0, target = 0; // target updated from wheel/native scroll
function frame(dt){ const k = 1 - Math.exp(-8 * dt);        // λ=8; lower = heavier
  current += (target - current) * k;
  content.style.transform = `translate3d(0, ${-current}px, 0)`; }
```
Keep anchors, keyboard scrolling, and find-in-page working; disable entirely when `!motionOK`.

## 3. Masked line reveal (the genre's defining move)

```html
<h1 class="reveal"><span class="line"><span class="inner">Words rise from</span></span>
<span class="line"><span class="inner">invisible slots</span></span></h1>
```
```css
.line { display:block; overflow:hidden; } .inner { display:block; transform: translateY(110%); }
```
```js
gsap.to('.reveal .inner', { y: 0, duration: 1.0, ease: 'expo.out', stagger: 0.06,
  scrollTrigger: { trigger: '.reveal', start: 'top 85%' } });
```
Use SplitText (GSAP, free) or split manually on resize-stable breakpoints. Same pattern reveals images: parent `overflow:hidden`, child `clip-path: inset(100% 0 0 0)` → `inset(0)` or `scale(1.15)` → `scale(1)`.

## 4. Scroll-scrubbed animation and parallax

```js
gsap.to('.layer-back',  { yPercent: -10, ease: 'none',
  scrollTrigger: { trigger: '.section', start: 'top bottom', end: 'bottom top', scrub: true } });
gsap.to('.layer-front', { yPercent: 15, ease: 'none', scrollTrigger: { /* same */ scrub: 0.5 } });
```
`scrub: true` = locked to scroll; `scrub: 0.5–1` adds a slight lag that pairs beautifully with the lerp. Easing is `none` because scroll position IS the easing.

## 5. Velocity skew (inertia illusion)

```js
let vel = 0;
lenis.on('scroll', e => { vel = e.velocity; });
gsap.ticker.add(() => {
  const skew = gsap.utils.clamp(-5, 5, vel * 0.3);
  gsap.set('.skew-target', { skewY: skew }); vel *= 0.9; });
```

## 6. Pinned and horizontal sections

```js
// Pin a stage while an inner timeline scrubs across 200vh of scroll:
gsap.timeline({ scrollTrigger: { trigger: '.stage', start: 'top top', end: '+=200%', pin: true, scrub: 1 } })
  .to('.stage .a', { xPercent: -50 }).to('.stage .b', { opacity: 1 }, '<');
// Horizontal section: translateX a wide track by (track.scrollWidth - innerWidth) over the pin distance.
```

## 7. Magnetic elements

```js
el.addEventListener('mousemove', e => { const r = el.getBoundingClientRect();
  const x = e.clientX - r.left - r.width/2, y = e.clientY - r.top - r.height/2;
  gsap.to(el, { x: x*0.3, y: y*0.3, duration: 0.4, ease: 'power3.out' });
  gsap.to(el.querySelector('.label'), { x: x*0.15, y: y*0.15, duration: 0.4 }); });
el.addEventListener('mouseleave', () => gsap.to([el, el.querySelector('.label')], { x:0, y:0, duration:0.7, ease:'expo.out' }));
```

## 8. Custom cursor

```js
const c = document.querySelector('.cursor'); let cx=0, cy=0, tx=0, ty=0;
addEventListener('mousemove', e => { tx = e.clientX; ty = e.clientY; });
(function loop(){ cx += (tx-cx)*0.2; cy += (ty-cy)*0.2;
  c.style.transform = `translate3d(${cx}px,${cy}px,0)`; requestAnimationFrame(loop); })();
// Scale 2–4× over [data-hover] targets; mix-blend-mode: difference for inversion.
```
Pointer-only (`@media (pointer: fine)`); never hide the native cursor without a fully functional replacement.

## 9. Underline wipe and label roll

```css
a.wipe { position:relative; } a.wipe::after { content:''; position:absolute; left:0; bottom:-2px;
  width:100%; height:1px; background:currentColor; transform:scaleX(0); transform-origin:right;
  transition: transform .5s cubic-bezier(0.19,1,0.22,1); }
a.wipe:hover::after { transform:scaleX(1); transform-origin:left; }  /* enters left, exits right */
```
Label roll: button contains two stacked labels in an overflow-hidden box; hover translates the stack −100%, expo.out, 400ms.

## 10. Image hover zoom

```css
.frame { overflow:hidden; } .frame img { transform:scale(1.01); transition: transform .8s cubic-bezier(0.16,1,0.3,1); }
.frame:hover img { transform:scale(1.06); }
```

## 11. Marquee (one of the few legitimate uses of linear)

```css
.marquee { overflow:hidden; white-space:nowrap; } .marquee .track { display:inline-flex; gap:4vw;
  animation: m 20s linear infinite; } @keyframes m { to { transform: translateX(-50%); } }
```
Duplicate content once so the track is exactly 200% wide; pause or slow on hover; optionally modulate speed by scroll velocity.

## 12. Grain overlay

```css
.grain { position:fixed; inset:-100%; width:300%; height:300%; pointer-events:none; opacity:.05; z-index:999;
  background-image:url(noise.png); animation: g .8s steps(4) infinite; }
@keyframes g { 0%{transform:translate(0,0)} 25%{transform:translate(-2%,3%)} 50%{transform:translate(3%,-2%)} 75%{transform:translate(-1%,-3%)} 100%{transform:translate(0,0)} }
```
Or inline SVG: `feTurbulence type="fractalNoise" baseFrequency="0.7"` rendered to a data-URI. Opacity 3–6%.

Cost note: an animated full-viewport overlay repaints every frame. Cheapest that reads the same is a *static* noise data-URI at 3–6% opacity (no animation) — reach for the animated version only when the concept genuinely wants living grain, and drop it on low-power devices.

## 13. Preloader counter

Count 0→100 tied to *real* load progress (asset promises), ease the displayed number (lerp toward actual), then exit with a curtain wipe (`clip-path: inset(0 0 100% 0)`, inOutQuint, ~900ms) that hands off directly into the hero's masked reveals — the preloader is the overture, its exit is the first note of the hero. Never fake-delay > 300ms. Skip entirely on fast loads and repeat visits.

## 14. Page transitions

- Curtain: fixed panel wipes in (cover) → swap route → wipe out (reveal), inOutQuint, 500ms + 700ms.
- Shared element (FLIP): measure thumbnail rect (First), navigate, measure hero rect (Last), Invert with a transform, Play to identity — the clicked image *becomes* the next page's hero.
- Native option: View Transitions API where supported, with the curtain as fallback.
- The outgoing page exits with intent (fade+translate the same direction the new page enters from). Exits are designed, not defaulted.

## 15. Text scramble (use once, if the concept is technical)

Cycle random glyphs per character, resolving left→right over ~600–900ms; glyph pool from a mono face; resolve order can be randomized. One appearance per page maximum — it's strong seasoning.

## 16. WebGL image distortion (the ceiling — sketch)

Plane per image, DOM-synced (mirror `getBoundingClientRect` each frame). Fragment core:
```glsl
vec2 uv = vUv;
float n = snoise(vec3(uv * 3.0, uTime * 0.2));
uv += n * uHover * 0.05;                       // hover-driven displacement, amp 0.02–0.08
float s = uVelocity * 0.006;                    // scroll-velocity RGB shift
vec4 col = vec4(texture2D(uMap, uv + vec2(s,0)).r,
                texture2D(uMap, uv).g,
                texture2D(uMap, uv - vec2(s,0)).b, 1.0);
```
Lerp `uHover` and `uVelocity` uniforms (never step them). Full DOM fallback mandatory. Post-processing (grain/vignette/bloom): if you can see the effect as an effect, halve it.

## 17. Detail one-liners

`::selection` in palette colors · scrollbar styled or hidden (only under a scroll indicator or lerp scroll) · local time + city in footer ("Lagos — 14:32", live) · index numbers on nav and projects ("01", "(02)") · mega-footer with one giant CTA headline · arrow icons rotating 45° on hover · `title`/favicon/meta/OG-image art-directed · designed 404 · current nav item marked typographically (not just color) · image captions in the micro-label register · easter egg for the curious (console message, konami, logo long-press) · sound toggle if audio exists, default muted · copyright year computed, not typed.
