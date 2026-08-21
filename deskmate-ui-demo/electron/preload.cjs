const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopBridge", {
  getCapabilities: () => ipcRenderer.invoke("desktop:get-capabilities"),
  registerShortcut: (shortcut) => ipcRenderer.invoke("desktop:register-shortcut", shortcut),
  setVoiceRecording: (recording) => ipcRenderer.invoke("desktop:set-voice-recording", Boolean(recording)),
  writeClipboard: (text) => ipcRenderer.invoke("desktop:clipboard-write", text),
  pasteActiveWindow: (text) => ipcRenderer.invoke("desktop:paste-active-window", text),
  keyDiagnostic: (event) => ipcRenderer.invoke("desktop:key-diagnostic", event),
  onVoiceToggle: (listener) => { const handler = (_event, payload) => listener(payload); ipcRenderer.on("voice-toggle", handler); return () => ipcRenderer.removeListener("voice-toggle", handler); },
  onKeyDiagnostic: (listener) => { const handler = (_event, payload) => listener(payload); ipcRenderer.on("key-diagnostic", handler); return () => ipcRenderer.removeListener("key-diagnostic", handler); },
});
