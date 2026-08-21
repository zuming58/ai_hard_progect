import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useReducer } from "react";
import { expressionPresets, historyItems, keyActions } from "../appData.js";
import { AI_EVENT_TYPES } from "../adapters/index.js";

export const STORAGE_KEY = "deskmate.app-state";
export const SCHEMA_VERSION = 2;

export const defaultState = {
  schemaVersion: SCHEMA_VERSION,
  history: historyItems,
  vocabulary: { hotwords: ["DeskMate", "ESP32-S3", "Codex", "Claude Code", "Hermes"], rules: [{ from: "桌面宠物", to: "桌宠" }, { from: "克劳德代码", to: "Claude Code" }] },
  keymap: [...keyActions.slice(0, 8)],
  settings: { microphoneId: "", microphoneSource: "computer", formatting: "smart", theme: "system", floating: true, backgroundOpacity: 70, operation: "toggle", startupSound: true, voiceShortcut: "Ctrl+Shift+Space", outputMode: "history", activeWindowOutputEnabled: false, keyDiagnosticsEnabled: false },
  expressionMapping: { idle: "sleep", listening: "listen", thinking: "think", working: "focus", waiting_user: "listen", completed: "happy", error: "alert" },
  agentExpressionMapping: { codex: "focus", claude: "listen", hermes: "think", workbody: "happy" },
  currentExpression: "focus",
  expressionEditor: { eyeSize: 72, eyeGap: 58, brightness: 80, blink: true, color: "cyan" },
  motion: { preset: "attentive", speed: 45, range: 55 },
  sensors: { autoBrightness: true, faceTracking: false },
  aiEvent: { type: "working", agent: "Codex", progress: 68, detail: "正在整理桌宠开发文档" },
};

function mergeDefaults(value) {
  if (!value || typeof value !== "object") return structuredClone(defaultState);
  return {
    ...structuredClone(defaultState), ...value, schemaVersion: SCHEMA_VERSION,
    vocabulary: { ...defaultState.vocabulary, ...(value.vocabulary || {}) },
    settings: { ...defaultState.settings, ...(value.settings || {}) },
    expressionMapping: { ...defaultState.expressionMapping, ...(value.expressionMapping || {}) },
    agentExpressionMapping: { ...defaultState.agentExpressionMapping, ...(value.agentExpressionMapping || {}) },
    expressionEditor: { ...defaultState.expressionEditor, ...(value.expressionEditor || {}) },
    motion: { ...defaultState.motion, ...(value.motion || {}) },
    sensors: { ...defaultState.sensors, ...(value.sensors || {}) },
    aiEvent: { ...defaultState.aiEvent, ...(value.aiEvent || {}) },
  };
}

export function migrateState(raw) {
  if (!raw || typeof raw !== "object") return structuredClone(defaultState);
  if (raw.schemaVersion === 0) raw = { ...raw, vocabulary: { hotwords: raw.hotwords || [], rules: raw.rules || [] } };
  return mergeDefaults(raw);
}

export function loadState(storage = globalThis.localStorage) {
  try {
    const raw = JSON.parse(storage?.getItem(STORAGE_KEY) || "null");
    return raw ? validateConfig(raw) : structuredClone(defaultState);
  } catch {
    return structuredClone(defaultState);
  }
}

