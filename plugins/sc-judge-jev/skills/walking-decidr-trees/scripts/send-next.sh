#!/usr/bin/env bash
# Guard the second decidr call: a leaf is a verdict, never another request.
set -euo pipefail
IFS= read -r payload || exit 0
route=$(printf '%s\n' "$payload" | jq -er '
  if has("questions") then "request"
  elif .verdict == "yes" and .stage == "gates" then "leaf"
  else error("Expected a next request or a gate leaf") end')
case "$route" in
  request)
    printf '%s\n' "$payload" | decidr send --project decidr-question-tree \
      --agent-role skill-author --model "${1:?second-stage model required}"
    ;;
  leaf) printf '%s\n' "$payload" ;;
esac
