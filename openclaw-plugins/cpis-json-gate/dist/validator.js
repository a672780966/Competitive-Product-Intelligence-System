const ROUTES = Object.freeze({
  "cpis-info-collector": Object.freeze({ sessionKey: "agent:cpis-product-analyst:main", toAgent: "cpis-product-analyst", payloadType: "evidence_batch" }),
  "cpis-product-analyst": Object.freeze({ sessionKey: "agent:cpis-knowledge-curator:main", toAgent: "cpis-knowledge-curator", payloadType: "product_analysis_batch" }),
});
const RUN_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$/;
const ALLOWED_STATUS = new Set(["success", "partial", "changed", "no_change", "insufficient_data"]);
const ALLOWED_PUBLISH_STATUS = new Set(["success", "partial", "failed"]);
const isObject = value => value !== null && typeof value === "object" && !Array.isArray(value);
const isNonEmptyString = value => typeof value === "string" && value.trim().length > 0;
function isHttpUrl(value) { if (!isNonEmptyString(value)) return false; try { const url = new URL(value); return url.protocol === "http:" || url.protocol === "https:"; } catch { return false; } }
function add(errors, condition, path, message) { if (!condition) errors.push(`${path}: ${message}`); }
function validateUrlArray(errors, value, path) { add(errors, Array.isArray(value), path, "must be an array"); if (Array.isArray(value)) value.forEach((url, i) => add(errors, isHttpUrl(url), `${path}[${i}]`, "must be an http/https URL")); }
function walkUrlFields(errors, value, path = "$", depth = 0) { if (depth > 12 || value === null) return; if (Array.isArray(value)) { value.forEach((entry, i) => walkUrlFields(errors, entry, `${path}[${i}]`, depth + 1)); return; } if (!isObject(value)) return; for (const [key, entry] of Object.entries(value)) { const p = `${path}.${key}`; if (["product_url","source_url","image_url","amazon_url","evidence_url"].includes(key) && entry !== null) add(errors, isHttpUrl(entry), p, "must be an http/https URL or null"); else if (["source_urls","evidence_urls","image_urls"].includes(key)) validateUrlArray(errors, entry, p); walkUrlFields(errors, entry, p, depth + 1); } }
function validateEnvelope(errors, data, agentId, route) { const allowed = new Set(["schema_version","object_type","run_id","from_agent","to_agent","payload_type","payload","sent_at"]); Object.keys(data).forEach(key => add(errors, allowed.has(key), `$.${key}`, "unexpected field")); add(errors, data.schema_version === "1.0", "$.schema_version", "must equal 1.0"); add(errors, data.object_type === "agent_handoff", "$.object_type", "must equal agent_handoff"); add(errors, isNonEmptyString(data.run_id) && RUN_ID_PATTERN.test(data.run_id), "$.run_id", "has invalid format"); add(errors, data.from_agent === agentId, "$.from_agent", `must equal ${agentId}`); add(errors, data.to_agent === route.toAgent, "$.to_agent", `must equal ${route.toAgent}`); add(errors, data.payload_type === route.payloadType, "$.payload_type", `must equal ${route.payloadType}`); add(errors, isObject(data.payload), "$.payload", "must be an object"); add(errors, isNonEmptyString(data.sent_at) && Number.isFinite(Date.parse(data.sent_at)), "$.sent_at", "must be a valid ISO 8601 date-time"); }
function validateEvidenceBatch(errors, payload, runId) {
  add(errors, payload.schema_version === "1.0", "$.payload.schema_version", "must equal 1.0"); add(errors, payload.object_type === "evidence_batch", "$.payload.object_type", "must equal evidence_batch"); add(errors, payload.run_id === runId, "$.payload.run_id", "must match envelope run_id"); add(errors, ALLOWED_STATUS.has(payload.status), "$.payload.status", "has unsupported value"); add(errors, isObject(payload.collection_scope), "$.payload.collection_scope", "must be an object"); add(errors, Array.isArray(payload.sources), "$.payload.sources", "must be an array"); add(errors, Array.isArray(payload.items), "$.payload.items", "must be an array"); add(errors, isObject(payload.collection_summary), "$.payload.collection_summary", "must be an object"); if (!Array.isArray(payload.sources) || !Array.isArray(payload.items)) return;
  const sourceIds = new Set(), sourcesById = new Map(); payload.sources.forEach((source, i) => { const p = `$.payload.sources[${i}]`; add(errors, isObject(source), p, "must be an object"); if (!isObject(source)) return; add(errors, isNonEmptyString(source.source_id), `${p}.source_id`, "is required"); if (isNonEmptyString(source.source_id)) { add(errors, !sourceIds.has(source.source_id), `${p}.source_id`, "must be unique"); sourceIds.add(source.source_id); sourcesById.set(source.source_id, source); } add(errors, isHttpUrl(source.source_url) || isHttpUrl(source.url), `${p}.source_url`, "source_url or url must contain an http/https evidence link"); });
  const itemIds = new Set(), asins = new Set(), productUrls = new Set(), rankingCounts = new Map(); const maxItems = payload.collection_scope?.max_items_per_ranking; add(errors, Number.isInteger(maxItems) && maxItems > 0 && maxItems <= 100, "$.payload.collection_scope.max_items_per_ranking", "must be an integer between 1 and 100");
  payload.items.forEach((item, i) => { const p = `$.payload.items[${i}]`; add(errors, isObject(item), p, "must be an object"); if (!isObject(item)) return; add(errors, isNonEmptyString(item.item_id), `${p}.item_id`, "is required"); if (isNonEmptyString(item.item_id)) { add(errors, !itemIds.has(item.item_id), `${p}.item_id`, "must be unique"); itemIds.add(item.item_id); } const refs=[]; if (isNonEmptyString(item.source_id)) refs.push(item.source_id); if (Array.isArray(item.source_ids)) refs.push(...item.source_ids); add(errors, refs.length > 0, `${p}.source_id`, "source_id or source_ids is required"); refs.forEach((id,j)=>{ add(errors,isNonEmptyString(id),`${p}.source_refs[${j}]`,"must be a string"); add(errors,sourceIds.has(id),`${p}.source_refs[${j}]`,`unknown source_id ${id}`); }); add(errors,isHttpUrl(item.product_url),`${p}.product_url`,"must be an http/https URL"); if(isHttpUrl(item.product_url)){add(errors,!productUrls.has(item.product_url),`${p}.product_url`,"must be unique");productUrls.add(item.product_url);} add(errors,"image_url" in item,`${p}.image_url`,"is required; use null when unavailable"); add(errors,item.image_url===null||isHttpUrl(item.image_url),`${p}.image_url`,"must be an http/https URL or null"); if(item.asin!==null){add(errors,/^[A-Z0-9]{10}$/.test(item.asin),`${p}.asin`,"must be a 10-character ASIN or null");if(typeof item.asin==="string"){add(errors,!asins.has(item.asin),`${p}.asin`,`duplicate ASIN ${item.asin}`);asins.add(item.asin);}} add(errors,item.ranking_type==="sales_rank"||item.ranking_type==="new_product_rank",`${p}.ranking_type`,"must be sales_rank or new_product_rank"); if(item.ranking_type==="sales_rank"||item.ranking_type==="new_product_rank") rankingCounts.set(item.ranking_type,(rankingCounts.get(item.ranking_type)||0)+1); add(errors,Number.isInteger(item.ranking_position)&&item.ranking_position>0,`${p}.ranking_position`,"must be a positive integer"); if(Number.isInteger(maxItems)) add(errors,Number.isInteger(item.ranking_position)&&item.ranking_position<=maxItems,`${p}.ranking_position`,`must not exceed max_items_per_ranking (${maxItems})`); add(errors,isNonEmptyString(item.ranking_source_id),`${p}.ranking_source_id`,"is required"); if(isNonEmptyString(item.ranking_source_id)){const source=sourcesById.get(item.ranking_source_id);add(errors,Boolean(source),`${p}.ranking_source_id`,"must reference a source");if(source){const expected=item.ranking_type==="sales_rank"?"amazon_best_sellers_rankings":"amazon_new_releases_rankings";add(errors,source.source_type===expected,`${p}.ranking_source_id`,`must reference source_type ${expected}, not search-result ordering`);}} });
  if(Number.isInteger(maxItems)) rankingCounts.forEach((count,type)=>add(errors,count<=maxItems,"$.payload.items",`${type} contains ${count} items; maximum is ${maxItems}`)); const warnings=payload.collection_summary?.warnings; if(Array.isArray(warnings)&&warnings.length>0) add(errors,payload.status==="partial","$.payload.status","must be partial when collection_summary.warnings is non-empty");
}
function validateAnalysisBatch(errors,payload,runId){add(errors,payload.schema_version==="1.0","$.payload.schema_version","must equal 1.0");add(errors,payload.object_type==="product_analysis_batch","$.payload.object_type","must equal product_analysis_batch");add(errors,payload.run_id===runId,"$.payload.run_id","must match envelope run_id");add(errors,ALLOWED_STATUS.has(payload.status),"$.payload.status","has unsupported value");add(errors,Array.isArray(payload.findings),"$.payload.findings","must be an array");add(errors,isObject(payload.analysis_summary),"$.payload.analysis_summary","must be an object");if(!Array.isArray(payload.findings))return;payload.findings.forEach((finding,i)=>{const p=`$.payload.findings[${i}]`;add(errors,isObject(finding),p,"must be an object");if(!isObject(finding))return;add(errors,isNonEmptyString(finding.claim),`${p}.claim`,"is required");add(errors,Array.isArray(finding.evidence_refs)&&finding.evidence_refs.length>0,`${p}.evidence_refs`,"must be a non-empty array");if("confidence" in finding)add(errors,typeof finding.confidence==="number"&&finding.confidence>=0&&finding.confidence<=1,`${p}.confidence`,"must be a number between 0 and 1");});}