export function validateConfig(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("配置必须是 JSON 对象");
  if (value.schemaVersion !== undefined && (!Number.isInteger(value.schemaVersion) || value.schemaVersion < 0)) throw new Error("schemaVersion 必须是非负整数数字");
  if ((value.schemaVersion ?? 0) > SCHEMA_VERSION) throw new Error("配置来自更高版本，请先升级 DeskMate");
  if (value.history !== undefined && (!Array.isArray(value.history) || value.history.some((item) => !item || typeof item !== "object" || typeof item.text !== "string" || typeof item.time !== "string"))) throw new Error("历史记录格式无效");
  if (value.keymap !== undefined && (!Array.isArray(value.keymap) || value.keymap.length !== 8 || value.keymap.some((item) => typeof item !== "string"))) throw new Error("按键映射必须包含 8 项文字动作");
  if (value.vocabulary !== undefined && (!value.vocabulary || typeof value.vocabulary !== "object" || Array.isArray(value.vocabulary))) throw new Error("词库格式无效");
  if (value.vocabulary?.hotwords && (!Array.isArray(value.vocabulary.hotwords) || value.vocabulary.hotwords.some((item) => typeof item !== "string"))) throw new Error("热词格式无效");
  if (value.vocabulary?.rules && (!Array.isArray(value.vocabulary.rules) || value.vocabulary.rules.some((item) => !item || typeof item.from !== "string" || typeof item.to !== "string"))) throw new Error("替换规则格式无效");
  if (value.settings !== undefined && (!value.settings || typeof value.settings !== "object" || Array.isArray(value.settings))) throw new Error("设置格式无效");
  const expressionIds = new Set(expressionPresets.map((item) => item.id));
  const checkExpressionMap = (mapping, label) => {
    if (mapping === undefined) return;
    if (!mapping || typeof mapping !== "object" || Array.isArray(mapping) || Object.values(mapping).some((item) => !expressionIds.has(item))) throw new Error(`${label}格式无效`);
  };
  checkExpressionMap(value.expressionMapping, "状态表情映射");
  checkExpressionMap(value.agentExpressionMapping, "AI 工具表情映射");
  if (value.currentExpression !== undefined && !expressionIds.has(value.currentExpression)) throw new Error("当前表情不存在");
  if (value.aiEvent !== undefined && (!value.aiEvent || typeof value.aiEvent !== "object" || !AI_EVENT_TYPES.includes(value.aiEvent.type))) throw new Error("AI 状态事件格式无效");
  if (value.expressionEditor !== undefined && (!value.expressionEditor || typeof value.expressionEditor !== "object")) throw new Error("表情编辑参数格式无效");
  if (value.motion !== undefined && (!value.motion || typeof value.motion !== "object")) throw new Error("动作参数格式无效");
  if (value.sensors !== undefined && (!value.sensors || typeof value.sensors !== "object")) throw new Error("传感器设置格式无效");
  return migrateState(value);
}

function agentKey(value = "") {
  const normalized = value.toLowerCase().replace(/\s+/g, "");
  if (normalized.includes("claude")) return "claude";
  if (normalized.includes("hermes")) return "hermes";
  if (normalized.includes("workbody")) return "workbody";
  return "codex";
}

export function reduceAppState(state, action) {
  if (action.type === "reset") return structuredClone(defaultState);
  if (action.type === "replace") return action.value;
  if (action.type === "patch") return { ...state, ...action.value };
  if (action.type === "event") {
    const event = action.value;
    const agentExpression = event.type === "working" ? state.agentExpressionMapping[agentKey(event.agent)] : null;
    const expression = agentExpression || state.expressionMapping[event.type] || state.currentExpression;
    return { ...state, aiEvent: event, currentExpression: expression };
  }
  return state;
}

const AppStoreContext = createContext(null);
export function AppStoreProvider({ children }) {
  const [state, dispatch] = useReducer(reduceAppState, undefined, loadState);
  useEffect(() => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* storage can be unavailable */ } }, [state]);
  const patch = useCallback((value) => dispatch({ type: "patch", value }), []);
  const reset = useCallback(() => dispatch({ type: "reset" }), []);
  const replace = useCallback((value) => {
    const validated = validateConfig(value);
    dispatch({ type: "replace", value: validated });
    return validated;
  }, []);
  const event = useCallback((value) => dispatch({ type: "event", value }), []);
  const exportConfig = useCallback(() => JSON.stringify(state, null, 2), [state]);
  const api = useMemo(() => ({ state, patch, reset, replace, event, exportConfig }), [state, patch, reset, replace, event, exportConfig]);
  return createElement(AppStoreContext.Provider, { value: api }, children);
}
export function useAppStore() { const value = useContext(AppStoreContext); if (!value) throw new Error("useAppStore must be used inside AppStoreProvider"); return value; }
