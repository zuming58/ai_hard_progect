import { useEffect, useMemo, useState } from "react";
import {
  IconAdjustmentsHorizontal as AdjustmentsHorizontal,
  IconAlertCircle as AlertCircle,
  IconArrowDown as ArrowDown,
  IconArrowLeft as ArrowLeft,
  IconArrowRight as ArrowRight,
  IconArrowUp as ArrowUp,
  IconBluetooth as Bluetooth,
  IconBook2 as Book2,
  IconBrain as Brain,
  IconCheck as Check,
  IconCloudDownload as CloudDownload,
  IconCode as Code,
  IconCopy as Copy,
  IconDeviceFloppy as DeviceFloppy,
  IconDeviceGamepad2 as DeviceGamepad2,
  IconDownload as Download,
  IconEye as Eye,
  IconFileExport as FileExport,
  IconGauge as Gauge,
  IconHistory as History,
  IconKeyboard as Keyboard,
  IconLink as Link,
  IconLock as Lock,
  IconMicrophone2 as Microphone2,
  IconMoodHappy as MoodHappy,
  IconMoodNerd as MoodNerd,
  IconMoodSmile as MoodSmile,
  IconMoon as Moon,
  IconMusic as Music,
  IconPlayerPause as PlayerPause,
  IconPlayerPlay as PlayerPlay,
  IconPlus as Plus,
  IconRefresh as Refresh,
  IconSend as Send,
  IconSettings2 as Settings2,
  IconSparkles as Sparkles,
  IconSun as Sun,
  IconTemperature as Temperature,
  IconTrash as Trash,
  IconUpload as Upload,
  IconUser as User,
} from "@tabler/icons-react";
import { agents, expressionPresets, historyItems, keyActions } from "./appData.js";
import { useAppStore } from "./store/appStore.js";
import { useRecorder } from "./hooks/useRecorder.js";
import {
  Button,
  Card,
  EmptyState,
  IconButton,
  Keycap,
  Metric,
  Notice,
  PageIntro,
  SearchField,
  SectionTitle,
  Segmented,
  Select,
  SettingRow,
  Slider,
  StatusBadge,
  Toggle,
} from "./ui.jsx";

const moodIcons = {
  focus: MoodNerd,
  listen: MoodSmile,
  think: Brain,
  happy: MoodHappy,
  sleep: Moon,
  alert: AlertCircle,
};

function ExpressionTile({ preset, selected, onClick, compact = false }) {
  const Icon = moodIcons[preset.mood] || MoodSmile;
  return (
    <button className={`expression-tile expression-tile--${preset.color} ${selected ? "is-selected" : ""} ${compact ? "is-compact" : ""}`} onClick={onClick}>
      <span className="expression-screen"><Icon size={compact ? 28 : 38} stroke={1.6} /></span>
      <span><strong>{preset.name}</strong>{!compact && <small>{preset.description}</small>}</span>
      {selected && <span className="expression-check"><Check size={14} /></span>}
    </button>
  );
}

export function DashboardPage({ navigate, notify }) {
  const { state, event } = useAppStore();
  const expression = state.currentExpression;
  const selectedPreset = expressionPresets.find((item) => item.id === expression);
  return (
    <div className="page page--dashboard">
      <PageIntro
        title="工作台"
        description="查看桌宠状态、AI 任务进度与设备运行情况"
        actions={<Button icon={Sparkles} variant="soft" onClick={() => notify("智能联动模式已启用")}>智能联动模式</Button>}
      />
      <div className="dashboard-grid">
        <Card className="pet-showcase">
          <div className="card-heading">
            <div><strong>桌宠实时状态</strong><small>DESKMATE · LIVE</small></div>
            <StatusBadge tone="success">{selectedPreset.name}中</StatusBadge>
          </div>
          <div className="pet-visual">
            <img src="/assets/deskmate-focus-face.png" alt="DeskMate 桌宠专注表情" />
            <span className="pet-mode"><span />{expression.toUpperCase()} · {selectedPreset.name}模式</span>
          </div>
          <div className="pet-footer">
            <div><small>设备姿态</small><strong>正对用户 · 0°</strong></div>
            <div className="sensor-mini"><span><strong>24.6℃</strong><small>温度</small></span><span><strong>46%</strong><small>湿度</small></span><span><strong>68%</strong><small>环境光</small></span></div>
          </div>
        </Card>
        <Card className="task-panel">
          <div className="task-panel__top"><span className="agent-label">CODEX</span><StatusBadge tone="success">运行中</StatusBadge></div>
          <div><h2>Codex 正在工作</h2><p>整理桌宠开发文档并生成任务结构</p></div>
          <div className="progress-block">
            <div className="progress-ring" style={{ "--value": 68 }}><strong>68<span>%</span></strong><small>任务进度</small></div>
            <div><span className="blue-kicker">当前步骤</span><h3>提取关键信息</h3><p>分析文档结构，识别核心内容</p></div>
          </div>
          <Button variant="primary" className="button--wide" onClick={() => navigate("agents")}>查看当前任务 <ArrowRight size={18} /></Button>
          <div className="task-divider" />
          <div className="card-heading"><strong>工作表情</strong><button className="text-link" onClick={() => navigate("expressions")}>管理表情 <ArrowRight size={14} /></button></div>
          <div className="expression-row">
            {expressionPresets.slice(0, 3).map((item) => <ExpressionTile key={item.id} compact preset={item} selected={expression === item.id} onClick={() => event({ type: item.id === "focus" ? "working" : item.id === "listen" ? "listening" : "thinking", agent: "Codex", progress: state.aiEvent.progress, detail: state.aiEvent.detail })} />)}
          </div>
          <div className="sync-line"><span />状态同步正常 · 2 秒前</div>
        </Card>
      </div>
    </div>
  );
}

