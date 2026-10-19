---
name: whistle-word-times
description: Transcribe audio in the browser with Cactus Whistle (ONNX, WebGPU or WASM, no server) and get the time each word is said. Use when a web app needs speech-to-text with word timestamps, karaoke-style word highlight, words placed on a waveform, or click-a-word-to-seek.
---

# Whistle word times

## How the times are found
1. The decoder writes text pieces one at a time. With `timestamps: true` it also saves each step's cross-attention: which audio frames it looked at for that piece.
2. `tokenFrames` in `whistle.js` runs DTW over that attention matrix, matching each piece to one audio frame and always moving forward.
3. Pieces join into words wherever a piece starts with `▁`.
4. A word's `start` is its first piece's frame × `FRAME_S`. Its `end` is the next word's start.
These times are estimates from attention, so they can be tens of ms off. Don't use them for sample-accurate edits.

## Setup
- Copy `static/whistle/` from a working app (`~/i/chunkflip` or `~/i/fl`): `worker.js whistle.js backend.js pack.js whistle.pack onnx/ NOTICE.md`, about 20 MB. Keep NOTICE.md for the Apache-2.0 notice.
- onnxruntime-web loads from jsDelivr at runtime, so the first load needs the network. The weight pack is cached after that.
- Leave `static/whistle/` out of eslint and prettier, because it's vendored code.

## Worker protocol
```ts
const w = new Worker('/whistle/worker.js', { type: 'module' });
w.postMessage({ type: 'init', cfg: {} }); // start the load early, e.g. when a file is picked
w.postMessage({ type: 'transcribe', id, partial: false, pcm, language: null, keywords: null, timestamps: true }, [pcm.buffer]);
// in: status {text} | progress {loaded,total} | ready | result {id, result:{text, words:[{word,start,end,probability}]}} | error {id?, text}
```
- `pcm` must be a mono Float32Array at 16 kHz. Resample with `OfflineAudioContext(1, ceil(dur*16000), 16000)`.
- Pass a copy of the samples, because transferring the buffer empties the original.
- An error with no `id` means the load failed. Reject every pending job.
- Jobs run in order, so to drop stale results, compare a sequence number on the caller side.

## Long audio
Split it into windows of 25 s or less and add `window_start / 16000` to every word's `start` and `end`. Reference code: `~/i/chunkflip/src/lib/whistle.ts` (`transcribe`).
