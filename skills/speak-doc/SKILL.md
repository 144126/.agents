---
name: speak-doc
description: "Compress a body of text into statements of fact and read it aloud via Gemini TTS (voice Kore, pcm). Saves audio to ~/doc_tts and supports Ctrl+S to stop playback."
---

# Speak Doc

Turns a body of text into a spoken summary. The model first compresses the text
into a clean series of statements of fact, then the result is synthesized with
Gemini TTS and played aloud.

## What it does

1. **Compress** the user-provided text per the instructions below — the model
   performs this transform directly when the skill/command is invoked.
2. **Synthesize** the compressed text with Gemini TTS (`gemini-2.5-flash-preview-tts`,
   voice `Kore`, `response_format: pcm`) using the fixed key baked into the script.
3. **Save** the raw PCM to `~/doc_tts/<short_name>.pcm` (always, for every caller).
4. **Play** it with `sox` (`play`). Press **Ctrl+S** to stop playback.

## The `speak_doc` command

The script lives at `~/.agents/skills/speak-doc/lib/speak_doc.sh` and is
symlinked onto PATH as `speak_doc`, so you can run it from anywhere:

```bash
# read text from stdin
echo "some text" | speak_doc myname

# read a file directly (name derived from filename)
speak_doc path/to/notes.txt

# explicit name + file
speak_doc myname path/to/notes.txt

# stop with Ctrl+S
```

Aliases `s` and `sd` also map to `speak_doc`, so `s notes.txt` works.

## Compression instructions

Run these instructions on the user-provided text:

```text
Go through the text line by line,
and delete any line that does not present new information.
For all the lines remaining,
remove any overly formal language, conversational filler, and conversational tones so that the document is simply a series of statements of fact.
```

Apply them to the text, then pass the compressed result to `speak_doc`.

## Trigger

Invoke via the `/speak-doc` slash command, or call `speak_doc` directly.
Use when the user says "speak this doc", "read this out", "compress and read",
or provides a body of text or file to be summarized aloud.
