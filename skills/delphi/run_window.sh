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
t=$(mktemp -d "$dd/run.XXXXXX")
dec=$dd/$tag.json
llm=$dd/$tag.llm
fresh=$dd/$tag.fresh.json
start_utc=$(date -u +%FT%TZ)
start_ms=$(date +%s%3N)
agents_git=$(git -C "$HOME/.agents" rev-parse --short HEAD 2>/dev/null)
mode=paper
[ "${DELPHI_LIVE:-}" = 1 ] && mode=live
kill_file=false
[ -e "$cfg/KILL" ] && kill_file=true
llm_called=0
llm_rc=
llm_ms=
final=
res=
trade_rc=
emit() {
  E_START_UTC=$start_utc E_START_MS=$start_ms E_ASSET=$asset E_WINDOW=$window \
  E_DEC=$dec E_FRESH=$fresh E_LLM_RAW=$t/llm.raw E_LLM_CALLED=$llm_called \
  E_LLM_RC=$llm_rc E_LLM_MS=$llm_ms E_JUDGE=$final E_TRADE_RC=$trade_rc \
  E_TRADE=$res E_TMP=$t E_MODE=$mode E_KILL=$kill_file E_GIT=$agents_git \
  E_OUT=$home/runs.jsonl python3 -I - <<'PY' || true
import datetime, json, os, time

def env(k):
    return os.environ.get(k, "")

def text(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""

def tail(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 1024))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""

def obj(s):
    try:
        v = json.loads(s)
    except ValueError:
        return None
    return v if isinstance(v, dict) else None

def num(s):
    return int(s) if s.lstrip("-").isdigit() else None

def sys_read(name):
    try:
        with open("/sys/class/power_supply/BAT0/" + name) as f:
            return f.read().strip()
    except OSError:
        return None

def iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

dec = obj(text(env("E_DEC")))
fresh = obj(text(env("E_FRESH")))
judge = obj(env("E_JUDGE"))
raw = text(env("E_LLM_RAW"))
called = env("E_LLM_CALLED") == "1"
reasons = judge.get("reasons", []) if judge else []
mismatch = ",".join(r for r in reasons if isinstance(r, str) and r.startswith("llm_"))
cap = sys_read("capacity")
end = time.time()
rec = {
    "start_utc": env("E_START_UTC"),
    "end_utc": iso(end),
    "duration_ms": int(end * 1000) - int(env("E_START_MS")),
    "asset": env("E_ASSET"),
    "window": env("E_WINDOW"),
    "slug": (dec or {}).get("slug"),
    "phase": (dec or {}).get("phase"),
    "secs_left": (dec or {}).get("secs_left"),
    "decide": dec,
    "llm": {
        "called": called,
        "exit_code": num(env("E_LLM_RC")),
        "latency_ms": num(env("E_LLM_MS")),
        "stdout": raw.encode()[:2048].decode("utf-8", "ignore"),
        "parsed": (obj(raw.strip()) is not None) if called else None,
        "mismatch": mismatch or None,
    },
    "fresh": fresh,
    "judge": judge,
    "trade": {"exit_code": num(env("E_TRADE_RC")), "output": env("E_TRADE")},
    "stderr": {k: tail(os.path.join(env("E_TMP"), k + ".err")) for k in ("decide", "llm", "fresh", "judge", "trade")},
    "mode": env("E_MODE"),
    "kill_file": env("E_KILL") == "true",
    "battery": {"capacity": int(cap) if cap and cap.isdigit() else None, "status": sys_read("status")},
    "agents_git": env("E_GIT") or None,
}
data = (json.dumps(rec, separators=(",", ":")) + "\n").encode()
fd = os.open(env("E_OUT"), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
try:
    os.write(fd, data)
finally:
    os.close(fd)
PY
  rm -rf -- "$t"
}
trap emit EXIT
trap 'exit 143' INT TERM HUP
log() { printf '%s %s %s\n' "$(date -u +%FT%TZ)" "$tag" "$*" >>"$home/runs.log"; }
[ "$kill_file" = true ] && { log KILL; exit 0; }
run() { timeout 90 uv run --script "$dir/delphi.py" "$@"; }
run decide --asset "$asset" --window "$window" >"$dec" 2>"$t/decide.err" || true
[ -s "$dec" ] || { log '{"action":"NO_BET","reasons":["engine_timeout"]}'; exit 0; }
: >"$llm"
rm -f "$fresh"
if [ "$(jq -r .action "$dec")" != NO_BET ]; then
  if [ -f "$dir/pi/operator.md" ]; then
    llm_called=1
    t0=$(date +%s%3N)
    timeout 15 pi -p --provider openrouter --model deepseek/deepseek-v4.1-flash -nt -nc -ns -ne --no-mcp --no-session \
      --system-prompt "$(cat "$dir/pi/operator.md")" "$(cat "$dec")" >"$t/llm.raw" 2>"$t/llm.err" </dev/null
    llm_rc=$?
    llm_ms=$(( $(date +%s%3N) - t0 ))
    if [ "$llm_rc" = 0 ]; then cp "$t/llm.raw" "$llm"; else : >"$llm"; fi
  fi
  run decide --asset "$asset" --window "$window" >"$fresh" 2>"$t/fresh.err" || rm -f "$fresh"
fi
args=(--decision "$dec" --llm "$llm")
[ -s "$fresh" ] && args+=(--fresh "$fresh")
final=$(run judge "${args[@]}" 2>"$t/judge.err") || final=""
[ -n "$final" ] || { log '{"action":"NO_BET","reasons":["judge_error"]}'; exit 0; }
flag=()
[ "${DELPHI_LIVE:-}" = 1 ] && flag=(--live)
res=$(printf '%s' "$final" | run trade --decision - "${flag[@]}" 2>"$t/trade.err"); trade_rc=$?
log "$final $res"
