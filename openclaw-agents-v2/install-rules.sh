#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install_rules(){ local agent_id="$1" source_file="$2" workspace="$HOME/.openclaw/workspace-$agent_id" target="$workspace/AGENTS.md" temp_file; mkdir -p "$workspace"; touch "$target"; cp "$target" "$target.bak.$(date +%Y%m%d%H%M%S)"; temp_file="$(mktemp)"; awk '/<!-- CPIS_V2_RULES_START -->/{skip=1;next}/<!-- CPIS_V2_RULES_END -->/{skip=0;next}!skip{print}' "$target" > "$temp_file"; { cat "$temp_file"; printf '\n'; cat "$BASE_DIR/$source_file"; printf '\n'; } > "$target"; rm -f "$temp_file"; printf 'Updated %s\n' "$target"; }
install_rules cpis-info-collector collector-rules.md
install_rules cpis-product-analyst analyst-rules.md
install_rules cpis-knowledge-curator curator-rules.md
openclaw gateway restart
printf '\nInstalled CPIS V2 rules.\n'
