#!/usr/bin/env bash
# CPIS JSON Gate v1.2 — deploy verification script
# Run after installing the plugin to verify everything works.
#
# Usage: bash scripts/verify-deploy.sh

set -euo pipefail

echo "=============================="
echo " CPIS JSON Gate v1.2 — Verify"
echo "=============================="
echo ""

# 1. Check plugin is loaded
echo "--- Checking plugin ---"
openclaw plugins inspect cpis-json-gate --runtime --json 2>&1 || {
  echo "FAIL: plugin not loaded"
  exit 1
}

# 2. Check version
VERSION_LINE=$(openclaw plugins inspect cpis-json-gate --runtime --json 2>&1 | grep -E '"version"' || true)
if echo "$VERSION_LINE" | grep -q '"1.2.0"'; then
  echo "PASS: version 1.2.0"
else
  echo "FAIL: expected 1.2.0, got: $VERSION_LINE"
  exit 1
fi

# 3. Check hooks
echo "--- Checking hooks ---"
HOOK_INFO=$(openclaw plugins inspect cpis-json-gate --runtime --json 2>&1)
if echo "$HOOK_INFO" | grep -q "before_tool_call"; then
  echo "PASS: before_tool_call hook registered"
else
  echo "FAIL: before_tool_call hook not found"
  exit 1
fi
if echo "$HOOK_INFO" | grep -q "before_agent_finalize"; then
  echo "PASS: before_agent_finalize hook registered"
else
  echo "FAIL: before_agent_finalize hook not found"
  exit 1
fi

# 4. Check plugins config has allowConversationAccess
echo "--- Checking config ---"
CONFIG_ACCESS=$(openclaw config get plugins.entries.cpis-json-gate.hooks.allowConversationAccess 2>&1 || echo "")
if [ "$CONFIG_ACCESS" = "true" ]; then
  echo "PASS: allowConversationAccess = true"
else
  echo "WARNING: allowConversationAccess is not set. Run:"
  echo "  openclaw config set plugins.entries.cpis-json-gate.hooks.allowConversationAccess true"
fi

echo ""
echo "--- Running unit tests ---"
cd "$(dirname "$0")/../openclaw-plugins/cpis-json-gate"
npm test 2>&1 || {
  echo "FAIL: unit tests"
  exit 1
}

echo ""
echo "=============================="
echo " CPIS JSON Gate v1.2 — PASSED"
echo "=============================="
