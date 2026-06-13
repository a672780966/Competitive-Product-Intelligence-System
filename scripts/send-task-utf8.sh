#!/usr/bin/env bash
# CPIS — UTF-8 safe task submission for OpenClaw agents.
# Usage:
#   bash scripts/send-task-utf8.sh cpis-info-collector examples/task-evidence.json
#   bash scripts/send-task-utf8.sh cpis-knowledge-curator examples/task-publish.json
#
# Purpose:
#   Avoids terminal locale / shell encoding corruption of Chinese characters
#   by reading task JSON from a UTF-8 file instead of pasting into the shell.
#   Requires that $HOME/.openclaw/openclaw-agent.json is configured.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <agent-id> <json-task-file>" >&2
  echo "" >&2
  echo "Examples:" >&2
  echo "  $0 cpis-info-collector examples/task-evidence.json" >&2
  echo "  $0 cpis-knowledge-curator examples/task-publish.json" >&2
  exit 1
fi

AGENT_ID="$1"
TASK_FILE="$2"

if [[ ! -f "$TASK_FILE" ]]; then
  echo "Error: file not found: $TASK_FILE" >&2
  exit 1
fi

# Read as raw bytes — no locale-based re-encoding
TASK_JSON="$(cat "$TASK_FILE")"

# Validate JSON is parseable
if ! echo "$TASK_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" > /dev/null 2>&1; then
  echo "Error: invalid JSON in $TASK_FILE" >&2
  exit 1
fi

echo "Submitting task to $AGENT_ID..."
echo "Task: $(echo "$TASK_JSON" | head -c 200)..."
echo ""

# Submit via OpenClaw CLI using --file to pass stdin
openclaw agent send "$AGENT_ID" --message-stdin < "$TASK_FILE" 2>&1

echo ""
echo "Done."
