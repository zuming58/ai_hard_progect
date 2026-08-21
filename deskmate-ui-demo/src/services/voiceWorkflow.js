export class VoiceWorkflow {
  constructor({ recorder, stt, organizer, output, saveHistory, debounceMs = 350 }) {
    Object.assign(this, { recorder, stt, organizer, output, saveHistory, debounceMs });
    this.state = "idle"; this.lastToggle = 0;
  }
  async toggle(now = Date.now()) {
    if (now - this.lastToggle < this.debounceMs) return { ignored: true, state: this.state };
    this.lastToggle = now;
    if (this.state === "recording") { this.state = "processing"; const recording = await this.recorder.stop(); return this.complete(recording); }
    if (this.state !== "idle" && this.state !== "completed" && this.state !== "error") return { ignored: true, state: this.state };
    try { await this.recorder.start(); this.state = "recording"; return { state: this.state }; } catch (error) { this.state = "error"; return { state: this.state, error }; }
  }
  async complete(recording) {
    let result;
    try { result = await this.stt.transcribe(recording?.blob); } catch (error) { result = { status: "error", text: "", error }; }
    const text = result.status === "success" ? await this.organizer.organize(result.text) : "录音完成，等待转写服务";
    const history = await this.saveHistory({ ...recording, text, transcriptStatus: result.status });
    let output = { ok: true, mode: "history" };
    if (result.status === "success") output = await this.output.output(text, recording?.outputMode || "history").catch((error) => ({ ok: false, error }));
    this.state = "completed";
    return { state: this.state, history, output, transcript: result };
  }
  deviceDisconnected() { if (this.state === "recording") return this.toggle(this.lastToggle + this.debounceMs + 1); return Promise.resolve({ ignored: true, state: this.state }); }
}
