---
name: storyboard-animatic
description: Make voiced storyboard animatics from held drawings, with dialogue-led acting beats, consistent illustrated characters, frame-accurate timing and a watchable MP4. Use for pencil-board story reels or illustrated dialogue tests, rather than full character animation.
---

# storyboard animatic

Deliver a short film built from intentional held drawings and performed dialogue. Preserve the user's requested medium, voice provider, duration and degree of finish. Moderate-detail colored pencil is a useful option, not a universal style.

## decide before spending

- Read the user's taste instructions. Research unfamiliar pacing or provider mechanics using primary sources; distinguish sourced principles from your editorial choices. Check the actual callable tool parameters instead of assuming API controls are exposed by a built-in tool.
- Inspect existing audio, tools and model caches before downloading anything. Keep credentials in the environment and out of output, source control and this skill.
- Check current model rates and account availability. State the difference between an estimate, an actual charge, and unmetered/unknown session usage. A failed subscription is not permission to pay an invoice or switch providers; obtain the user's choice if the requested route cannot run. Do not retry a paid generation blindly after an ambiguous timeout.
- Write a microstory with a readable change: intention, obstacle, choice, consequence. Two short lines and one physical action often fit nine seconds. Preserve time to think and react instead of filling the runtime with speech.

## performance and timing

Generate the dialogue before final timing. Use a small cast of appropriate public voices or authorized references. Direct emotional intent and conversational delivery; avoid narration cadence for dialogue. Keep the raw take, exact request without credentials, model identity and any measured charge.

Use returned alignment when available. Otherwise align the known script or use an already-installed word-timestamp model, then inspect doubtful boundaries against the waveform and listening. A word end may include following silence. Character or word timestamps are not phoneme/syllable timestamps. Syllable alignment is usually unnecessary for held drawings without mouth animation. Whistle word starts can run about 0.25 s early before a pause, so take gap boundaries from `ffmpeg -af silencedetect=noise=-35dB:d=0.12` on the voice file.

Make a new drawing for a new thought, attitude, discovery, anticipation, action, contact or reaction. Do not cut automatically on every word, sentence, or fixed interval. A pose change can occur within one camera setup. Stressed words are cues, not edit commands. Hold a reaction long enough to read it; give fast physical actions fewer frames than considered emotional changes.

For a quiet nine-second first pass, roughly 6–12 drawings at a 24 fps export can be a useful hypothesis, with brief action poses and longer emotional holds. These are starting choices, not researched universal standards. Judge the actual performance and revise.

Keep a frame-based edit list: each drawing, integer frame count and intended beat; record audio offsets separately. Sum frames before rendering. Avoid optical flow, automatic mouth animation, constant camera drift and dissolves unless the particular story benefits from them.

## drawings

Make bitmap drawings with Codex image generation only, as the user requires; OpenRouter is for dialogue audio, never drawings. In a Claude thread, send drawings to a Codex child with `delegate_task` (provider `codex`). Establish one approved frame and reference it in subsequent generations. Lock character proportions, hair, costume, props, palette, lighting and screen geography. Use separate prompts for distinct drawings. For an adjacent action pair, reference the previous pose as well when composition must stay fixed.

Prompt each frame's camera setup, gaze, hand, prop orientation and emotional subtext. Favor clear silhouettes and legible faces/hands over extra rendering. Keep backgrounds subordinate. For colored pencil, request visible dry hatching and paper tooth, moderate facial detail and deliberate searching contour lines; avoid equating low API quality with attractive restrained drawing. Write where each prop is after every handover (held, or lying where); an unstated envelope stayed in a hand in one frame. Name jewellery and earrings in the continuity text; faint earring dots still appeared under "no jewellery".

Inspect every result: identity, hand anatomy, costume, prop count, direction of travel, eyelines and pose progression. Fix demonstrated faults with targeted changes. Independent frames can drift even when each is individually attractive.

## edit and verify

Assemble held frames around the actual audio, with minimal sound effects that support visible actions. Keep speech clear; avoid a music bed by default when it adds no story information. Optional subtitles should be selectable, not burned across drawings without a reason.