export function VoicePage({ notify }) {
  const { state, patch } = useAppStore();
  const [source, setSource] = useState(state.settings.microphoneId || "");
  const [devices, setDevices] = useState([]);
  const [transcript, setTranscript] = useState("");
  const [recordingItem, setRecordingItem] = useState(null);
  const { status, seconds, level, error, start, stop, cancel } = useRecorder({ deviceId: source || undefined, onComplete: (item) => { setRecordingItem(item); setTranscript("录音完成，等待转写服务"); patch({ history: [{ id: Date.now(), time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }), date: "今天", duration: `${item.duration} 秒`, count: "待转写", text: "录音完成，等待转写服务" }, ...state.history] }); notify("录音已完成，等待转写服务"); }, onError: notify });
  const recording = status === "recording";
  const toggleRecording = () => recording ? stop() : start();
  useEffect(() => {
    let active = true;
    const list = async () => { try { const items = await navigator.mediaDevices?.enumerateDevices?.() || []; if (active) setDevices(items.filter((item) => item.kind === "audioinput")); } catch { /* permissions may hide labels */ } };
    list(); navigator.mediaDevices?.addEventListener?.("devicechange", list); return () => { active = false; navigator.mediaDevices?.removeEventListener?.("devicechange", list); };
  }, []);
  useEffect(() => { if (source && devices.length && !devices.some((device) => device.deviceId === source)) { setSource(""); patch({ settings: { ...state.settings, microphoneId: "" } }); notify("所选麦克风已拔出，已切换为系统默认设备"); } }, [devices, source]);
  const time = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  return (
    <div className="page">
      <PageIntro title="语音输入" description="专注录音、实时转写与智能整理" actions={<StatusBadge tone="success">语音服务已连接</StatusBadge>} />
      <Card className="voice-console">
        <div className="voice-console__header">
          <div><span className="section-kicker"><span>01</span>语音输入</span><p>专注录音与转写</p></div>
          <div className="source-switch">
            <Microphone2 size={18} />
            <select className="voice-device-select" value={source} onChange={(event) => { setSource(event.target.value); patch({ settings: { ...state.settings, microphoneId: event.target.value } }); }} aria-label="麦克风设备"><option value="">系统默认麦克风</option>{devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `麦克风 ${index + 1}`}</option>)}</select>
          </div>
        </div>
          <div className={`recorder ${recording ? "is-recording" : ""}`}>
          <div className="recorder__state"><span className="pulse-dot" />{recording ? "正在录音…" : transcript ? "录音完成" : "准备就绪"}</div>
          <div className="waveform" aria-label="录音声波">
            {Array.from({ length: 42 }).map((_, index) => <span key={index} style={{ "--height": `${recording ? Math.max(8, level * (0.35 + ((index % 5) / 10))) : 8 + ((index * 7) % 14)}px`, "--delay": `${index * -0.04}s` }} />)}
          </div>
          <div className="recorder__time">{time}</div>
          <p className="recorder__transcript">{transcript || (recording ? "正在采集音频…" : "按下按钮或使用快捷键开始录音")}</p>
          <Button icon={recording ? PlayerPause : Microphone2} variant={recording ? "danger" : "primary"} onClick={toggleRecording}>{recording ? "停止录音" : "开始录音"}</Button>
          {recording && <Button variant="ghost" onClick={cancel}>取消</Button>}
          {recordingItem?.blob && <audio controls src={URL.createObjectURL(recordingItem.blob)} />}
          {error && <Notice tone="warning" title="麦克风不可用">{error}</Notice>}
        </div>
      <div className="voice-statusbar"><span>状态 · {recording ? "正在录音" : status === "error" ? "不可用" : "准备就绪"}</span><span>音量 · {level}%</span><span>悬浮窗 · {state.settings.floating ? "已开启" : "已关闭"}</span></div>
      </Card>
      <div className="two-column compact-panels">
        <Card><SectionTitle index="02" title="输出方式" /><SettingRow title="智能整理" description="移除口头语并按语义分段"><Toggle checked onChange={() => notify("将在下一次录音时生效")} /></SettingRow></Card>
        <Card><SectionTitle index="03" title="录音设备" /><SettingRow title={source === "computer" ? "系统默认麦克风" : "EasyInput 键盘麦克风"} description="录音过程中不会自动切换"><StatusBadge tone="success">可用</StatusBadge></SettingRow></Card>
      </div>
    </div>
  );
}