// --- v1.2: validatePublishResult ---
const ALLOWED_PUBLISH_FIELDS = new Set([
  "schema_version", "object_type", "run_id", "agent_id",
  "status", "published", "message_zh", "message_en",
  "feishu_url", "images_expected", "images_uploaded", "image_failures"
]);

export function validatePublishResult(text) {
  const errors = [];
  add(errors, isNonEmptyString(text), "$text", "must be a non-empty string");
  if (!isNonEmptyString(text)) return { valid: false, errors };

  const trimmed = text.trim();
  add(errors, !trimmed.startsWith("```") && !trimmed.endsWith("```"), "$text", "Markdown fences are forbidden");
  // Also reject any backtick fence patterns
  add(errors, !/^```|```$/.test(trimmed), "$text", "Markdown code fences are forbidden");
  add(errors, !/\n```/.test(trimmed) && !/```\n/.test(trimmed), "$text", "Inline Markdown code fences are forbidden");

  if (errors.length) return { valid: false, errors };

  let data;
  try {
    data = JSON.parse(trimmed);
  } catch (e) {
    return { valid: false, errors: [`$: invalid JSON (${e.message})`] };
  }

  add(errors, isObject(data), "$", "must be a single JSON object");
  if (!isObject(data)) return { valid: false, errors };

  // 4. Check only allowed fields (no unknown fields)
  Object.keys(data).forEach(key => {
    add(errors, ALLOWED_PUBLISH_FIELDS.has(key), `$.${key}`, "unexpected field");
  });

  // 5. Schema version
  add(errors, data.schema_version === "1.0", "$.schema_version", "must equal 1.0");
  add(errors, data.object_type === "publish_result", "$.object_type", "must equal publish_result");
  add(errors, isNonEmptyString(data.run_id) && RUN_ID_PATTERN.test(data.run_id), "$.run_id", "has invalid format");
  add(errors, isNonEmptyString(data.agent_id), "$.agent_id", "is required");
  add(errors, ALLOWED_PUBLISH_STATUS.has(data.status), "$.status", "must be success, partial, or failed");

  // 6. published must be boolean
  add(errors, typeof data.published === "boolean", "$.published", "must be a boolean");

  // 7. message fields
  add(errors, isNonEmptyString(data.message_zh), "$.message_zh", "is required");
  add(errors, isNonEmptyString(data.message_en), "$.message_en", "is required");

  // 8. feishu_url: when published=true, must be a valid http/https URL
  if (data.published === true) {
    add(errors, isHttpUrl(data.feishu_url), "$.feishu_url", "is required and must be an http/https URL when published=true");
  } else {
    add(errors, data.feishu_url === null || data.feishu_url === undefined || isHttpUrl(data.feishu_url), "$.feishu_url", "should be null or an http/https URL");
  }

  // 9. images_expected and images_uploaded
  add(errors, Number.isInteger(data.images_expected) && data.images_expected >= 0, "$.images_expected", "must be a non-negative integer");
  add(errors, Number.isInteger(data.images_uploaded) && data.images_uploaded >= 0, "$.images_uploaded", "must be a non-negative integer");
  add(errors, data.images_uploaded <= data.images_expected, "$.images_uploaded", "must not exceed images_expected");

  // 10. images_uploaded < images_expected => status must NOT be success
  if (data.images_uploaded < data.images_expected) {
    add(errors, data.status !== "success", "$.status", "must not be success when images_uploaded < images_expected");
  }

  // 11. image_failures must be an array (allow empty)
  add(errors, Array.isArray(data.image_failures), "$.image_failures", "must be an array");
  if (Array.isArray(data.image_failures)) {
    data.image_failures.forEach((failure, i) => {
      const p = `$.image_failures[${i}]`;
      add(errors, isObject(failure), p, "each item must be an object");
      if (isObject(failure)) {
        add(errors, isNonEmptyString(failure.item_id), `${p}.item_id`, "is required");
        add(errors, failure.image_url === null || isHttpUrl(failure.image_url), `${p}.image_url`, "must be an http/https URL or null");
        add(errors, isNonEmptyString(failure.reason), `${p}.reason`, "is required");
      }
    });
  }

  return { valid: errors.length === 0, errors };
}

