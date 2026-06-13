import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { validatePublishResult, validateSessionsSend } from "../dist/validator.js";

// ──────────────────────────────────────────────
// validatePublishResult unit tests (v1.2)
// ──────────────────────────────────────────────
function validPublishJson(overrides = {}) {
  return JSON.stringify({
    schema_version: "1.0",
    object_type: "publish_result",
    run_id: "amazon_us_tens_20260613_e2e001",
    agent_id: "cpis-knowledge-curator",
    status: "success",
    published: true,
    message_zh: "测试中文",
    message_en: "test English",
    feishu_url: "https://feishu.cn/docx/TJBnduVpmofKEpxPP6dcRd3Ende",
    images_expected: 2,
    images_uploaded: 2,
    image_failures: [],
    ...overrides,
  });
}

describe("validatePublishResult", () => {
  it("accepts a valid publish_result", () => {
    const r = validatePublishResult(validPublishJson());
    assert.equal(r.valid, true);
    assert.deepEqual(r.errors, []);
  });

  it("rejects empty text", () => {
    const r = validatePublishResult("");
    assert.equal(r.valid, false);
  });

  it("rejects Markdown fences", () => {
    const r = validatePublishResult("```json\n" + validPublishJson() + "\n```");
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("fence") || e.includes("Fence")));
  });

  it("rejects invalid JSON", () => {
    const r = validatePublishResult("{not json}");
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("invalid JSON")));
  });

  it("rejects non-object JSON", () => {
    const r = validatePublishResult('["array"]');
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("single JSON object")));
  });

  it("rejects unknown fields", () => {
    const r = validatePublishResult(validPublishJson({ extra_field: "nope" }));
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("extra_field")));
  });

  it("rejects wrong object_type", () => {
    const r = validatePublishResult(validPublishJson({ object_type: "agent_handoff" }));
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("object_type")));
  });

  it("rejects wrong schema_version", () => {
    const r = validatePublishResult(validPublishJson({ schema_version: "2.0" }));
    assert.equal(r.valid, false);
  });

  it("rejects missing run_id", () => {
    const r = validatePublishResult(validPublishJson({ run_id: "" }));
    assert.equal(r.valid, false);
  });

  it("rejects missing agent_id", () => {
    const r = validatePublishResult(validPublishJson({ agent_id: "" }));
    assert.equal(r.valid, false);
  });

  it("rejects invalid status", () => {
    const r = validatePublishResult(validPublishJson({ status: "changed" }));
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("status")));
  });

  it("accepts partial and failed status", () => {
    assert.equal(validatePublishResult(validPublishJson({ status: "partial" })).valid, true);
    assert.equal(validatePublishResult(validPublishJson({ status: "failed" })).valid, true);
  });

  it("rejects non-boolean published", () => {
    const r = validatePublishResult(validPublishJson({ published: "yes" }));
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("published")));
  });

  it("allows published=false without feishu_url", () => {
    const r = validatePublishResult(validPublishJson({
      published: false,
      feishu_url: null,
    }));
    assert.equal(r.valid, true);
  });

  it("rejects published=true without feishu_url", () => {
    const r = validatePublishResult(validPublishJson({
      published: true,
      feishu_url: null,
    }));
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("feishu_url")));
  });

  it("rejects invalid feishu_url", () => {
    const r = validatePublishResult(validPublishJson({ feishu_url: "not-a-url" }));
    assert.equal(r.valid, false);
  });

  it("rejects negative images_expected", () => {
    const r = validatePublishResult(validPublishJson({ images_expected: -1 }));
    assert.equal(r.valid, false);
  });

  it("rejects images_uploaded > images_expected", () => {
    const r = validatePublishResult(validPublishJson({ images_uploaded: 5 }));
    assert.equal(r.valid, false);
  });

  it("rejects status=success when images_uploaded < images_expected", () => {
    const r = validatePublishResult(validPublishJson({
      images_expected: 3,
      images_uploaded: 2,
      status: "success",
    }));
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("status")));
  });

  it("allows status=partial when images_uploaded < images_expected", () => {
    const r = validatePublishResult(validPublishJson({
      images_expected: 3,
      images_uploaded: 2,
      status: "partial",
    }));
    assert.equal(r.valid, true);
  });

  it("rejects non-array image_failures", () => {
    const r = validatePublishResult(validPublishJson({ image_failures: "not-array" }));
    assert.equal(r.valid, false);
  });

  it("validates image_failures items", () => {
    const r = validatePublishResult(validPublishJson({
      image_failures: [{ item_id: "", image_url: null, reason: "" }],
    }));
    assert.equal(r.valid, false);
  });

  it("accepts valid image_failures", () => {
    const r = validatePublishResult(validPublishJson({
      image_failures: [{ item_id: "prod1", image_url: null, reason: "404" }],
      images_expected: 3,
      images_uploaded: 2,
      status: "partial",
    }));
    assert.equal(r.valid, true);
  });

  it("accepts whitespace around JSON (trailing newline is ok)", () => {
    const r = validatePublishResult("  " + validPublishJson() + "  ");
    assert.equal(r.valid, true);
  });

  it("rejects leading/trailing explanatory text", () => {
    const r = validatePublishResult("OK," + validPublishJson());
    // JSON.parse fails on leading non-whitespace
    assert.equal(r.valid, false);
  });
});

// ──────────────────────────────────────────────
// validateSessionsSend smoke test (v1.1 baseline)
// ──────────────────────────────────────────────
describe("validateSessionsSend (v1.1 baseline)", () => {
  it("rejects non-applicable agent", () => {
    const r = validateSessionsSend({ agentId: "main", params: {} });
    assert.equal(r.applicable, false);
    assert.equal(r.valid, true);
  });

  it("rejects Markdown fences in message", () => {
    const r = validateSessionsSend({
      agentId: "cpis-info-collector",
      params: {
        sessionKey: "agent:cpis-product-analyst:main",
        message: "```json\n{}```",
      },
    });
    assert.equal(r.valid, false);
    assert.ok(r.errors.some(e => e.includes("fence") || e.includes("Fence")));
  });
});
