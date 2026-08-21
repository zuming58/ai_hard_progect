const { app, BrowserWindow, globalShortcut, ipcMain, clipboard } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const DEFAULT_SHORTCUT = "Ctrl+Shift+Space";
let mainWindow;
let shortcut = DEFAULT_SHORTCUT;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 1024,
    minWidth: 960,
    minHeight: 680,
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), nodeIntegration: false, contextIsolation: true, sandbox: true },
  });
  const devUrl = process.env.DESKMATE_DEV_URL || "http://localhost:5173";
  if (process.argv.includes("--dev")) mainWindow.loadURL(devUrl);
  else mainWindow.loadFile(path.join(__dirname, "..", "dist", "client", "index.html"));
  mainWindow.webContents.on("before-input-event", (_event, input) => {
    if (input.type !== "keyDown") return;
    mainWindow.webContents.send("key-diagnostic", { key: input.key, code: input.code, control: input.control, shift: input.shift, alt: input.alt, meta: input.meta, at: new Date().toISOString() });
  });
  mainWindow.on("closed", () => { mainWindow = null; });
}

function registerShortcut(nextShortcut = shortcut) {
  globalShortcut.unregisterAll();
  shortcut = nextShortcut || DEFAULT_SHORTCUT;
  const registered = globalShortcut.register(shortcut, () => {
    const at = new Date().toISOString();
    mainWindow?.webContents.send("key-diagnostic", { source: "global-shortcut", key: "Space", code: "Space", control: true, shift: true, alt: false, meta: false, shortcut, at });
    mainWindow?.webContents.send("voice-toggle", { source: "global-shortcut", shortcut, at });
  });
  return { registered, shortcut };
}

app.whenReady().then(() => {
  createWindow();
  ipcMain.handle("desktop:get-capabilities", () => ({ supported: true, platform: process.platform, shortcut }));
  ipcMain.handle("desktop:register-shortcut", (_event, value) => registerShortcut(value));
  ipcMain.handle("desktop:clipboard-write", (_event, value) => { clipboard.writeText(String(value || "")); return { ok: true }; });
  ipcMain.handle("desktop:paste-active-window", (_event, text) => new Promise((resolve) => {
    clipboard.writeText(String(text || ""));
    const child = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')"], { windowsHide: true });
    child.once("error", (error) => resolve({ ok: false, reason: error.message }));
    child.once("exit", (code) => resolve(code === 0 ? { ok: true } : { ok: false, reason: `paste-exit-${code}` }));
  }));
  ipcMain.handle("desktop:key-diagnostic", (_event, value) => ({ ok: true, event: value }));
  registerShortcut();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
