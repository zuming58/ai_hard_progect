const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("overlayBridge", {
  onState: (listener) => {
    const handler = (_event, payload) => listener(payload);
    ipcRenderer.on("voice-state", handler);
    return () => ipcRenderer.removeListener("voice-state", handler);
  },
});

window.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("root");
  const labels = { recording: "正在录音", transcribing: "正在转写", outputting: "正在输出", completed: "语音输入完成", error: "语音输入失败", cancelled: "已取消" };
  const render = (value = {}) => {
    const state = value.state || "idle";
    const seconds = Math.max(0, Number(value.seconds) || 0);
    const time = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
    root.innerHTML = `<div class="shell ${state}"><div class="orb"></div><div class="copy"><strong>${labels[state] || "DeskMate"}</strong><p>${String(value.message || "电脑麦克风 · EasyInput 触发").replace(/[<>&]/g, "")}</p></div><div class="meter">${state === "recording" ? time : `${Math.round(Number(value.level) || 0)}%`}</div></div>`;
  };
  ipcRenderer.on("voice-state", (_event, value) => render(value));
});
