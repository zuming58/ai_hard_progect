export const AI_EVENT_TYPES = ["idle", "listening", "thinking", "working", "waiting_user", "completed", "error"];

export class SpeechToTextAdapter { async transcribe() { return { text: "", status: "pending" }; } }
export class DeviceAdapter { async listInputDevices() { return []; } async getStatus() { return { connected: false, source: "mock" }; } }
export class AgentStatusAdapter {
  constructor() { this.listeners = new Set(); this.event = { type: "working", agent: "Codex", progress: 68, detail: "正在整理桌宠开发文档" }; }
  subscribe(listener) { this.listeners.add(listener); listener(this.event); return () => this.listeners.delete(listener); }
  setStatus(event) { if (!AI_EVENT_TYPES.includes(event.type)) throw new Error("未知 AI 状态"); this.event = event; this.listeners.forEach((listener) => listener(event)); }
}
export class DesktopBridge { async openFloatingWindow() { return { supported: false }; } async registerShortcut() { return { supported: false }; } }

export const mockAdapters = { speechToText: new SpeechToTextAdapter(), device: new DeviceAdapter(), agentStatus: new AgentStatusAdapter(), desktop: new DesktopBridge() };