export function HistoryPage({ notify }) {
  const { state, patch } = useAppStore();
  const [query, setQuery] = useState("");
  const items = state.history;
  const setItems = (next) => patch({ history: typeof next === "function" ? next(state.history) : next });
  const filtered = items.filter((item) => item.text.includes(query) || item.time.includes(query));
  const copy = async (text) => { try { await navigator.clipboard.writeText(text); } catch { /* demo fallback */ } notify("内容已复制"); };
  return (
    <div className="page">
      <PageIntro title="历史记录" description="管理、搜索和导出最近的语音输入" actions={<><Button icon={FileExport} onClick={() => notify("已生成演示导出文件")}>导出</Button><Button icon={Trash} variant="ghost" onClick={() => setItems([])}>清空</Button></>} />
      <Card>
        <div className="list-toolbar"><div><strong>最近记录</strong><small>共 {items.length} 条演示记录</small></div><SearchField value={query} onChange={setQuery} placeholder="搜索文字或时间" /></div>
        {filtered.length ? <div className="history-list">{filtered.map((item) => <article className="history-item" key={item.id}><time>{item.time}</time><div><p>{item.text}</p><small>{item.date} · {item.duration} · {item.count}</small></div><div className="row-actions"><IconButton icon={Copy} label="复制" onClick={() => copy(item.text)} /><IconButton icon={Trash} label="删除" onClick={() => setItems((current) => current.filter((entry) => entry.id !== item.id))} /></div></article>)}</div> : <EmptyState icon={History} title="没有找到记录" description="更换搜索词，或者开始一次新的语音输入。" />}
      </Card>
    </div>
  );
}

export function VocabularyPage({ notify }) {
  const { state, patch } = useAppStore();
  const hotwords = state.vocabulary.hotwords;
  const rules = state.vocabulary.rules;
  const setHotwords = (next) => patch({ vocabulary: { ...state.vocabulary, hotwords: typeof next === "function" ? next(hotwords) : next } });
  const setRules = (next) => patch({ vocabulary: { ...state.vocabulary, rules: typeof next === "function" ? next(rules) : next } });
  const [newWord, setNewWord] = useState("");
  const addWord = () => { if (!newWord.trim()) return; setHotwords([...hotwords, newWord.trim()]); setNewWord(""); notify("热词已添加"); };
  return (
    <div className="page">
      <PageIntro title="词库" description="提高专有名词识别率并自动修正常见表达" actions={<><Button icon={Upload}>导入</Button><Button icon={Download}>导出</Button><Button icon={DeviceFloppy} variant="primary" onClick={() => notify("词库更改已保存")}>保存更改</Button></>} />
      <div className="two-column vocabulary-layout">
        <Card>
          <SectionTitle index="01" title={`热词 · ${hotwords.length} 个`} description="让语音识别更容易听对人名、产品名和项目名。" />
          <div className="chips">{hotwords.map((word) => <button key={word} className="chip" onClick={() => setHotwords(hotwords.filter((entry) => entry !== word))}>{word}<span>×</span></button>)}</div>
          <div className="inline-form"><input value={newWord} onChange={(e) => setNewWord(e.target.value)} placeholder="添加新的专业词汇" onKeyDown={(e) => e.key === "Enter" && addWord()} /><Button icon={Plus} onClick={addWord}>添加</Button></div>
        </Card>
        <Card>
          <SectionTitle index="02" title={`替换规则 · ${rules.length} 条`} description="识别完成后自动把左侧词语替换为右侧。" />
          <div className="rule-list">{rules.map((rule, index) => <div className="rule-row" key={`${rule.from}-${index}`}><input value={rule.from} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, from: e.target.value } : item))} /><ArrowRight size={18} /><input value={rule.to} onChange={(e) => setRules(rules.map((item, i) => i === index ? { ...item, to: e.target.value } : item))} /><IconButton icon={Trash} label="删除" onClick={() => setRules(rules.filter((_, i) => i !== index))} /></div>)}</div>
          <Button icon={Plus} variant="ghost" onClick={() => setRules([...rules, { from: "", to: "" }])}>添加规则</Button>
        </Card>
      </div>
    </div>
  );
}

