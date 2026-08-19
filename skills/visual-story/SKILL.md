---
name: visual-story
description: Make a picture, shot, video, or scene look cinematic on purpose, using Bruce Block's The Visual Story. Structure the seven visual components — space, line, shape, tone, colour, movement, rhythm — with the principle of contrast and affinity, so the look carries the story instead of decorating it. Use when you design a shot, a video, a keyframe, a film prompt, an animation, a poster, or a UI hero; when you write a prompt for an image or video model and want a real cinematic look; when work looks flat, generic, amateur, or "like a video someone took"; when asked how to make something cinematic, moody, intense, or calm.
---

# The visual story

Every picture already says something. The only question is whether you chose it.

Source: *The Visual Story: Creating the Visual Structure of Film, TV and Digital Media*, Bruce Block, 3rd edition 2021. Block produced *Something's Gotta Give*, *What Women Want*, *The Parent Trap*, and teaches visual structure at USC. The lineage runs Eisenstein to Vorkapich to Novros to Block.

Full detail on each component: `components.md`. Read it when you need the depth cues, the tone controls, or the movement continuum.

## The principle

There is one rule, and it applies to all seven components:

> **The greater the contrast in a visual component, the more the visual intensity increases.**
> **The greater the affinity, the more the visual intensity decreases.**

Contrast means difference. Affinity means sameness. That is the entire theory.

**CONTRAST = MORE INTENSITY. AFFINITY = LESS INTENSITY.**

It works at three scales: inside one shot, from shot to shot, and from sequence to sequence.

Cinematic is not a filter, a lens, or a colour grade. Cinematic is a picture whose intensity is chosen, and whose intensity matches what the story needs at that moment. A shot with no chosen contrast reads as amateur even when it is well exposed.

## The seven components

| Component | Contrast, more intense | Affinity, less intense |
| --- | --- | --- |
| **Space** | deep, ambiguous, open frame, many surface divisions | flat, recognisable, closed frame, few divisions |
| **Line** | diagonal, mixed orientations, mixed quality | all horizontal, or all one orientation |
| **Shape** | triangles, mixed shapes | one repeated shape, circles |
| **Tone** | full black to white, low key, non-coincidence | middle greys only, high key, coincidence |
| **Colour** | opposed hues, high saturation, warm against cool | one hue family, desaturated |
| **Movement** | toward or away from camera, fast, mixed directions, 3D camera moves | across frame, slow, one direction, locked or 2D camera |
| **Rhythm** | fast, irregular, fragmented | slow, regular, continuous |

Every one of these is a dial you set. Set them all one way and you get a calm picture. Set them all the other way and you get an aggressive one. Set most to affinity and spike one at the right moment, and you get a film.

## The method

**1. Graph the story first.** The first graph is always the story, never the visuals. Draw conflict intensity from 0 to 100 across the running time. Mark exposition, conflict, climax, resolution. If you cannot find the conflict, you cannot design the look.

Break a single scene into directorial beats and graph those. A nine second video has a beat list too.

**2. Write the visual exposition.** Story exposition is the facts needed to begin. Visual exposition is the rules for how the seven components will be used, taught to the audience early and then obeyed.

> "Once upon a time there was a cautious, unhappy family who lived in flat space, with square shapes, and cool colours."

Meaning is assigned, not inherited. There is no universal colour language. Red means death in *Don't Look Now* because the opening scene teaches it. *Klute* is entirely flat space and flat means trapped. *The Shining* is entirely deep space and deep means trapped. Opposite choices, same meaning, because each film taught its own rule and then kept it.

**3. Choose one of three treatments for each component.**

- **Constant.** It never changes. This gives unity and a style. Most components should be constant.
- **Progression.** It changes gradually across the piece. *The Shining* runs space from shallow to extreme depth and red from pale pink to full saturation, in step with Jack's decline.
- **Contrast and affinity.** It spikes at chosen moments. The most precise control, and the one to use sparingly.

**4. Spike at the climax.** The visual climax should sit on the story climax. *Ninotchka* is flat space for the entire film except one shot: Garbo's entrance. One deep shot in ninety minutes, and it lands like a gunshot.

