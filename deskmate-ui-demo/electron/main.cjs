const { app, BrowserWindow, globalShortcut, ipcMain, clipboard, session, safeStorage, Tray, Menu, nativeImage, screen } = require("electron");
const path = require("path");
const { fileURLToPath } = require("url");
const { spawn } = require("child_process");
const fs = require("fs");
const { normalizeShortcut } = require("./shortcut.cjs");
const { InputBridgeManager } = require("./input-bridge.cjs");
const { transcribe: transcribeBailian } = require("./bailian.cjs");
const { createSecureBailianStore } = require("./secure-bailian.cjs");

const DEFAULT_SHORTCUT = "Ctrl+Shift+Space";
const DEFAULT_DEV_URL = "http://localhost:5173";
const APP_ROOT = path.resolve(__dirname, "..", "dist", "client");
const FOREGROUND_SCRIPT = "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class DeskMateForeground { [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow(); }'; [DeskMateForeground]::GetForegroundWindow().ToInt64()";
const PASTE_SCRIPT = "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')";
const VOICE_STATES = new Set(["idle", "recording", "transcribing", "outputting", "completed", "error", "cancelled"]);

let mainWindow;
let overlayWindow;
let tray;
let inputBridge;
let shortcut = DEFAULT_SHORTCUT;
let voiceSessionRecording = false;
let voiceTargetWindow = null;
let bailianStore;
let isQuitting = false;
let lastVoiceState = { state: "idle", message: "准备就绪", seconds: 0, level: 0, floating: true };
const activeBailianRequests = new Map();
const smokeMode = process.argv.includes("--deskmate-smoke-test");
const bailianTestAudio = process.argv.find((value) => value.startsWith("--bailian-test-audio="))?.slice("--bailian-test-audio=".length) || "";
let smokeStage = 0;

if (smokeMode) {
  app.setPath("userData", path.join(app.getPath("temp"), `deskmate-smoke-${process.pid}`));
  app.commandLine.appendSwitch("use-fake-device-for-media-stream");
  app.commandLine.appendSwitch("use-fake-ui-for-media-stream");
}

function getInputBridgeExecutable() {
  const name = "DeskMate.InputBridge.exe";
  return app.isPackaged
    ? path.join(process.resourcesPath, "input-bridge", name)
    : path.join(__dirname, "..", "native", "DeskMate.InputBridge", "publish", name);
}

