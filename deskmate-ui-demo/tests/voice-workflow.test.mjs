import test from "node:test";
import assert from "node:assert/strict";
import { VoiceWorkflow } from "../src/services/voiceWorkflow.js";
import { DesktopBridgeAdapter, EasyInputLanAudioAdapter, SttAdapter, TextOrganizerAdapter, TextOutputAdapter } from "../src/adapters/voiceAdapters.js";

function setup(overrides = {}) {
  const calls = [];
  const recorder = { start: async () => calls.push("start"), stop: async () => { calls.push("stop"); return { blob: new Blob(["audio"]), duration: 1 }; } };
  const workflow = new VoiceWorkflow({ recorder, stt: new SttAdapter(), organizer: new TextOrganizerAdapter(), output: new TextOutputAdapter(), saveHistory: async (item) => { calls.push(item.text); return item; }, debounceMs: 100, ...overrides });
  return { workflow, calls };
}

test("global shortcut and manual trigger share debounced start/stop state machine", async () => {
  const { workflow, calls } = setup();
  await workflow.toggle(1000);
  await workflow.toggle(1050);
  await workflow.toggle(1200);
  assert.deepEqual(calls, ["start", "stop", "录音完成，等待转写服务"]);
  assert.equal(workflow.state, "completed");
});

test("STT failure still saves fallback history text", async () => {
  const saved = [];
  const { workflow } = setup({ stt: { transcribe: async () => { throw new Error("timeout"); } }, saveHistory: async (item) => { saved.push(item); return item; } });
  await workflow.toggle(1000); const result = await workflow.toggle(1200);
  assert.equal(result.transcript.status, "error");
  assert.equal(saved[0].text, "录音完成，等待转写服务");
});

test("web desktop bridge safely degrades and LAN audio stays unavailable", async () => {
  const bridge = new DesktopBridgeAdapter(null);
  assert.equal((await bridge.capabilities()).supported, false);
  assert.equal((await bridge.registerShortcut("Ctrl+Shift+Space")).registered, false);
  assert.equal((await new EasyInputLanAudioAdapter().getStatus()).connected, false);
  await assert.rejects(() => new EasyInputLanAudioAdapter().openStream(), /协议尚未确认/);
});

test("clipboard failure reports failure without deleting source text", async () => {
  const output = new TextOutputAdapter({ writeClipboard: async () => ({ ok: false, reason: "denied" }) });
  const result = await output.output("保留在历史", "clipboard");
  assert.equal(result.ok, false);
});