**5. Resolve with affinity.** When the conflict ends, the intensity drops. *Collateral* cuts from a fast, tight, intense rhythm to a wide, near-still frame.

## What to remember above the detail

- **The story graph comes first. Always.** Motivation for every visual choice lives in the story structure, not in taste.
- **Keep it simple.** Block's own advice: the best approach is usually the simplest. Most components stay constant. An over-designed visual structure confuses the crew and the audience.
- **You will photograph these components whether you plan them or not.** They will speak regardless. Unplanned means the picture says something you did not choose.
- **Contrast is not always right.** Two characters who slowly stop fighting are best drawn as warm against cool that converges into warm. The visual can move opposite to the conflict when the story asks for it.
- **Advertisements are the pure case.** In an ad the visuals often are the content, so the component choices carry the whole message. Same product, all-contrast reads as exciting; all-affinity reads as calm and trustworthy.

## The attention ladder

Inside one frame the eye goes, in this order, to:

1. movement
2. the brightest area
3. faces
4. the vanishing point of converging lines
5. anything new that enters

You do not ask the audience to look somewhere. You make the place you want them to look the brightest thing that moves. Everything else is hope.

## The 26-point checklist

Block's own list. Run it over any shot or sequence and decide each line, or accept whatever the room hands you.

1. **Story**: conflict intensity
2. **Space**: flat / deep
3. **Space**: ambiguous / recognisable
4. **Space**: open / closed frame
5. **Space**: surface divisions
6. **Line**: orientation
7. **Line**: direction
8. **Line**: quality
9. **Shape**: circle, square, triangle
10. **Colour**: hue
11. **Colour**: brightness
12. **Colour**: saturation
13. **Colour**: warm / cool
14. **Tone**: controlled by art direction or by lighting
15. **Tone**: coincidence / non-coincidence
16. **Movement, object**: direction
17. **Movement, object**: fast / slow
18. **Movement**: continuum of movement
19. **Movement, camera**: 2D / 3D
20. **Rhythm, stationary objects**: fast / slow
21. **Rhythm, stationary objects**: regular / irregular
22. **Rhythm, moving objects**: fast / slow
23. **Rhythm, moving objects**: regular / irregular
24. **Rhythm, editorial**: fast / slow
25. **Rhythm, editorial**: regular / irregular
26. **Rhythm**: continuous / fragmented

## Applied: prompts for image and video models

Block wrote for camera crews, but the components are exactly the levers a generative model responds to. A prompt built from them beats a prompt of adjectives, because "cinematic" is not a description and "deep space with a long lens, low key, warm interior against a cold window, locked camera, slow rhythm" is.

Order for a shot prompt:

1. **Style and medium** first, and hold it identical across every prompt in the set.
2. **Space**: name the depth. Give a foreground, a midground, and a background object, or say the space is flat and frontal.
3. **Lens**: long lens flattens and compresses, wide lens deepens and bends. Naming a focal length is the cheapest depth control there is.
4. **Tone**: name the key and where the brightest area sits. The brightest area is where the audience looks, so put it on the subject or deliberately not.
5. **Colour**: name two or three hues and their saturation, and say which is warm and which is cool. Never leave the palette open.
6. **Line and shape**: name the dominant orientation in the set, the walls, the window frames, the road.
7. **Movement**: name the object track and the camera move separately, and keep camera moves slow and 3D for grounded work.
8. **Rhythm**: for video, name the tempo and whether it is regular.

Then check it against the story graph. If the shot lands on a calm beat, every dial above should be set to affinity. If it lands on the climax, spike one or two dials, not all seven.

## Failure modes

- **Flat intensity.** Everything at the same level for the whole piece. It reads as boring even when each frame is pretty.
- **Intensity in the wrong place.** The visuals peak on a beat the story does not care about.
- **Every dial at contrast, all the time.** Exhausting, and it leaves nothing for the climax. Contrast means nothing without affinity around it.
- **A palette nobody chose.** Colour arrives from the location, and it says whatever it says.
- **Decoration.** Visual structure that draws attention to itself is not supporting the story. It is competing.