For exact holds in FFmpeg, use `-loop 1 -framerate 24 -i frame.png` per still, then `trim=end_frame=N,setpts=PTS-STARTPTS` for each video input, followed by the concat **filter**. Normalize dimensions and sample aspect ratios. Use the selected export fps throughout. The [FFmpeg filter manual](https://ffmpeg.org/ffmpeg-filters.html) documents trim, setpts and concat.

Encode a compatible H.264/yuv420p MP4 with AAC audio and `-movflags +faststart`. Check the VIDEO stream's `nb_frames`, duration and frame rate with ffprobe, plus actual cut timestamps in decoded frames (`-vf "select='gt(scene,0.2)',showinfo"` lists them). A nine-second container with nine-second audio can conceal a shorter video stream. Decode through the last frame; check missing/black frames, speech offsets, sound levels and the final hold. Inspect the rendered result, and listen where audio playback is available; do not claim to have listened based only on a transcript. Check speech onsets with per-0.1 s RMS of the MP4 audio: an `adelay` inside a multi-input `amix` graph was silently ignored, so delay each sound as its own WAV before mixing.

Deliver the watchable MP4, individual selected drawings, original dialogue, exact prompts, editable timing and a rebuild script. Keep source files needed to revise the film, but delete scratch previews, failed outputs, duplicate images and temporary renders. Report actual limitations and separately measured costs.

## provider and local findings

Observed 2026-11-10; recheck availability and prices for new work:

- **ElevenLabs:** `POST /v1/text-to-dialogue/with-timestamps` returns base64 audio, character alignment and voice segments. Check `GET /v1/models` and account status. `401 payment_issue` can occur despite successful authentication and remaining quota; stop that generation route rather than retrying or changing billing. Check first with `GET https://api.elevenlabs.io/v1/user/subscription`: `status: past_due` (seen 2026-11-10) means the route cannot run.
- **OpenRouter credits:** check `GET /api/v1/credits` (`total_credits` minus `total_usage`) before paid calls. On 2026-11-10 only $0.14 remained, enough for a TTS take but not for image work; topping up is the user's decision. [API](https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps), [pricing](https://elevenlabs.io/pricing/api).
- **OpenRouter Fish Drama 3:** use `POST https://openrouter.ai/api/v1/audio/speech`, model `fish-audio/drama-3`, `response_format: "mp3"`, and `input: [{text, voice, instructions}, ...]`. It returns raw audio and `X-Generation-Id`, not word alignment. Do not send the ordinary chat-completions audio schema. TTS discovery requires `GET /api/v1/models?output_modalities=speech`; the unfiltered list can omit these models. Instructions and inserted speaker tags also count toward billing. Read the live rate and retrieve actual charge using `/api/v1/generation?id=...`. [OpenRouter guide](https://openrouter.ai/docs/guides/overview/multimodal/tts).
- **Fish public cast:** Delia, female EN-US: `c70cfb98867a4bfb9ae20d2401257b92`; Adrian, male EN-US: `bf322df2096a46f18c579d0baa36f41d`. Check current [official cast and direction syntax](https://docs.fish.audio/features/text-to-speech/drama-3) before reuse. Use natural-language performance instructions rather than inventing an emotion parameter.
- **Installed Whistle on Ed's machine:** `/home/ed/.venvs/whistle/bin/python` has `needle.Whistle().transcribe(raw_bytes, language="en", word_timestamps=True)`. Feed 16 kHz mono f32le bytes from `ffmpeg -v error -i INPUT -ar 16000 -ac 1 -f f32le pipe:1` through a subprocess pipe; a path input expects WAV, so an MP3 path causes `wave.Error: file does not start with RIFF id`. Use `PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 NEEDLE_TELEMETRY=0` and existing caches. Its [80 ms timing resolution](https://www.cactuscompute.com/blog/whistle-best-practices) suits storyboard beats, not precision lip sync. Do not assume the existing HTTP voice wrapper exposes its word timings.
- **Codex imagegen:** this session's built-in tool exposed no quality/effort/model selector. The separate [Image API](https://developers.openai.com/api/docs/guides/image-generation) has controls that may differ by model. [Built-in images consume Codex limits](https://learn.chatgpt.com/docs/image-generation); without tool billing metadata, do not invent a per-image dollar cost or call them free.
- **Drawings via a Codex child (Claude threads):** `delegate_task` with provider `codex`, model `gpt-6.1-sol`, reasoningEffort `medium`, role `design`. Attach frame 01 as the reference. The 2026-11-10 run returned 1672×941 PNGs, so scale to 16:9 in the build. Regenerate one frame at a time under a `-v2` name and promote it after review.
- **OpenRouter TTS cost:** `GET /api/v1/generation?id=` can return nulls right after the call; ask again later for `total_cost` (2026-11-10: $0.000586 for 6 s of speech).
- **Export trap:** the first still-image concat-demuxer attempt produced only 191 video frames inside a nine-second container, with cuts one frame early. The loop/trim/concat-filter method produced all 216 frames and the intended cut times. Verify decoded output instead of trusting the command or container duration.

Pacing sources: [Pixar storyreels](https://www.khanacademy.org/partner-content/hass-storytelling/storytelling-pixar-in-a-box/ah-piab-pitching-and-feedback/v/pitching4), [Toon Boom panel timing](https://learn.toonboom.com/modules/animatic/topic/changing-the-panel-duration), and [Wendy Grieb's first-person storyboard advice](https://www.creativebloq.com/advice/storyboard-tips).

## learn after every use

After each use, and whenever the user gives feedback on its output, update this skill before finishing that follow-up. Record only demonstrated improvements: the observed problem or preference, the narrow correction, and a working command when relevant. Put timing lessons in timing, visual preferences in drawings, and provider failures in local findings; revise existing guidance instead of growing a repetitive log. Preserve the user's feedback accurately and scope project-specific preferences to that project. Remove superseded guidance. Do not turn one sample's timing, promotional price or machine path into a universal requirement. Never record credentials, account identifiers or private dialogue here. If a use reveals no new finding, do not invent one or churn the file.
