#!/usr/bin/env bash
# speak_doc — read text (or a file) aloud verbatim via OpenRouter Kokoro TTS
# (voice af_heart, pcm). Always saves the raw PCM to ~/doc_tts/<name>.pcm (every
# caller gets the file for free), then plays it with sox; press Ctrl+S to stop.
#
# Usage:
#   speak_doc <name>                 # read text from stdin, save as <name>.pcm
#   speak_doc <file>                 # read the file VERBATIM (chunked TTS)
#   speak_doc <name> <file>          # read file, save as <name>.pcm
#   speak_doc --file <file>          # read file, name from filename
#   cat file | speak_doc <name>      # stdin still works
#
# Text is read verbatim; long input is split into chunks (Kokoro has an input
# token limit) and each chunk is synthesized + concatenated. Requests are
# retried with backoff on 429 / connection reset. No summarization is performed.
#
# Requires: curl, jq, base64, play (sox). No OpenCode needed.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers (defined first so they are available to the main flow below)
# ---------------------------------------------------------------------------

# Load the OpenRouter key: OPENROUTER_KEY in the environment wins, else ~/i/e4/.env.
load_openrouter_key() {
  local key="${OPENROUTER_KEY:-}"
  local env_file="${HOME}/i/e4/.env"
  if [[ -z "${key}" && -r "${env_file}" ]]; then
    key="$(grep -E '^OPENROUTER_KEY=' "${env_file}" | head -1 | cut -d= -f2- | sed 's/^["'"'"']//; s/["'"'"']$//')"
  fi
  if [[ -z "${key}" ]]; then
    echo "speak-doc: no OpenRouter key. Export OPENROUTER_KEY, or add OPENROUTER_KEY=... to ${env_file}." >&2
    return 1
  fi
  printf '%s' "${key}"
}

# Synthesize one chunk with retry/backoff. Echoes raw PCM bytes to stdout.
synthesize_chunk() {
  local text="$1"
  local attempt=0
  local max_attempts=6
  local backoff=5
  while (( attempt < max_attempts )); do
    attempt=$((attempt + 1))
    local http_code
    local body
    body="$(curl -sS --max-time 120 -o /tmp/speak_doc_chunk.$$ -w '%{http_code}' \
      -X POST "https://openrouter.ai/api/v1/audio/speech" \
      -H "Authorization: Bearer ${OPENROUTER_KEY}" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --arg t "${text}" --arg v "${VOICE}" --arg m "${MODEL}" \
            '{model:$m, input:$t, voice:$v, response_format:"pcm"}')")"
    http_code="${body}"

    if [[ "${http_code}" == "200" && -s /tmp/speak_doc_chunk.$$ ]]; then
      cat /tmp/speak_doc_chunk.$$
      rm -f /tmp/speak_doc_chunk.$$
      return 0
    fi

    # Inspect error for rate limit / other.
    local err
    err="$(head -c 300 /tmp/speak_doc_chunk.$$ 2>/dev/null)"
    rm -f /tmp/speak_doc_chunk.$$
    if [[ "${http_code}" == "429" ]]; then
      local retry_delay=15
      echo "speak_doc: rate limited (429), waiting ${retry_delay}s (attempt ${attempt}/${max_attempts})" >&2
      sleep "${retry_delay}"
    else
      echo "speak_doc: chunk ${attempt} failed (HTTP ${http_code}); retrying in ${backoff}s" >&2
      sleep "${backoff}"
      backoff=$((backoff * 2))
      if (( backoff > 60 )); then backoff=60; fi
    fi
  done
  echo "speak_doc: giving up after ${max_attempts} attempts on a chunk" >&2
  return 1
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SHORT_NAME=""
FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file|-f)
      FILE="$2"
      shift 2
      ;;
    *)
      if [[ -z "${SHORT_NAME}" ]]; then
        SHORT_NAME="$1"
      elif [[ -z "${FILE}" ]]; then
        FILE="$1"
      fi
      shift
      ;;
  esac
done

# Single positional that is an existing file -> treat as the file, name from it.
if [[ -z "${FILE}" && -n "${SHORT_NAME}" && -f "${SHORT_NAME}" ]]; then
  FILE="${SHORT_NAME}"
  SHORT_NAME="$(basename "${FILE}")"
  SHORT_NAME="${SHORT_NAME%.*}"
fi

[[ -z "${SHORT_NAME}" ]] && SHORT_NAME="doc"

if [[ -n "${FILE}" ]]; then
  if [[ ! -f "${FILE}" ]]; then
    echo "speak_doc: file not found: ${FILE}" >&2
    exit 1
  fi
  TEXT="$(cat "${FILE}")"
else
  TEXT="$(cat)"
fi

# OpenRouter config (active). Key from OPENROUTER_KEY or ~/i/e4/.env.
OPENROUTER_KEY="$(load_openrouter_key)" || exit 1
MODEL="hexgrad/kokoro-82m"        # Kokoro TTS
VOICE="af_heart"

# Output is always saved under ~/doc_tts so any skill/command using this
# script gets the pcm file without saving it themselves.
OUT_DIR="${HOME}/doc_tts"
OUT_FILE="${OUT_DIR}/${SHORT_NAME}.pcm"

mkdir -p "${OUT_DIR}"

if [[ -z "${TEXT}" ]]; then
  echo "speak_doc: no text provided (stdin empty or file empty)" >&2
  exit 1
fi

CHUNK_CHARS=5500  # stay safely under the model's input token limit

# Split TEXT into chunks of at most CHUNK_CHARS, breaking at word boundaries.
mapfile -t CHUNKS < <(
  awk -v max="${CHUNK_CHARS}" '
    BEGIN { buf = "" }
    {
      for (i = 1; i <= NF; i++) {
        w = $i
        if (length(buf) > 0 && length(buf) + length(w) + 1 > max) {
          print buf
          buf = w
        } else {
          buf = (buf == "" ? w : buf " " w)
        }
      }
    }
    END { if (buf != "") print buf }
  ' <<<"${TEXT}"
)

echo "speak_doc: ${#CHUNKS[@]} chunk(s) to synthesize" >&2

# --- Synthesize all chunks, concatenating PCM into the output file ---
: > "${OUT_FILE}"
for i in "${!CHUNKS[@]}"; do
  echo "speak_doc: synthesizing chunk $((i + 1))/${#CHUNKS[@]}" >&2
  if ! synthesize_chunk "${CHUNKS[$i]}" >>"${OUT_FILE}"; then
    echo "speak_doc: TTS failed on chunk $((i + 1))" >&2
    exit 1
  fi
done

if [[ ! -s "${OUT_FILE}" ]]; then
  echo "speak_doc: TTS returned empty audio" >&2
  exit 1
fi

echo "speak_doc: saved ${OUT_FILE} ($(wc -c < "${OUT_FILE}") bytes)"
echo "speak_doc: playing. Press Ctrl+S to stop."

# --- Play PCM (Kokoro outputs 24000 Hz, 16-bit, mono raw) ---
# Run in background so we can trap Ctrl+S (SIGINT) to stop playback.
play -t raw -r 24000 -e signed -b 16 -c 1 -q "${OUT_FILE}" &
PLAY_PID=$!

cleanup() {
  if kill -0 "${PLAY_PID}" 2>/dev/null; then
    kill -INT "${PLAY_PID}" 2>/dev/null || true
    wait "${PLAY_PID}" 2>/dev/null || true
    echo "speak_doc: playback stopped."
  fi
}
trap cleanup EXIT INT TERM

# Block until playback finishes (or Ctrl+S -> SIGINT -> cleanup).
wait "${PLAY_PID}" 2>/dev/null || true
