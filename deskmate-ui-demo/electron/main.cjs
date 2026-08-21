const { app, BrowserWindow, globalShortcut, ipcMain, clipboard, session } = require("electron");
const path = require("path");
const { fileURLToPath } = require("url");
const { spawn } = require("child_process");
const { normalizeShortcut } = require("./shortcut.cjs");

const DEFAULT_SHORTCUT = "Ctrl+Shift+Space";
const DEFAULT_DEV_URL = "http://localhost:5173";
const APP_ROOT = path.resolve(__dirname, "..", "dist", "client");
const FOREGROUND_SCRIPT = "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class DeskMateForeground { [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow(); }'; [DeskMateForeground]::GetForegroundWindow().ToInt64()";
const PASTE_SCRIPT = "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')";

let mainWindow;
let shortcut = DEFAULT_SHORTCUT;
let voiceSessionRecording = false;
let voiceTargetWindow = null;

function getDevUrl() {
  const candidate = process.env.DESKMATE_DEV_URL || DEFAULT_DEV_URL;
  try {
    const url = new URL(candidate);
    if (url.protocol !== "http:" || !["localhost", "127.0.0.1"].includes(url.hostname)) return DEFAULT_DEV_URL;
    return url.href;
  } catch {
    return DEFAULT_DEV_URL;
  }
}

function isAllowedAppUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    if (process.argv.includes("--dev")) return url.origin === new URL(getDevUrl()).origin;
    if (url.protocol !== "file:") return false;
    const resolved = path.resolve(fileURLToPath(url));
    return resolved === path.join(APP_ROOT, "index.html") || resolved.startsWith(`${APP_ROOT}${path.sep}`);
  } catch {
    return false;
  }
}

function assertTrustedSender(event) {
  const senderUrl = event.senderFrame?.url || event.sender?.getURL?.() || "";
  if (!isAllowedAppUrl(senderUrl)) throw new Error("拒绝非 DeskMate 页面调用桌面能力");
}

function handleTrusted(channel, handler) {
  ipcMain.handle(channel, (event, ...args) => {
    assertTrustedSender(event);
    return handler(...args);
  });
}

function runPowershell(script, timeoutMs = 3000) {
  return new Promise((resolve) => {
    const child = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { windowsHide: true });
    let stdout = "";
    let stderr = "";
    const timeout = setTimeout(() => {
      child.kill();
      resolve({ ok: false, reason: "powershell-timeout" });
    }, timeoutMs);
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.once("error", (error) => {
      clearTimeout(timeout);
      resolve({ ok: false, reason: error.message });
    });
    child.once("exit", (code) => {
      clearTimeout(timeout);
      resolve(code === 0 ? { ok: true, value: stdout.trim() } : { ok: false, reason: stderr.trim() || `powershell-exit-${code}` });
    });
  });
}

async function getForegroundWindowId() {
  const result = await runPowershell(FOREGROUND_SCRIPT);
  return result.ok && /^\d+$/.test(result.value) ? result.value : null;
}

async function emitVoiceToggle(activeShortcut) {
  const phase = voiceSessionRecording ? "stop" : "start";
  if (phase === "start") voiceTargetWindow = await getForegroundWindowId();
  voiceSessionRecording = phase === "start";
  const payload = { source: "global-shortcut", shortcut: activeShortcut, phase, targetCaptured: Boolean(voiceTargetWindow), at: new Date().toISOString() };
  mainWindow?.webContents.send("key-diagnostic", { source: "global-shortcut", key: activeShortcut.split("+").at(-1), code: activeShortcut.split("+").at(-1), shortcut: activeShortcut, at: payload.at });
  mainWindow?.webContents.send("voice-toggle", payload);
}

function registerShortcut(nextShortcut = shortcut) {
  let candidate;
  try {
    candidate = normalizeShortcut(nextShortcut || DEFAULT_SHORTCUT);
  } catch (error) {
    return { registered: globalShortcut.isRegistered(shortcut), shortcut, reason: error.message };
  }
  if (candidate === shortcut && globalShortcut.isRegistered(shortcut)) return { registered: true, shortcut };
  let registered = false;
  try {
    registered = globalShortcut.register(candidate, () => { void emitVoiceToggle(candidate); });
  } catch (error) {
    return { registered: globalShortcut.isRegistered(shortcut), shortcut, reason: error.message };
  }
  if (!registered) return { registered: globalShortcut.isRegistered(shortcut), shortcut, reason: "shortcut-unavailable" };
  const previous = shortcut;
  shortcut = candidate;
  if (previous !== candidate) globalShortcut.unregister(previous);
  return { registered: true, shortcut };
}

async function pasteIntoCapturedWindow(text) {
  const value = String(text || "");
  if (!value || value.length > 100000) return { ok: false, reason: "invalid-text" };
  if (!voiceTargetWindow) return { ok: false, reason: "no-captured-target" };
  const currentWindow = await getForegroundWindowId();
  if (!currentWindow || currentWindow !== voiceTargetWindow) return { ok: false, reason: "target-window-changed" };
  clipboard.writeText(value);
  const result = await runPowershell(PASTE_SCRIPT);
  if (result.ok) voiceTargetWindow = null;
  return result.ok ? { ok: true, mode: "active-window" } : result;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 1024,
    minWidth: 960,
    minHeight: 680,
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), nodeIntegration: false, contextIsolation: true, sandbox: true },
  });
  if (process.argv.includes("--dev")) mainWindow.loadURL(getDevUrl());
  else mainWindow.loadFile(path.join(APP_ROOT, "index.html"));
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-navigate", (event, url) => { if (!isAllowedAppUrl(url)) event.preventDefault(); });
  mainWindow.webContents.on("before-input-event", (_event, input) => {
    if (input.type !== "keyDown") return;
    mainWindow.webContents.send("key-diagnostic", { key: input.key, code: input.code, control: input.control, shift: input.shift, alt: input.alt, meta: input.meta, at: new Date().toISOString() });
  });
  mainWindow.on("closed", () => { mainWindow = null; });
}

app.whenReady().then(() => {
  createWindow();
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => callback(permission === "media" && isAllowedAppUrl(webContents.getURL())));
  handleTrusted("desktop:get-capabilities", () => ({ supported: true, platform: process.platform, shortcut, shortcutRegistered: globalShortcut.isRegistered(shortcut) }));
  handleTrusted("desktop:register-shortcut", (value) => registerShortcut(value));
  handleTrusted("desktop:set-voice-recording", (recording) => {
    voiceSessionRecording = Boolean(recording);
    return { ok: true, recording: voiceSessionRecording };
  });
  handleTrusted("desktop:clipboard-write", (value) => {
    const text = String(value || "");
    if (text.length > 100000) return { ok: false, reason: "text-too-long" };
    clipboard.writeText(text);
    return { ok: true, mode: "clipboard" };
  });
  handleTrusted("desktop:paste-active-window", (text) => pasteIntoCapturedWindow(text));
  handleTrusted("desktop:key-diagnostic", (value) => ({ ok: true, event: value }));
  registerShortcut(DEFAULT_SHORTCUT);
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