export function KeymapPage({ notify }) {
  const { state, patch } = useAppStore();
  const [selectedKey, setSelectedKey] = useState(0);
  const actions = state.keymap;
  const update = (value) => patch({ keymap: actions.map((action, index) => index === selectedKey ? value : action) });
  return (
    <div className="page">
      <PageIntro title="按键配置" description="配置键盘按键、旋钮和快捷动作" actions={<><StatusBadge tone="success">EasyInput AI 已连接</StatusBadge><Button icon={Send} variant="primary" onClick={() => notify("配置已模拟同步到键盘")}>同步到键盘</Button></>} />
      <Notice tone="demo" title="演示模式">当前尚未获得真实键盘通信协议；页面中的同步和容量为模拟状态。</Notice>
      <div className="keymap-grid">
        <Card className="keymap-board">
          <div className="device-line"><span>当前电脑 <strong>Windows</strong></span><span>键盘系统 <strong>尚未读取</strong></span><span>同步结果 <strong className="success-text">UI 已就绪</strong></span></div>
          <div className="keyboard-visual">
            <div className="key-grid">{actions.map((action, index) => <button key={index} className={`hardware-key ${selectedKey === index ? "is-selected" : ""}`} onClick={() => setSelectedKey(index)}><small>KEY{index + 1}</small><Keyboard size={25} stroke={1.5} /><strong>{action}</strong></button>)}</div>
            <button className="dial-control" onClick={() => notify("旋钮：滚动 / 上下")}><AdjustmentsHorizontal size={42} stroke={1.3} /><strong>滚动 · 上下</strong><small>ENCODER</small></button>
          </div>
        </Card>
        <Card className="key-editor">
          <div className="key-editor__title"><span>KEY {selectedKey + 1}</span><strong>按键设置</strong></div>
          <label>按下动作<Select value={actions[selectedKey]} onChange={update} ariaLabel="按键动作">{keyActions.map((action) => <option key={action}>{action}</option>)}</Select></label>
          <div className="mapping-preview"><span>当前映射</span><strong>{actions[selectedKey]}</strong><small>切换按键后自动保存到本机</small></div>
          <Button variant="primary" className="button--wide" onClick={() => notify(`KEY ${selectedKey + 1} 已保存为“${actions[selectedKey]}”`)}>保存当前按键</Button>
        </Card>
      </div>
    </div>
  );
}

export function ConnectionsPage({ notify }) {
  const { state, patch } = useAppStore();
  const [tab, setTab] = useState("overview");
  const mic = state.settings.microphoneSource || "computer";
  const setMic = (value) => patch({ settings: { ...state.settings, microphoneSource: value } });
  const startupSound = state.settings.startupSound;
  const setStartupSound = (value) => patch({ settings: { ...state.settings, startupSound: value } });
  const [wifiName, setWifiName] = useState("");
  return (
    <div className="page">
      <PageIntro title="设备与连接" description="管理 USB、Wi-Fi、蓝牙、麦克风与提示音" actions={<Button icon={Refresh} onClick={() => notify("设备状态已刷新")}>刷新设备</Button>} />
      <Segmented value={tab} onChange={setTab} options={[{ value: "overview", label: "连接概览" }, { value: "microphone", label: "麦克风" }, { value: "network", label: "Wi-Fi 与蓝牙" }, { value: "sound", label: "提示音" }]} />
      {tab === "overview" && <div className="connection-cards">
        <Card interactive><div className="connection-icon"><Link size={28} /></div><div><strong>USB 键盘输入</strong><p>HID 设备 · VID 303A</p></div><StatusBadge tone="success">已连接</StatusBadge></Card>
        <Card interactive><div className="connection-icon"><Microphone2 size={28} /></div><div><strong>键盘麦克风</strong><p>需要 2.4GHz Wi-Fi</p></div><StatusBadge tone="warning">待配网</StatusBadge></Card>
        <Card interactive><div className="connection-icon"><Bluetooth size={28} /></div><div><strong>蓝牙键盘</strong><p>可作为普通输入设备使用</p></div><StatusBadge tone="neutral">未连接</StatusBadge></Card>
        <Card interactive><div className="connection-icon"><DeviceGamepad2 size={28} /></div><div><strong>桌宠控制器</strong><p>串口协议待接入</p></div><StatusBadge tone="demo">Demo</StatusBadge></Card>
      </div>}
      {tab === "microphone" && <Card><SectionTitle index="01" title="麦克风来源" description="录音开始后不会中途切换。" /><Segmented value={mic} onChange={setMic} options={[{ value: "computer", label: "电脑优先" }, { value: "keyboard", label: "键盘优先" }]} /><Notice tone="success" title={mic === "computer" ? "已选择电脑麦克风" : "已选择键盘麦克风"}>{mic === "computer" ? "键盘网络仍可用于同步提示音和配置。" : "键盘麦克风采集的音频将通过局域网实时发送到电脑。"}</Notice></Card>}
      {tab === "network" && <div className="two-column"><Card><SectionTitle index="01" title="网络与连接" description="键盘仅支持 2.4GHz Wi-Fi。" /><Notice tone="warning" title="配网尚未完成">电脑和键盘需要处于同一路由器网络。</Notice><label className="field-label">Wi-Fi 名称<input value={wifiName} onChange={(e) => setWifiName(e.target.value)} placeholder="自动获取或手动输入" /></label><label className="field-label">Wi-Fi 密码<input type="password" placeholder="开放网络可留空" /></label><Button icon={Send} variant="primary" onClick={() => notify(wifiName ? "网络配置已保存到 Demo" : "请先填写 Wi-Fi 名称")}>补全后同步</Button></Card><Card><SectionTitle index="02" title="蓝牙功能" /><SettingRow icon={Bluetooth} title="蓝牙 HID 输入" description="用于按键和旋钮，不用于传输麦克风音频"><Toggle checked onChange={() => notify("蓝牙状态为 Demo")}/></SettingRow><Notice tone="info" title="为什么麦克风需要 Wi-Fi？">蓝牙 HID 适合传输按键事件，不适合这套方案的实时音频数据；键盘麦克风通过局域网把音频流发送给电脑。</Notice></Card></div>}
      {tab === "sound" && <Card><SectionTitle index="03" title="开机提示音" description="选择内置音效或导入最长 8 秒的音频。" /><div className="sound-grid">{["WaytoAGI", "来 WaytoAGI 学 AI 硬件", "又来写 bug 了", "晶亮启动", "柔和启动", "极简启动"].map((name, index) => <button key={name} className={index === 0 ? "is-selected" : ""} onClick={() => notify(`已试听“${name}”`)}><Music size={22} /><strong>{name}</strong><small>{["1.7", "2.8", "2.1", "0.6", "0.8", "0.3"][index]} 秒</small></button>)}</div><SettingRow title="开机音效" description="完整开机时播放已选音效"><Toggle checked={startupSound} onChange={setStartupSound} /></SettingRow></Card>}
    </div>
  );
}

