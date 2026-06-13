#!/usr/bin/env bash
# Install/upgrade CPIS JSON Gate
# Usage: bash openclaw-plugins/cpis-json-gate/install-on-lx.sh

set -euo pipefail
PLUGIN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "Node version:"
node --version
echo "npm version:"
npm --version
echo ""

# ── Run unit tests first ──
echo "--- Running unit tests ---"
(cd "$PLUGIN_DIR" && npm test 2>&1) || {
  echo "FAIL: unit tests failed. Aborting installation."
  exit 1
}
echo ""

# ── Install/upgrade plugin ──
if [[ -d "$HOME/.openclaw/extensions/cpis-json-gate" ]]; then
  echo "Upgrading existing plugin..."
  openclaw gateway stop
  cp -a "$HOME/.openclaw/extensions/cpis-json-gate" "$HOME/.openclaw/extensions/cpis-json-gate.backup.$(date +%Y%m%d%H%M%S)"
  cp -a "$PLUGIN_DIR/dist" "$PLUGIN_DIR/package.json" "$PLUGIN_DIR/openclaw.plugin.json" "$HOME/.openclaw/extensions/cpis-json-gate/"
  openclaw gateway start
else
  echo "Installing fresh plugin..."
  openclaw plugins install "$PLUGIN_DIR"
  openclaw plugins enable cpis-json-gate
  openclaw gateway restart
fi
echo ""

# ── WARNING: allowConversationAccess is REQUIRED for v1.2 ──
echo "--- Checking config ---"
# before_agent_finalize hook needs allowConversationAccess=true
CONFIG_ACCESS=$(openclaw config get plugins.entries.cpis-json-gate.hooks.allowConversationAccess 2>&1 || echo "")
if [ "$CONFIG_ACCESS" != "true" ]; then
  echo "WARNING: allowConversationAccess is not set."
  echo "This is REQUIRED for before_agent_finalize to work."
  echo "Run the following AFTER the gateway starts:"
  echo ""
  echo '  openclaw config set plugins.entries.cpis-json-gate.hooks.allowConversationAccess true'
  echo ""
else
  echo "OK: allowConversationAccess = true"
fi

echo ""
echo "--- Verifying runtime ---"
openclaw plugins inspect cpis-json-gate --runtime --json 2>&1
echo ""
printf 'CPIS JSON Gate v1.2 installed or upgraded successfully.\n'
printf 'Remember: run verify-deploy.sh to confirm everything works.\n'
