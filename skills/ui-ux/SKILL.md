---
name: ui-ux
description: Design or review any interface so it is professional, pleasant, memorable, stimulating, and engaging. Use when building, redesigning, auditing, or criticizing UI/UX, screens, layouts, flows, dashboards, forms, nav, or product chrome.
---

# UI/UX

Research this skill came from — read it first: `~/search/ui-ux-first-principles.md`

Standard for every UI, any project: pass every rule in `foundations.md` (next to this file) before calling UI work done.

A good interface is cheap, successful sense-making. Pretty is easy processing. Gripping is a gap the user can close.

1. First 50 ms: look like the category, stay visually simple.
2. Spend the 3–5 chunk budget on the task. One mark for the next act.
3. Next target big and near. Answer in 100 ms if you can, 400 ms if you must. Never silent past 1 s. Never blank past 10 s.
4. Contrast at least 4.5:1. Space and type in ratios.
5. Pleasant = fluent. Stimulating = a closeable gap. Do not mix them by accident.
6. Memory = one peak + a clean end + one odd thing.
7. Engagement = visible progress + choice + competence + a scent trail. Watch for wanting without liking.
8. Hover labels: first one ~500 ms so it is not an accident. Once moving between siblings, show the rest now. Leave ~300 ms and the delay resets.

Do not use the golden ratio, “fewer choices is always faster,” or dopamine-as-pleasure as reasons.

Flutter chat forms: keep drafts and saved state outside recycled list children; serialize saves across remounts. Before pushing payment, await the modal route's `completed`, and bound missing audio-drain signals with a timer. Verify with `flutter test` and `flutter analyze`.

Palette trials on a live page: inject a `<style>` with `agent-browser eval`, take `agent-browser screenshot --full`, tile it into 4 columns with ffmpeg (`crop` ×4 + `hstack=4`), Read the one image to judge colour rhythm. Scope colour bands as tone classes that remap the semantic tokens; keep button fill/label as constants.