export function AgentsPage({ notify }) {
  const { state, patch, event } = useAppStore();
  const mapping = state.expressionMapping;
  const setMapping = (next) => patch({ expressionMapping: next });
  return (
    <div className="page">
      <PageIntro title="AI 联动" description="把编程助手的运行状态映射到桌宠灯效和表情" actions={<Button icon={Plus} variant="primary" onClick={() => notify("自定义适配器将在开发阶段开放")}>添加适配器</Button>} />
      <Notice tone="demo" title="适配器 Demo">Codex、Claude Code、Hermes 和 Workbody 的自动状态读取尚未接入，本页演示未来的映射逻辑。</Notice>
      <div className="agent-grid">{agents.map((agent) => <Card key={agent.id} className={`agent-card agent-card--${agent.tone}`}>
        <div className="agent-card__head"><span className="agent-icon"><Code size={24} /></span><StatusBadge tone={agent.state === "工作中" ? "success" : agent.state === "待命" ? "neutral" : "warning"}>{agent.state}</StatusBadge></div>
        <h3>{agent.name}</h3><p>{agent.id === "codex" ? state.aiEvent.detail : agent.detail}</p>
        {agent.progress > 0 && <div className="agent-progress"><span style={{ width: `${agent.progress}%` }} /><small>{agent.progress}%</small></div>}
        <label>工作时表情<Select value={mapping[agent.id]} onChange={(value) => setMapping({ ...mapping, [agent.id]: value })}>{expressionPresets.map((item) => <option key={item.id}>{item.name}</option>)}</Select></label>
        <Button icon={agent.state === "未连接" || agent.state === "未配置" ? Settings2 : Eye} onClick={() => notify(`${agent.name} 配置面板为演示状态`)}>{agent.state === "未连接" || agent.state === "未配置" ? "配置" : "查看状态"}</Button>
      </Card>)}</div>
      <Card><SectionTitle index="02" title="状态接收" description="桌宠 App 将把适配器状态统一为待命、工作、等待、完成和错误。" /><div className="state-flow"><span>AI 工具</span><ArrowRight /><span>本地适配器</span><ArrowRight /><span>DeskMate 状态总线</span><ArrowRight /><span>表情 / 动作 / 灯效</span></div></Card>
    </div>
  );
}

