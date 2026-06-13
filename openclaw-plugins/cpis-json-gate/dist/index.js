import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { formatBlockReason, validatePublishResult, validateSessionsSend } from "./validator.js";

export default definePluginEntry({
  id: "cpis-json-gate",
  name: "CPIS JSON Gate",
  description: "Hard JSON, routing, and finalize validation for the CPIS three-agent workflow.",
  register(api) {
    // v1.1: before_tool_call — block invalid sessions_send
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

    // v1.2: before_agent_finalize — enforce publish_result JSON for curator
    api.on(
      "before_agent_finalize",
      async (event, ctx) => {
        // Only apply to cpis-knowledge-curator
        if (ctx.agentId !== "cpis-knowledge-curator") return;

        const text = event.lastAssistantMessage;
        if (!text || typeof text !== "string") return;

        const result = validatePublishResult(text);

        if (result.valid) return; // pass

        // Need to revise — metadata for the runtime
        return {
          action: "revise",
          reason: formatBlockReason(result.errors),
          maxAttempts: 1,
        };
      },
      { priority: 1000, timeoutMs: 5000 },
    );
  },
});