function trayIcon() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="#222c3a"/><rect x="6" y="8" width="20" height="16" rx="5" fill="#0e1622" stroke="#35c9ed"/><rect x="9" y="12" width="5" height="6" rx="2" fill="#35d7f4"/><rect x="18" y="12" width="5" height="6" rx="2" fill="#35d7f4"/><path d="M13 21h6" stroke="#35d7f4" stroke-width="1.5" stroke-linecap="round"/></svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`);
}

function getDevUrl() {
  const candidate = process.env.DESKMATE_DEV_URL || DEFAULT_DEV_URL;
  try {
    const url = new URL(candidate);
    if (url.protocol !== "http:" || !["localhost", "127.0.0.1"].includes(url.hostname)) return DEFAULT_DEV_URL;
    return url.href;
  } catch { return DEFAULT_DEV_URL; }
}

function isAllowedAppUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    if (process.argv.includes("--dev")) return url.origin === new URL(getDevUrl()).origin;
    if (url.protocol !== "file:") return false;
    const resolved = path.resolve(fileURLToPath(url));
    return resolved === path.join(APP_ROOT, "index.html") || resolved.startsWith(`${APP_ROOT}${path.sep}`);
  } catch { return false; }
}

function assertTrustedSender(event) {
  const senderUrl = event.senderFrame?.url || event.sender?.getURL?.() || "";
  if (!isAllowedAppUrl(senderUrl)) throw new Error("拒绝非 DeskMate 页面调用桌面能力");
}

function handleTrusted(channel, handler) {
  ipcMain.handle(channel, (event, ...args) => { assertTrustedSender(event); return handler(...args); });
}

function runPowershell(script, timeoutMs = 3000) {
  return new Promise((resolve) => {
    const child = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { windowsHide: true });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (value) => { if (settled) return; settled = true; clearTimeout(timeout); resolve(value); };
    const timeout = setTimeout(() => { child.kill(); finish({ ok: false, reason: "powershell-timeout" }); }, timeoutMs);
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.once("error", (error) => finish({ ok: false, reason: error.message }));
    child.once("exit", (code) => finish(code === 0 ? { ok: true, value: stdout.trim() } : { ok: false, reason: stderr.trim() || `powershell-exit-${code}` }));
  });
}

async function getForegroundWindowId() {
  const result = await runPowershell(FOREGROUND_SCRIPT);
  return result.ok && /^\d+$/.test(result.value) ? result.value : null;
}

function sendToMain(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send(channel, payload);
}

async function emitVoiceToggle(source = "global-shortcut", label = shortcut) {
  const phase = voiceSessionRecording ? "stop" : "start";
  if (phase === "start") voiceTargetWindow = await getForegroundWindowId();
  voiceSessionRecording = phase === "start";
  const at = new Date().toISOString();
  const payload = { source, shortcut: label, phase, targetCaptured: Boolean(voiceTargetWindow), at };
  sendToMain("key-diagnostic", { source, key: label, action: "release", at });
  sendToMain("voice-toggle", payload);
  return payload;
}

function emitVoiceCancel(source = "keyboard") {
  voiceSessionRecording = false;
  sendToMain("voice-cancel", { source, at: new Date().toISOString() });
}

function registerShortcut(nextShortcut = shortcut) {
  let candidate;
  try { candidate = normalizeShortcut(nextShortcut || DEFAULT_SHORTCUT); }
  catch (error) { return { registered: globalShortcut.isRegistered(shortcut), shortcut, reason: error.message }; }
  if (candidate === shortcut && globalShortcut.isRegistered(shortcut)) return { registered: true, shortcut };
  let registered = false;
  try { registered = globalShortcut.register(candidate, () => { void emitVoiceToggle("fallback-shortcut", candidate); }); }
  catch (error) { return { registered: globalShortcut.isRegistered(shortcut), shortcut, reason: error.message }; }
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

function createOverlayWindow() {
  overlayWindow = new BrowserWindow({
    width: 360,
    height: 104,
    frame: false,
    transparent: true,
    resizable: false,
    show: false,
    focusable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: { preload: path.join(__dirname, "overlay-preload.cjs"), nodeIntegration: false, contextIsolation: true, sandbox: true },
  });
  overlayWindow.setAlwaysOnTop(true, "floating");
  overlayWindow.setIgnoreMouseEvents(true);
  const html = "<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\"><style>html,body{margin:0;background:transparent;font-family:'Segoe UI','Microsoft YaHei',sans-serif;color:#eaf6ff}.shell{box-sizing:border-box;height:92px;margin:6px;padding:15px 18px;border:1px solid rgba(75,207,239,.55);border-radius:22px;background:rgba(24,33,46,.94);box-shadow:0 14px 35px rgba(13,28,46,.28);display:flex;align-items:center;gap:14px}.orb{width:44px;height:44px;border-radius:15px;background:linear-gradient(145deg,#287df5,#32d1e9);box-shadow:0 0 24px rgba(49,208,234,.38);display:grid;place-items:center}.orb:after{content:'';width:16px;height:16px;border:3px solid white;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite}.completed .orb:after{content:'✓';border:0;animation:none;font-size:24px}.error .orb{background:linear-gradient(145deg,#df5858,#fa976c)}.error .orb:after{content:'!';border:0;animation:none;font-size:24px}.cancelled .orb:after{content:'×';border:0;animation:none;font-size:26px}.copy{min-width:0;flex:1}.copy strong{font-size:16px}.copy p{margin:5px 0 0;color:#aebccc;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meter{width:58px;text-align:right;color:#56d8ef;font-variant-numeric:tabular-nums}@keyframes spin{to{transform:rotate(360deg)}}</style></head><body><div id='root'></div></body></html>";
  overlayWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

function positionAndShowOverlay() {
  if (!overlayWindow || overlayWindow.isDestroyed()) return;
  const area = screen.getPrimaryDisplay().workArea;
  const [width, height] = overlayWindow.getSize();
  overlayWindow.setPosition(area.x + area.width - width - 24, area.y + area.height - height - 24, false);
  overlayWindow.showInactive();
}

function updateVoiceState(value = {}) {
  const state = VOICE_STATES.has(value.state) ? value.state : "error";
  lastVoiceState = {
    state,
    message: String(value.message || "").slice(0, 240),
    seconds: Math.max(0, Math.min(36000, Number(value.seconds) || 0)),
    level: Math.max(0, Math.min(100, Number(value.level) || 0)),
    floating: value.floating !== false,
  };
  voiceSessionRecording = state === "recording";
  overlayWindow?.webContents.send("voice-state", lastVoiceState);
  if (!lastVoiceState.floating || ["idle"].includes(state)) overlayWindow?.hide();
  else {
    positionAndShowOverlay();
    if (["completed", "error", "cancelled"].includes(state)) setTimeout(() => { if (lastVoiceState.state === state) overlayWindow?.hide(); }, 1800);
  }
  refreshTrayMenu();
  return { ok: true, state };
}

function showMain(route) {
  if (!mainWindow) createWindow();
  mainWindow.show();
  mainWindow.restore();
  if (route) sendToMain("desktop-navigate", { route });
}

function refreshTrayMenu() {
  if (!tray) return;
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "打开 DeskMate", click: () => showMain() },
    { label: voiceSessionRecording ? "停止语音输入" : "开始语音输入", click: () => { void emitVoiceToggle("system-tray", "Tray"); } },
    { label: "设置与诊断", click: () => showMain("settings") },
    { type: "separator" },
    { label: "退出", click: () => { isQuitting = true; app.quit(); } },
  ]));
}

function createTray() {
  tray = new Tray(trayIcon());
  tray.setToolTip("DeskMate 语音输入");
  tray.on("double-click", () => showMain());
  refreshTrayMenu();
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
  mainWindow.webContents.on("did-finish-load", () => {
    sendToMain("input-bridge-status", inputBridge?.snapshot() || { available: false, process: "unsupported", boardConnected: false });
    if (smokeStage === 0) void runSmokeTest(); else if (smokeStage === 1) void finishSmokeTest();
  });
  mainWindow.on("close", (event) => {
    if (isQuitting || smokeMode) return;
    event.preventDefault();
    mainWindow.hide();
  });
  mainWindow.on("closed", () => { mainWindow = null; });
}

function startInputBridge() {
  if (process.platform !== "win32") return;
  const executable = getInputBridgeExecutable();
  if (!fs.existsSync(executable)) {
    sendToMain("input-bridge-status", { available: false, process: "missing", boardConnected: false, error: "input-bridge-not-built" });
    return;
  }
  inputBridge = new InputBridgeManager({ executable });
  inputBridge.on("status", (value) => sendToMain("input-bridge-status", value));
  inputBridge.on("diagnostic", (event) => sendToMain("key-diagnostic", event));
  inputBridge.on("trigger", (event) => { sendToMain("key-diagnostic", event); void emitVoiceToggle(event.source, event.key); });
  inputBridge.on("cancel", (event) => { sendToMain("key-diagnostic", event); emitVoiceCancel(event.source); });
  inputBridge.start();
}

async function runSmokeTest() {
  if (!smokeMode || smokeStage !== 0) return;
  smokeStage = 1;
  await mainWindow.webContents.executeJavaScript(`localStorage.setItem("deskmate.app-state", JSON.stringify({ schemaVersion: 4, settings: { keyDiagnosticsEnabled: true, simulatorEnabled: true, sttMode: "mock", outputMode: "clipboard", formatting: "raw" } })); location.hash = "/dashboard"; location.reload();`);
}

async function finishSmokeTest() {
  if (!smokeMode || smokeStage !== 1) return;
  smokeStage = 2;
  await new Promise((resolve) => setTimeout(resolve, 800));
  await emitVoiceToggle("smoke-test", shortcut);
  await new Promise((resolve) => setTimeout(resolve, 1200));
  await emitVoiceToggle("smoke-test", shortcut);
  await new Promise((resolve) => setTimeout(resolve, 2800));
  const report = await mainWindow.webContents.executeJavaScript(`(() => { const state = JSON.parse(localStorage.getItem("deskmate.app-state") || "{}"); return { historyText: state.history?.[0]?.text || "", route: location.hash }; })()`);
  report.clipboardText = clipboard.readText();
  report.ok = Boolean(report.historyText && report.clipboardText === report.historyText && report.route === "#/voice");
  const resultPath = process.env.DESKMATE_SMOKE_RESULT;
  if (resultPath && path.extname(resultPath).toLowerCase() === ".json") fs.writeFileSync(resultPath, JSON.stringify(report, null, 2));
  app.exit(report.ok ? 0 : 1);
}

async function runBailianConnectionTest(audioPath) {
  const resultPath = process.env.DESKMATE_BAILIAN_TEST_RESULT;
  const report = { ok: false };
  try {
    const resolved = path.resolve(audioPath);
    const extension = path.extname(resolved).toLowerCase();
    if (![".wav", ".webm"].includes(extension)) throw new Error("测试音频只允许 WAV 或 WebM");
    const audio = fs.readFileSync(resolved);
    const result = await transcribeBailian({ ...bailianStore.loadSecret(), audio, mimeType: extension === ".wav" ? "audio/wav" : "audio/webm" });
    Object.assign(report, { ok: true, characters: result.text.length, language: result.language, emotion: result.emotion, requestId: result.requestId });
  } catch (error) { report.error = String(error?.message || error || "unknown-error").replace(/sk-[A-Za-z0-9_-]+/g, "[REDACTED]"); }
  if (resultPath && path.extname(resultPath).toLowerCase() === ".json") fs.writeFileSync(resultPath, JSON.stringify(report, null, 2));
  app.exit(report.ok ? 0 : 1);
}

app.whenReady().then(async () => {
  bailianStore = createSecureBailianStore({ safeStorage, userDataPath: app.getPath("userData") });
  if (bailianTestAudio) { await runBailianConnectionTest(bailianTestAudio); return; }
  createWindow();
  createOverlayWindow();
  createTray();
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => callback(permission === "media" && isAllowedAppUrl(webContents.getURL())));
  handleTrusted("desktop:get-capabilities", () => ({ supported: true, platform: process.platform, shortcut, shortcutRegistered: globalShortcut.isRegistered(shortcut), inputBridge: inputBridge?.snapshot() || { available: false, process: process.platform === "win32" ? "missing" : "unsupported", boardConnected: false } }));
  handleTrusted("desktop:register-shortcut", (value) => registerShortcut(value));
  handleTrusted("desktop:set-trigger-config", (value) => ({ ok: true, config: inputBridge?.configure(value || {}) || { boardF22: true, rightAlt: false } }));
  handleTrusted("desktop:set-voice-recording", (recording) => { voiceSessionRecording = Boolean(recording); refreshTrayMenu(); return { ok: true, recording: voiceSessionRecording }; });
  handleTrusted("desktop:set-voice-state", (value) => updateVoiceState(value));
  handleTrusted("desktop:clipboard-write", (value) => { const text = String(value || ""); if (text.length > 100000) return { ok: false, reason: "text-too-long" }; clipboard.writeText(text); return { ok: true, mode: "clipboard" }; });
  handleTrusted("desktop:paste-active-window", (text) => pasteIntoCapturedWindow(text));
  handleTrusted("desktop:key-diagnostic", (value) => ({ ok: true, event: value }));
  handleTrusted("bailian:get-status", () => bailianStore.status());
  handleTrusted("bailian:save-credentials", (value) => bailianStore.save(value || {}));
  handleTrusted("bailian:clear-credentials", () => bailianStore.clear());
  handleTrusted("bailian:transcribe", async (value = {}) => {
    const secret = bailianStore.loadSecret();
    const audio = value.audio instanceof ArrayBuffer ? Buffer.from(value.audio) : Buffer.from(value.audio || []);
    const requestId = typeof value.requestId === "string" && /^[a-zA-Z0-9-]{8,80}$/.test(value.requestId) ? value.requestId : `asr-${Date.now()}`;
    const controller = new AbortController();
    activeBailianRequests.set(requestId, controller);
    try { return await transcribeBailian({ ...secret, audio, mimeType: value.mimeType, signal: controller.signal }); }
    finally { activeBailianRequests.delete(requestId); }
  });
  handleTrusted("bailian:cancel", (requestId) => { const controller = activeBailianRequests.get(String(requestId || "")); if (!controller) return { ok: false, reason: "request-not-active" }; controller.abort(); return { ok: true }; });
  registerShortcut(DEFAULT_SHORTCUT);
  startInputBridge();
  app.on("activate", () => showMain());
});

app.on("before-quit", () => { isQuitting = true; inputBridge?.stop(); activeBailianRequests.forEach((controller) => controller.abort()); activeBailianRequests.clear(); });
app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => { if (process.platform === "darwin" && !isQuitting) return; });
