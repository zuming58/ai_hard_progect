import test from "node:test";
import assert from "node:assert/strict";
import { defaultState, migrateState, validateConfig } from "../src/store/appStore.js";
import { AI_EVENT_TYPES, AgentStatusAdapter } from "../src/adapters/index.js";

test("migrates legacy storage to current schema without dropping defaults", () => {
  const result = migrateState({ schemaVersion: 0, hotwords: ["旧词"], rules: [] });
  assert.equal(result.schemaVersion, 1);
  assert.deepEqual(result.vocabulary.hotwords, ["旧词"]);
  assert.equal(result.settings.theme, defaultState.settings.theme);
  assert.equal(result.keymap.length, 8);
});

test("rejects malformed imported configurations", () => {
  assert.throws(() => validateConfig({ keymap: ["only-one"] }), /8 项/);
  assert.throws(() => validateConfig({ schemaVersion: "1" }), /数字/);
  assert.throws(() => validateConfig(null), /JSON 对象/);
});

test("agent adapter emits only supported events and maps status payload", () => {
  const adapter = new AgentStatusAdapter();
  const received = [];
  adapter.subscribe((event) => received.push(event));
  adapter.setStatus({ type: "waiting_user", agent: "Codex", progress: 68, detail: "等待用户确认" });
  assert.deepEqual(received.at(-1), { type: "waiting_user", agent: "Codex", progress: 68, detail: "等待用户确认" });
  assert.deepEqual(AI_EVENT_TYPES, ["idle", "listening", "thinking", "working", "waiting_user", "completed", "error"]);
  assert.throws(() => adapter.setStatus({ type: "unknown" }), /未知 AI 状态/);
});
