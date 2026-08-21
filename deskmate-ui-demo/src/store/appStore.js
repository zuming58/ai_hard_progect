import { createContext, createElement, useContext, useEffect, useMemo, useReducer } from "react";
import { expressionPresets, historyItems, keyActions } from "../appData.js";

export const STORAGE_KEY = "deskmate.app-state";
export const SCHEMA_VERSION = 1;

export const defaultState = {
  schemaVersion: SCHEMA_VERSION,
  history: historyItems,
  vocabulary: { hotwords: ["DeskMate", "ESP32-S3", "Codex", "Claude Code", "Hermes"], rules: [{ from: "桌面宠物", to: "桌宠" }, { from: "克劳德代码", to: "Claude Code" }] },
  keymap: [...keyActions.slice(0, 8)],
  settings: { microphoneId: "", microphoneSource: "computer", formatting: "smart", theme: "system", floating: true, operation: "toggle", startupSound: true },
  expressionMapping: { idle: "sleep", listening: "listen", thinking: "think", working: "focus", waiting_user: "listen", completed: "happy", error: "alert" },
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
  try { return migrateState(JSON.parse(storage?.getItem(STORAGE_KEY) || "null")); } catch { return structuredClone(defaultState); }
}

export function validateConfig(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("配置必须是 JSON 对象");
  if (value.schemaVersion !== undefined && typeof value.schemaVersion !== "number") throw new Error("schemaVersion 必须是数字");
  if (value.keymap !== undefined && (!Array.isArray(value.keymap) || value.keymap.length !== 8)) throw new Error("按键映射必须包含 8 项");
  if (value.vocabulary?.rules && !Array.isArray(value.vocabulary.rules)) throw new Error("替换规则格式无效");
  return migrateState(value);
}

function reducer(state, action) {
  if (action.type === "reset") return structuredClone(defaultState);
  if (action.type === "replace") return validateConfig(action.value);
  if (action.type === "patch") return { ...state, ...action.value };
  if (action.type === "event") {
    const event = action.value;
    const expression = state.expressionMapping[event.type] || state.currentExpression;
    return { ...state, aiEvent: event, currentExpression: expression };
  }
  return state;
}

const AppStoreContext = createContext(null);
export function AppStoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, undefined, loadState);
  useEffect(() => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* storage can be unavailable */ } }, [state]);
  const api = useMemo(() => ({ state, dispatch, patch: (value) => dispatch({ type: "patch", value }), reset: () => dispatch({ type: "reset" }), replace: (value) => dispatch({ type: "replace", value }), event: (value) => dispatch({ type: "event", value }), exportConfig: () => JSON.stringify(state, null, 2) }), [state]);
  return createElement(AppStoreContext.Provider, { value: api }, children);
}
export function useAppStore() { const value = useContext(AppStoreContext); if (!value) throw new Error("useAppStore must be used inside AppStoreProvider"); return value; }
