import { useEffect, useState } from "react";
import {
  IconBell as Bell,
  IconBook as BookOpen,
  IconBrain as Brain,
  IconChevronLeft as ChevronLeft,
  IconChevronRight as ChevronRight,
  IconCircleCheck as CircleCheck,
  IconCode as Code,
  IconKeyboard as Keyboard,
  IconLayoutDashboard as LayoutDashboard,
  IconMenu2 as Menu2,
  IconMicrophone2 as Microphone2,
  IconMoodSmile as MoodSmile,
  IconPalette as Palette,
  IconPlugConnected as PlugConnected,
  IconRotate3d as Rotate3d,
  IconSettings2 as Settings2,
  IconSparkles as Sparkles,
  IconTemperature as Temperature,
  IconX as X,
} from "@tabler/icons-react";
import { pageMeta } from "./appData.js";
import { AppStoreProvider, useAppStore } from "./store/appStore.js";
import { mockAdapters } from "./adapters/index.js";
import {
  AgentsPage,
  ConnectionsPage,
  DashboardPage,
  ExpressionEditorPage,
  ExpressionsPage,
  HistoryPage,
  KeymapPage,
  MotionPage,
  SensorsPage,
  SettingsPage,
  VocabularyPage,
  VoicePage,
} from "./pages.jsx";

const navigation = [
  { id: "dashboard", label: "工作台", icon: LayoutDashboard },
  { id: "voice", label: "语音输入", icon: Microphone2 },
  { id: "history", label: "历史记录", icon: BookOpen },
  { id: "vocabulary", label: "词库", icon: Brain },
  { id: "keymap", label: "按键配置", icon: Keyboard },
  { id: "connections", label: "设备连接", icon: PlugConnected },
  { id: "agents", label: "AI 联动", icon: Code },
  { id: "expressions", label: "表情库", icon: MoodSmile },
  { id: "editor", label: "表情编辑", icon: Palette },
  { id: "motion", label: "动作编排", icon: Rotate3d },
  { id: "sensors", label: "环境感知", icon: Temperature },
  { id: "settings", label: "设置诊断", icon: Settings2 },
];

function BrandMark() {
  return <span className="brand-mark"><MoodSmile size={23} stroke={1.8} /></span>;
}

function Sidebar({ current, navigate, collapsed, setCollapsed, mobileOpen, setMobileOpen }) {
  return (
    <aside className={`sidebar ${collapsed ? "is-collapsed" : ""} ${mobileOpen ? "is-mobile-open" : ""}`}>
      <div className="sidebar__brand">
        <BrandMark />
        <div className="brand-copy"><strong>DESKMATE</strong><span>AI 工作台伙伴</span></div>
        <button className="sidebar__mobile-close" onClick={() => setMobileOpen(false)} aria-label="关闭菜单"><X size={20} /></button>
      </div>
      <div className="sidebar__rule" />
      <nav className="sidebar__nav" aria-label="主导航">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={current === item.id ? "is-active" : ""}
              onClick={() => { navigate(item.id); setMobileOpen(false); }}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={21} stroke={1.65} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <button className="sidebar__collapse" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "展开侧栏" : "收起侧栏"}>{collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}<span>收起导航</span></button>
      <div className="device-card">
        <div className="device-card__screen"><img src="/assets/deskmate-focus-face.png" alt="DeskMate 设备" /></div>
        <div className="device-card__status device-card__status--pending"><span />板子联动待接入</div>
        <small>Windows 已识别 HID · App 桥待接入</small>
      </div>
    </aside>
  );
}

function AppHeader({ current, setMobileOpen }) {
  const meta = pageMeta[current];
  return (
    <header className="app-header">
      <button className="mobile-menu" aria-label="打开菜单" onClick={() => setMobileOpen(true)}><Menu2 size={22} /></button>
      <div className="breadcrumbs"><strong>DESKMATE</strong><span>/</span><span>{meta.title}</span></div>
      <div className="app-header__right">
        <span className="service-status"><i />本地核心已运行</span>
        <span className="app-date">8月20日 · 周四</span>
        <button className="header-icon" aria-label="通知"><Bell size={19} stroke={1.7} /><i /></button>
      </div>
    </header>
  );
}

const pages = {
  dashboard: DashboardPage,
  voice: VoicePage,
  history: HistoryPage,
  vocabulary: VocabularyPage,
  keymap: KeymapPage,
  connections: ConnectionsPage,
  agents: AgentsPage,
  expressions: ExpressionsPage,
  editor: ExpressionEditorPage,
  motion: MotionPage,
  sensors: SensorsPage,
  settings: SettingsPage,
};

function resolveHash() {
  const value = window.location.hash.replace("#/", "").replace("#", "");
  return pages[value] ? value : "dashboard";
}

export function App() {
  return <AppStoreProvider><AppContent /></AppStoreProvider>;
}

function AppContent() {
  const [current, setCurrent] = useState(resolveHash);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState("");
  const { event } = useAppStore();
  useEffect(() => mockAdapters.agentStatus.subscribe(event, { emitCurrent: false }), [event]);
  useEffect(() => {
    const onHash = () => setCurrent(resolveHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);
  const navigate = (page) => {
    window.location.hash = `/${page}`;
    setCurrent(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const CurrentPage = pages[current] || DashboardPage;
  return (
    <div className={`app-shell ${collapsed ? "has-collapsed-sidebar" : ""}`}>
      <Sidebar current={current} navigate={navigate} collapsed={collapsed} setCollapsed={setCollapsed} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      {mobileOpen && <button className="mobile-scrim" aria-label="关闭菜单" onClick={() => setMobileOpen(false)} />}
      <main className="app-main">
        <AppHeader current={current} setMobileOpen={setMobileOpen} />
        <div className="app-content"><CurrentPage navigate={navigate} notify={setToast} /></div>
      </main>
      {toast && <div className="toast"><CircleCheck size={18} />{toast}</div>}
      <div className="demo-watermark"><Sparkles size={14} />软件 MVP · 板子联动待接入</div>
    </div>
  );
}