export function ExpressionsPage({ navigate, notify }) {
  const [selected, setSelected] = useState("focus");
  const [category, setCategory] = useState("all");
  const filtered = category === "all" ? expressionPresets : expressionPresets.filter((item) => category === "work" ? ["focus", "listen", "think"].includes(item.id) : ["happy", "sleep", "alert"].includes(item.id));
  return (
    <div className="page">
      <PageIntro title="表情库" description="管理内置表情、收藏与工作状态映射" actions={<Button icon={Plus} variant="primary" onClick={() => navigate("editor")}>新建表情</Button>} />
      <div className="library-toolbar"><Segmented value={category} onChange={setCategory} options={[{ value: "all", label: "全部" }, { value: "work", label: "工作状态" }, { value: "life", label: "生活状态" }]} /><SearchField value="" placeholder="搜索表情" /></div>
      <div className="expression-library">{filtered.map((preset) => <ExpressionTile key={preset.id} preset={preset} selected={selected === preset.id} onClick={() => setSelected(preset.id)} />)}</div>
      <Card className="assignment-card"><SectionTitle index="02" title="当前状态映射" description="选择一个工作状态，再指定桌宠显示的表情。" /><div className="assignment-grid">{[["Codex 工作中", "专注"], ["等待用户输入", "倾听"], ["复杂推理", "思考"], ["任务已完成", "开心"]].map(([state, mood]) => <div key={state}><span>{state}</span><Select value={mood} onChange={() => notify("映射已在 Demo 中更新")}>{expressionPresets.map((item) => <option key={item.id}>{item.name}</option>)}</Select></div>)}</div></Card>
    </div>
  );
}

export function ExpressionEditorPage({ notify }) {
  const { state, patch } = useAppStore();
  const { eyeSize, eyeGap, brightness, blink, color } = state.expressionEditor;
  const updateEditor = (value) => patch({ expressionEditor: { ...state.expressionEditor, ...value } });
  return (
    <div className="page">
      <PageIntro title="表情编辑" description="调整眼睛、嘴型、颜色和动画节奏" actions={<><Button icon={Eye} onClick={() => notify("预览已同步到虚拟桌宠")}>实时预览</Button><Button icon={DeviceFloppy} variant="primary" onClick={() => notify("表情“专注 Pro”已保存")}>保存表情</Button></>} />
      <div className="editor-grid">
        <Card className="editor-preview"><div className="card-heading"><strong>实时预览</strong><StatusBadge tone="demo">虚拟设备</StatusBadge></div><div className={`editor-face editor-face--${color}`} style={{ "--eye-size": `${eyeSize}%`, "--eye-gap": `${eyeGap}px`, opacity: 0.55 + brightness / 220 }}><MoodNerd size={230} stroke={1.25} /></div><div className="preview-note">硬件屏幕协议接入后，将使用相同参数生成端侧动画。</div></Card>
        <Card className="editor-controls">
          <SectionTitle index="01" title="眼睛" />
          <SettingRow title="眼睛尺寸" description="控制两只眼睛的整体大小"><Slider label="眼睛尺寸" value={eyeSize} onChange={(value) => updateEditor({ eyeSize: value })} /></SettingRow>
          <SettingRow title="眼间距" description="适配不同宽度的显示屏"><Slider label="眼间距" value={eyeGap} onChange={(value) => updateEditor({ eyeGap: value })} min={32} max={96} suffix=" px" /></SettingRow>
          <SettingRow title="自动眨眼" description="空闲时随机眨眼，更有生命感"><Toggle checked={blink} onChange={(value) => updateEditor({ blink: value })} /></SettingRow>
          <SectionTitle index="02" title="颜色与亮度" />
          <div className="color-options">{["cyan", "blue", "violet", "green", "amber"].map((item) => <button aria-label={`${item} 颜色`} className={`${item} ${color === item ? "is-selected" : ""}`} onClick={() => updateEditor({ color: item })} key={item} />)}</div>
          <SettingRow title="显示亮度" description="最终值还会受到环境光上限约束"><Slider label="显示亮度" value={brightness} onChange={(value) => updateEditor({ brightness: value })} /></SettingRow>
        </Card>
      </div>
    </div>
  );
}

