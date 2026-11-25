#!/usr/bin/env bash
# Guard the second decidr call: a leaf is a verdict, never another request.
set -euo pipefail
model=${1:-}
if [ "$#" -gt 0 ]; then shift; fi
project=${SC_PROJECT:-}
agent_role=${DECIDR_AGENT_ROLE:-}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --project|--agent-role)
      if [ "$#" -lt 2 ]; then printf '%s requires a value\n' "$1" >&2; exit 2; fi
      if [ "$1" = --project ]; then project=$2; else agent_role=$2; fi
      shift 2
      ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done
payload=''
IFS= read -r payload || [ -n "$payload" ] || exit 0
route=$(printf '%s\n' "$payload" | jq -er '
  if has("questions") then "request"
  elif .verdict == "yes" and .stage == "gates" then "leaf"
  else error("Expected a next request or a gate leaf") end')
case "$route" in
  request)
    if [ -z "$model" ] || [ -z "$project" ] || [ -z "$agent_role" ]; then
      printf '%s\n' 'A request needs MODEL, --project (or SC_PROJECT), and --agent-role (or DECIDR_AGENT_ROLE).' >&2
      exit 2
    fi
    printf '%s\n' "$payload" | decidr send --project "$project" \
      --agent-role "$agent_role" --model "$model"
    ;;
  leaf) printf '%s\n' "$payload" ;;
esac
