#!/usr/bin/env bash
set -euo pipefail
for agent in cpis-info-collector cpis-product-analyst cpis-knowledge-curator; do
  file="$HOME/.openclaw/workspace-$agent/AGENTS.md"
  count="$(grep -c '<!-- CPIS_V2_RULES_START -->' "$file" || true)"
  if [[ "$count" != "1" ]]; then printf 'FAIL %s: expected one V2 block, found %s\n' "$agent" "$count"; exit 1; fi
  printf 'PASS %s\n' "$agent"
done

grep -q 'CPIS V2 图片交接硬约束' "$HOME/.openclaw/workspace-cpis-info-collector/AGENTS.md"
grep -q 'CPIS V2 图片字段透传硬约束' "$HOME/.openclaw/workspace-cpis-product-analyst/AGENTS.md"
grep -q 'CPIS V2 飞书图片发布硬约束' "$HOME/.openclaw/workspace-cpis-knowledge-curator/AGENTS.md"
printf 'PASS CPIS image handoff and upload rules\n'

openclaw plugins inspect cpis-json-gate --runtime --json | grep -E '"version": "1.1.0"|"status": "loaded"|"name": "before_tool_call"|"priority": 1000'
printf '\nCPIS rules and JSON Gate are present.\n'
