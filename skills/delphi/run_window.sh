#!/usr/bin/env bash
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
dir=$(cd "$(dirname "$0")" && pwd)
asset=${1%%-*}
window=${2:-${1#*-}}
home=${DELPHI_HOME:-$HOME/.local/share/delphi}
cfg=${DELPHI_CONFIG:-$HOME/.config/delphi}
tag=$asset-$window
dd=$home/decisions
mkdir -p "$dd"
exec 9>"$dd/$tag.lock"
flock -n 9 || exit 0
log() { printf '%s %s %s\n' "$(date -u +%FT%TZ)" "$tag" "$*" >>"$home/runs.log"; }
[ -e "$cfg/KILL" ] && { log KILL; exit 0; }
run() { timeout 90 uv run --script "$dir/delphi.py" "$@"; }
dec=$dd/$tag.json
llm=$dd/$tag.llm
fresh=$dd/$tag.fresh.json
run decide --asset "$asset" --window "$window" >"$dec" || true
[ -s "$dec" ] || { log '{"action":"NO_BET","reasons":["engine_timeout"]}'; exit 0; }
: >"$llm"
rm -f "$fresh"
if [ "$(jq -r .action "$dec")" != NO_BET ]; then
  if [ -f "$dir/pi/operator.md" ]; then
    timeout 15 pi -p --provider openrouter --model deepseek/deepseek-v4.1-flash -nt -nc -ns -ne --no-mcp --no-session \
      --system-prompt "$(cat "$dir/pi/operator.md")" "$(cat "$dec")" >"$llm" 2>/dev/null </dev/null || : >"$llm"
  fi
  run decide --asset "$asset" --window "$window" >"$fresh" 2>/dev/null || rm -f "$fresh"
fi
args=(--decision "$dec" --llm "$llm")
[ -s "$fresh" ] && args+=(--fresh "$fresh")
final=$(run judge "${args[@]}") || final=""
[ -n "$final" ] || { log '{"action":"NO_BET","reasons":["judge_error"]}'; exit 0; }
flag=()
[ "${DELPHI_LIVE:-}" = 1 ] && flag=(--live)
res=$(printf '%s' "$final" | run trade --decision - "${flag[@]}") || true
log "$final $res"
