# UI foundations: the standard checklist

Every UI must pass this before it ships, on every project and in any stack (web, Flutter, native).
The rules are rewritten from TypeUI's UI Foundations (typeui.sh/ui-foundations/configurator, by @roberttanislav), which builds on Refactoring UI. Use the configurator to see a live bad/good example of any rule.

## Type
- Use one small type scale and pick every size from it. Example: 12 / 14 / 16 / 18 / 20 / 24 / 30 / 36.
- Set the size by role: headings bigger and tighter, body 16, supporting text smaller and quieter.
- Line height is about 1.2 for headings and 1.5–1.6 for body.
- Keep long text to 60–75 characters per line. Cap the width (`max-width: 65ch`; in Flutter, a ConstrainedBox).
- Balance headings and avoid one-word last lines (`text-wrap: balance`, `pretty`). Long links and ids must wrap inside their box.
- Tighten big display text slightly, and give short all-caps labels a little more letter spacing.
- Align prose to its reading direction. Never justify narrow columns.
- When mixed text sizes share a line, align them on the baseline, not the centre.
- Pick a font that stays legible at the size actually used, and keep similar characters (0/O, 1/l/I) distinct wherever people copy ids or codes.
- Links in running text look clickable without relying on colour (underline or weight). Link text says where it goes ("View order", not "click here").

## Numbers and data
- Use tabular numerals for prices, totals, counters and timers that change.
- In tables, left-align names and right-align comparable amounts.

## Spacing and size
- Start too spacious, then tighten until things feel connected. Example: 24 px card padding beats 8 px.
- Keep related items closer together than separate groups.
- Size inputs to what people type (a PIN field is narrow, an address field is wide).
- Columns with fixed content take the width they need, and the main area flexes.
- Fewer borders: separate things with space or background first, and use a quiet divider only when needed.

## Hierarchy
- The important information gets the emphasis; supporting details get quieter (colour and weight before size).
- Keep the size range restrained, and use weight and contrast to show importance.
- To make the main action stand out, first quiet down whatever competes with it.
- Style actions by importance: one primary, the rest secondary or tertiary. Destructive actions are not automatically red and big.
- Drop labels when the data explains itself; keep the ones that are needed.
- Choose the heading element (h1/h2) for structure and its size for its role.

## Colour
- Build palette families (neutral, primary, success/warn/danger), each with 8–10 shades: pick the base, a light edge and a dark edge, then fill in the gaps. Shift the hue and saturation slightly at the edges so tints stay rich, not grey.
- Never show meaning with colour alone, including chart series: add direct labels, icons or patterns.

## Contrast
- Body text ≥ 4.5:1, aiming for 7:1. Button labels ≥ 4.5:1.
- An input's surface must visibly differ from its parent surface, by fill or border.
- Secondary text on a coloured surface uses an opaque, related tint of that colour, never grey at low opacity.
- When a solid fill is too loud, try dark text on a pale tint.
- Text over images: control the image (scrim, gradient, blur), not just the text colour.

## Optical balance
- Start from the geometric layout, then correct by eye: icons next to text, a play icon inside a circle, button padding with icons, glyph overshoot, the visual weight of colour (a heavy icon looks bigger than text of the same size), and hanging punctuation.

## Corners and layers
- Nested radius: inner = outer − padding. Active highlights inside a panel use max(0, panel radius − inset).
- Elevation: base surface < raised card < dropdown < floating toast < modal. A modal lifts and dims the page behind it.

## Touch, pointer and focus
- Targets are ≥ 44×44 px (48 in Material) with space between them. This covers close buttons, icons and edge navigation; leave room to swipe.
- Focus rings are ≥ 2 px with a visible offset, and always visible when using a keyboard.
- Show the pressed state where the finger is: pressed scale 0.95–0.98 for about 200 ms.

## Forms
- Labels are clickable and don't select text when tapped. Put a checkbox next to the first line of a wrapped label.
- Buttons look like buttons. Lay choices out in one column. Make options comparable side by side.
- Long lists get a type-to-filter search instead of scrolling.
- Sliders show their current value while they move.
- Inputs and the buttons beside them share one height (search plus button, pagination, toolbars).

## Status and states
- Every status shows colour, an icon and a label.
- An empty state says why it's empty and offers one useful first action.
- Errors are noticeable and say what to do next.

## Motion
- Motion is interruptible: sheets, sidebars and popovers reverse from wherever they are right now, never from the end.
- Ease in and out, move along clear paths or arcs, and let follow-through overlap. Anticipate big moves a little.
- Feedback informs without distracting. Use consistent timing (about 100–300 ms for UI and 200 ms for presses), and keep flips readable.
- Gestures respond instantly, can be cancelled mid-way, and track the finger continuously.
- Honour reduced motion: swap movement for a fade, or drop it.

## Images
- Use sharp images at their real display size, in consistent frames and ratios. Give images on similar backgrounds a subtle inner outline (about 1 px at 10% black).

## Consistency
- Shared styles and tokens only, with one name for each thing everywhere. List icons carry meaning. Accent borders are used sparingly. Backgrounds stay quiet.
- Put the main feature first, then the structure, with actions placed where the eye ends.
- Add a little personality through one consistent choice (font, radius or colour), not noise.

## How to apply
1. Before building, set the tokens: type scale, spacing scale (4/8 base), palette families, radii, elevations and motion durations.
2. While building, use only the tokens.
3. Before calling it done, walk every screen against this file and fix anything that fails. Check contrast with a calculator, never by eye.
