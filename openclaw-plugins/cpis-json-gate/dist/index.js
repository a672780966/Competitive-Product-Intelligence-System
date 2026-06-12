import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { formatBlockReason, validateSessionsSend } from "./validator.js";

export default definePluginEntry({
  id: "cpis-json-gate",
  name: "CPIS JSON Gate",
  description: "Hard JSON and routing validation for the CPIS three-agent workflow.",
  register(api) {
    api.on(
      "before_tool_call",
      async (event, ctx) => {
        if (event.toolName !== "sessions_send") return;
        const result = validateSessionsSend({ agentId: ctx.agentId, params: event.params });
        if (!result.applicable || result.valid) return;
        return { block: true, blockReason: formatBlockReason(result.errors) };
      },
      { priority: 1000, timeoutMs: 5000 },
    );
  },
});
