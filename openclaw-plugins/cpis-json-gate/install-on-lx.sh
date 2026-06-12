#!/usr/bin/env bash
set -euo pipefail
PLUGIN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
node --version
npm --version
if [[ -d "$HOME/.openclaw/extensions/cpis-json-gate" ]]; then
  openclaw gateway stop
  cp -a "$HOME/.openclaw/extensions/cpis-json-gate" "$HOME/.openclaw/extensions/cpis-json-gate.backup.$(date +%Y%m%d%H%M%S)"
  cp -a "$PLUGIN_DIR/dist" "$PLUGIN_DIR/package.json" "$PLUGIN_DIR/openclaw.plugin.json" "$HOME/.openclaw/extensions/cpis-json-gate/"
  openclaw gateway start
else
  openclaw plugins install "$PLUGIN_DIR"
  openclaw plugins enable cpis-json-gate
  openclaw gateway restart
fi
openclaw plugins inspect cpis-json-gate --runtime --json
printf '\nCPIS JSON Gate installed or upgraded.\n'
