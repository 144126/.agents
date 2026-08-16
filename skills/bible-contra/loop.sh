#!/usr/bin/env bash
# Run the bible-contra hunt unattended, one pass per agent invocation.
# Usage: loop.sh [passes]            default 20
#        BCON_AGENT="opencode run" loop.sh 100
set -u

PASSES="${1:-20}"
AGENT="${BCON_AGENT:-claude -p --dangerously-skip-permissions}"
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BCON="python3 $SKILL/bcon.py"

$BCON init >/dev/null || exit 1

PROMPT="Read $SKILL/SKILL.md and follow it for exactly one pass. \
Start with 'python3 $SKILL/bcon.py brief', do the job it prints, \
and finish with 'python3 $SKILL/bcon.py done'. Do not run more than one pass."

for i in $(seq 1 "$PASSES"); do
  echo "=== pass $i/$PASSES  $(date +%H:%M:%S) ==="
  $AGENT "$PROMPT" || echo "(agent exited non-zero, continuing)"
  $BCON stats
done