export function validateSessionsSend({agentId,params}){const route=ROUTES[agentId];if(!route)return{applicable:false,valid:true,errors:[]};const errors=[];add(errors,isObject(params),"$params","must be an object");if(!isObject(params))return{applicable:true,valid:false,errors};add(errors,params.sessionKey===route.sessionKey,"$params.sessionKey",`must equal ${route.sessionKey}`);add(errors,typeof params.message==="string","$params.message","must be a JSON string");if(typeof params.message!=="string")return{applicable:true,valid:false,errors};const message=params.message.trim();add(errors,message.length>0,"$params.message","must not be empty");add(errors,!message.startsWith("```")&&!message.endsWith("```"),"$params.message","Markdown fences are forbidden");if(errors.length)return{applicable:true,valid:false,errors};let data;try{data=JSON.parse(message);}catch(error){return{applicable:true,valid:false,errors:[`$params.message: invalid JSON (${error.message})`]};}add(errors,isObject(data),"$","must contain one JSON object");if(!isObject(data))return{applicable:true,valid:false,errors};validateEnvelope(errors,data,agentId,route);if(isObject(data.payload)){route.payloadType==="evidence_batch"?validateEvidenceBatch(errors,data.payload,data.run_id):validateAnalysisBatch(errors,data.payload,data.run_id);walkUrlFields(errors,data.payload,"$.payload");}return{applicable:true,valid:errors.length===0,errors,parsed:errors.length===0?data:undefined};}
export function formatBlockReason(errors){const visible=errors.slice(0,8).join("; ");const suffix=errors.length>8?`; and ${errors.length-8} more error(s)`:"";return `CPIS_JSON_GATE_BLOCKED: ${visible}${suffix}`;}
