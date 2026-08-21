import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const require = createRequire(import.meta.url);
const { buildRequest, endpointForWorkspace, parseResponse, transcribe, validateApiKey } = require("../electron/bailian.cjs");
const { createSecureBailianStore } = require("../electron/secure-bailian.cjs");

test("Bailian request uses base64 audio without exposing key in the body", () => {
  const request = buildRequest(Buffer.from("audio"), { mimeType: "audio/webm" });
  assert.equal(request.model, "qwen3-asr-flash");
  assert.match(request.messages[0].content[0].input_audio.data, /^data:audio\/webm;base64,/);
  assert.doesNotMatch(JSON.stringify(request), /sk-/);
});

test("Bailian validates keys and workspace endpoints", () => {
  assert.equal(validateApiKey("sk-12345678"), "sk-12345678");
  assert.throws(() => validateApiKey("secret"), /格式/);
  assert.equal(endpointForWorkspace("workspace-123"), "https://workspace-123.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions");
  assert.match(endpointForWorkspace(""), /dashscope\.aliyuncs\.com/);
});

test("Bailian parses text and sends authorization only as a header", async () => {
  let captured;
  const value = await transcribe({ apiKey: "sk-12345678", audio: Buffer.from("audio"), fetchImpl: async (url, options) => { captured = { url, options }; return { ok: true, json: async () => ({ id: "req", choices: [{ message: { content: "识别成功", annotations: [{ language: "zh", emotion: "neutral" }] } }] }) }; } });
  assert.equal(value.text, "识别成功");
  assert.equal(value.language, "zh");
  assert.equal(captured.options.headers.Authorization, "Bearer sk-12345678");
  assert.doesNotMatch(captured.options.body, /sk-12345678/);
  assert.equal(parseResponse({ choices: [{ message: { content: " 文本 " } }] }).text, "文本");
});

test("Bailian credentials are encrypted at rest and status never returns the key", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "deskmate-bailian-"));
  const safeStorage = { isEncryptionAvailable: () => true, encryptString: (value) => Buffer.from(`encrypted:${value}`), decryptString: (value) => value.toString().replace(/^encrypted:/, "") };
  try {
    const store = createSecureBailianStore({ safeStorage, userDataPath: directory });
    const status = store.save({ apiKey: "sk-12345678", workspaceId: "workspace-123" });
    assert.equal(status.configured, true);
    assert.equal("apiKey" in status, false);
    const disk = fs.readFileSync(path.join(directory, "bailian-credentials.json"), "utf8");
    assert.doesNotMatch(disk, /sk-12345678/);
    assert.equal(store.loadSecret().apiKey, "sk-12345678");
    assert.equal(store.clear().configured, false);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