export function MotionPage({ notify }) {
  const { state, patch } = useAppStore();
  const { preset, speed, range } = state.motion;
  const updateMotion = (value) => patch({ motion: { ...state.motion, ...value } });
  const [testing, setTesting] = useState(false);
  const play = () => { setTesting(true); notify("正在播放虚拟动作预览"); window.setTimeout(() => setTesting(false), 1800); };
  return (
    <div className="page">
      <PageIntro title="动作编排" description="设计左右摇头、上下点头与组合动作" actions={<Button icon={testing ? PlayerPause : PlayerPlay} variant="primary" onClick={play}>{testing ? "预览中…" : "测试动作"}</Button>} />
      <Notice tone="demo" title="虚拟动作预览">双轴舵机型号、角度零点和安全限位尚未确定，当前只展示动作编排体验。</Notice>
      <div className="motion-grid">
        <Card className="motion-stage"><div className={`motion-avatar ${testing ? `is-playing is-${preset}` : ""}`}><img src="/assets/deskmate-focus-face.png" alt="桌宠动作预览" /></div><div className="axis-controls"><Button icon={ArrowLeft}>左转</Button><Button icon={ArrowUp}>抬头</Button><Button icon={ArrowDown}>点头</Button><Button icon={ArrowRight}>右转</Button></div></Card>
        <Card><SectionTitle index="01" title="动作参数" /><label className="field-label">动作预设<Segmented value={preset} onChange={(value) => updateMotion({ preset: value })} options={[{ value: "attentive", label: "关注" }, { value: "nod", label: "点头" }, { value: "search", label: "寻找" }]} /></label><SettingRow title="动作速度" description="速度越高，运动越利落"><Slider label="动作速度" value={speed} onChange={(value) => updateMotion({ speed: value })} /></SettingRow><SettingRow title="运动范围" description="限制头部最大转动角度"><Slider label="运动范围" value={range} onChange={(value) => updateMotion({ range: value })} min={10} max={80} suffix="°" /></SettingRow><SettingRow title="柔性起停" description="减少舵机突然启动带来的晃动"><Toggle checked onChange={() => notify("柔性起停已保持开启")} /></SettingRow></Card>
      </div>
      <Card><SectionTitle index="02" title="动作时间线" description="把表情和动作组合为一段可复用行为。" /><div className="timeline"><span className="timeline-label">0s</span><div className="timeline-track"><i style={{ left: "4%", width: "22%" }}>看向用户</i><i style={{ left: "32%", width: "18%" }}>眨眼</i><i style={{ left: "56%", width: "32%" }}>轻点头 × 2</i></div><span className="timeline-label">4s</span></div></Card>
    </div>
  );
}

export function SensorsPage({ notify }) {
  const { state, patch } = useAppStore();
  const { autoBrightness, faceTracking } = state.sensors;
  const updateSensors = (value) => patch({ sensors: { ...state.sensors, ...value } });
  const bars = useMemo(() => Array.from({ length: 28 }).map((_, index) => 28 + ((index * 19) % 56)), []);
  return (
    <div className="page">
      <PageIntro title="环境感知" description="查看温湿度、环境光与用户方向检测" actions={<StatusBadge tone="demo">传感器模拟数据</StatusBadge>} />
      <div className="metric-grid"><Metric label="环境温度" value="24.6" unit="℃" trend="舒适范围" tone="orange" /><Metric label="空气湿度" value="46" unit="%" trend="较昨日 +2%" tone="blue" /><Metric label="环境光" value="328" unit="lx" trend="建议亮度 68%" tone="cyan" /><Metric label="用户方向" value="0" unit="°" trend="位于设备正前方" tone="violet" /></div>
      <div className="two-column sensor-layout">
        <Card><SectionTitle index="01" title="24 小时环境趋势" /><div className="sensor-chart">{bars.map((height, index) => <span key={index} style={{ height: `${height}%` }} title={`${index}:00`} />)}</div><div className="chart-legend"><span><i className="blue" />环境光</span><span><i className="orange" />温度</span><span>00:00</span><span>12:00</span><span>现在</span></div></Card>
        <Card><SectionTitle index="02" title="自动调节" /><SettingRow icon={Sun} title="屏幕自动亮度" description="根据环境光调节桌宠屏幕亮度"><Toggle checked={autoBrightness} onChange={(value) => updateSensors({ autoBrightness: value })} /></SettingRow><SettingRow icon={User} title="面向用户" description="根据方向传感器或视觉模块转向用户"><Toggle checked={faceTracking} onChange={(value) => updateSensors({ faceTracking: value })} /></SettingRow><SettingRow icon={Temperature} title="温湿度提醒" description="超出舒适范围时显示提醒表情"><Toggle checked onChange={() => notify("温湿度提醒已保持开启")} /></SettingRow><Notice tone="info" title="人脸方向检测建议">单独使用红外距离传感器难以区分人脸和手部。后续可选用摄像头视觉模块，或使用左右两组 ToF / PIR 做粗略方向判断。</Notice></Card>
      </div>
    </div>
  );
}

export function SettingsPage({ notify }) {
  const { state, patch, reset, replace, exportConfig } = useAppStore();
  const [section, setSection] = useState("input");
  const operation = state.settings.operation;
  const format = state.settings.formatting;
  const theme = state.settings.theme;
  const floating = state.settings.floating;
  const updateSettings = (value) => patch({ settings: { ...state.settings, ...value } });
  const downloadConfig = () => { const blob = new Blob([exportConfig()], { type: "application/json" }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "deskmate-config.json"; link.click(); URL.revokeObjectURL(link.href); notify("配置 JSON 已导出"); };
  const importConfig = (event) => { const file = event.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => { try { replace(JSON.parse(reader.result)); notify("配置已导入"); } catch (error) { notify(`导入失败：${error.message}`); } }; reader.readAsText(file); event.target.value = ""; };
  return (
    <div className="page">
      <PageIntro title="设置与诊断" description="管理快捷键、输入方式、外观和系统诊断" actions={<><Button icon={Upload} onClick={() => document.getElementById("config-import").click()}>导入配置</Button><input id="config-import" type="file" accept="application/json" hidden onChange={importConfig} /><Button icon={Download} onClick={downloadConfig}>导出配置</Button><Button icon={Refresh} onClick={() => { reset(); notify("设置已恢复为默认值"); }}>恢复默认</Button></>} />
      <div className="settings-layout">
        <Card className="settings-nav">{[{ id: "input", icon: Keyboard, label: "输入与快捷键" }, { id: "format", icon: Book2, label: "文字整理" }, { id: "appearance", icon: Sun, label: "外观与悬浮窗" }, { id: "account", icon: User, label: "账户" }, { id: "diagnostics", icon: Gauge, label: "系统诊断" }].map((item) => <button className={section === item.id ? "is-active" : ""} onClick={() => setSection(item.id)} key={item.id}><item.icon size={19} /><span>{item.label}</span><ArrowRight size={16} /></button>)}</Card>
        <Card className="settings-panel">
          {section === "input" && <><SectionTitle index="01" title="快捷键" /><SettingRow title="语音输入快捷键" description="按此快捷键开始或结束语音输入"><div className="key-sequence"><Keycap>Ctrl</Keycap><Keycap>Shift</Keycap><Keycap>Space</Keycap></div></SettingRow><SettingRow title="语音编辑快捷键" description="选中文字后说出修改要求"><div className="key-sequence"><Keycap>Ctrl</Keycap><Keycap>Shift</Keycap><Keycap>E</Keycap></div></SettingRow><SettingRow title="快捷键操作方式" description="语音输入和语音编辑共同使用"><Segmented compact value={operation} onChange={(value) => updateSettings({ operation: value })} options={[{ value: "hold", label: "按住说话" }, { value: "toggle", label: "按一下开始" }]} /></SettingRow></>}
          {section === "format" && <><SectionTitle index="02" title="文字整理" /><SettingRow title="整理方式" description="所有方式都以不改变原意为前提"><Segmented value={format} onChange={(value) => updateSettings({ formatting: value })} options={[{ value: "raw", label: "原样输出" }, { value: "smart", label: "智能整理" }, { value: "custom", label: "自定义" }]} /></SettingRow><SettingRow title="标点格式" description="仅调整语音编辑结果的标点"><Select value="智能默认"><option>智能默认</option><option>中文标点</option><option>英文标点</option></Select></SettingRow><Notice tone="success" title="当前规则">{format === "raw" ? "保留识别结果，只应用词库纠错。" : format === "smart" ? "自动修正口误、适当分段并精简重复表达。" : "使用你保存的自定义提示词整理文字。"}</Notice></>}
          {section === "appearance" && <><SectionTitle index="03" title="外观与悬浮窗" /><SettingRow title="外观" description="跟随系统外观，或手动固定亮色 / 暗色"><Segmented value={theme} onChange={(value) => updateSettings({ theme: value })} options={[{ value: "system", label: "跟随系统" }, { value: "light", label: "亮色" }, { value: "dark", label: "暗色" }]} /></SettingRow><SettingRow title="悬浮窗显示" description="录音时显示状态和实时识别文字"><Toggle checked={floating} onChange={(value) => updateSettings({ floating: value })} /></SettingRow><SettingRow title="背景不透明度" description="数值越高，悬浮窗背景越实"><Slider label="背景不透明度" value={70} /></SettingRow></>}
          {section === "account" && <><SectionTitle index="04" title="账户" /><div className="account-card"><span className="avatar"><User size={28} /></span><div><strong>DeskMate Demo 用户</strong><p>本地演示账户 · 不上传私人记录</p></div><StatusBadge tone="success">已登录</StatusBadge></div><SettingRow title="当前方案" description="Demo 版本开放全部界面功能"><span className="plan-pill">原型体验版</span></SettingRow><Button variant="ghost" icon={Lock}>隐私与数据说明</Button></>}
          {section === "diagnostics" && <><SectionTitle index="05" title="系统诊断" /><div className="diagnostic-list">{[["桌面应用运行", true], ["语音服务", true], ["USB HID 键盘", true], ["键盘网络音频", false], ["桌宠串口协议", false], ["AI 状态适配器", false]].map(([label, ok]) => <div key={label}><span>{ok ? <Check size={18} /> : <AlertCircle size={18} />}</span><strong>{label}</strong><StatusBadge tone={ok ? "success" : "demo"}>{ok ? "正常" : "待接入"}</StatusBadge></div>)}</div><Button icon={CloudDownload} onClick={() => notify("诊断报告已生成（演示）")}>导出诊断报告</Button></>}
        </Card>
      </div>
    </div>
  );
}
