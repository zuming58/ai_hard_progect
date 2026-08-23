# DeskMate / EasyInput 台式机续开发交接（2026-08-23）

本文汇总从 Phase 3B 交接后，在当前电脑完成的 Phase 3C 无硬件代码先行和 Phase 3D 真机稳定性准备。原台式机后续开发应以远程分支和提交为准，不要从 `release/`、聊天记录或本机未提交目录复制源码。

## 1. 远程基线

- 仓库：`https://github.com/zuming58/ai_hard_progect`
- 当前交接分支：`codex/easyinput-phase3d-hardware-acceptance`
- Phase 3C 提交：`23bbb0d696365502813648509f47c839898b8b6e`
- Phase 3D 实现提交：`54f705b3c8ecda187fb46686883c5a15b379f660`
- Phase 3B 基线：`origin/codex/easyinput-phase3b-productization`
- 桌面应用目录：`deskmate-ui-demo/`

当前仓库只配置了名为 `origin` 的 GitHub 远程，没有 GitLab 远程。若后续必须同步到 GitLab，应由项目所有者提供明确的 GitLab 仓库 URL 和授权方式，再增加独立远程；不要猜测地址或覆盖 `origin`。

## 2. Phase 3C 已完成内容

### 协议无关的局域网音频边界

- 新增 `EasyInputLanAudioAdapter`，通过可注入 `transportFactory` 隔离未知的真实传输协议。
- 状态包含 unavailable、discovering、connecting、streaming、reconnecting、error、closed。
- 默认无真实 transport 时返回 `protocol-unconfirmed`，不会扫描、广播或连接未知 IP/端口。
- 支持 PCM S16LE/F32LE 格式声明、采样参数校验、单帧大小和会话总量限制。
- 使用有限帧队列，统计重复、乱序、迟到、缺失和丢弃帧。
- 支持取消、`AbortSignal`、幂等停止和有限次数指数退避重连。
- 诊断只包含状态和计数，不包含音频内容、IP、MAC、SSID 或设备路径。

### 脱敏网络诊断

- Electron 主进程新增安全 IPC `desktop:get-network-summary`。
- preload 只暴露 `getNetworkSummary()`，继续保持 `nodeIntegration: false` 和 `contextIsolation: true`。
- 返回内容仅包含网络是否可用、ethernet/wifi/unknown 类别、同局域网可能性和 `protocol-unconfirmed`。
- 设置与连接页面展示脱敏摘要，不把“网络可用”描述成“板载麦克风已连接”。

### AI 状态和桌宠意图

- 新增版本化 AI 事件模型和纯 reducer，状态包括 offline、idle、listening、thinking、working、waiting、completed、error。
- 过滤非法事件、重复事件、乱序序号和旧会话事件，并支持 provider 断开。
- 建立表情、动作、屏幕亮度、注意力意图映射及优先级。
- Codex、Claude Code、Hermes、Workbody 仅提供集中 mock provider，没有宣称真实连接。
- UI 明确标注模拟数据，意图层不会调用屏幕、灯效、舵机或传感器硬件。

### Phase 3C 主要文件

- `deskmate-ui-demo/src/adapters/easyInputLanAudioAdapter.js`
- `deskmate-ui-demo/electron/network-summary.cjs`
- `deskmate-ui-demo/src/domain/aiStatus.js`
- `deskmate-ui-demo/src/domain/petIntent.js`
- `deskmate-ui-demo/src/adapters/mockAgentProviders.js`
- `deskmate-ui-demo/tests/phase3c-code-first.test.mjs`
- `docs/PHASE3C_CODE_FIRST_STATUS.md`

## 3. Phase 3D 已完成内容

### 真机只读证据

- Windows 已识别 EasyInput `VID 303A / PID 1006`。
- 可见 HID 键盘、鼠标和厂商自定义 HID 集合，设备状态为 OK。
- 自包含 Raw Input 输入桥返回 `boardConnected: true`。
- 只读诊断捕获到当前板子语音键发送的真实组合键为 `Ctrl + Shift + Space`，包含完整按下和释放事件。
- F22 路径继续作为兼容入口保留，不再把它描述成当前板子的唯一真实按键。
- 没有向 HID 写数据，没有烧录、擦除、修改固件、分区或 eFuse。

### 已跑通的语音链路

当前已由用户现场确认：

```text
EasyInput Ctrl+Shift+Space 语音键
  → Electron 全局快捷键
  → 与页面按钮/F22 兼容入口共用的录音状态机
  → 电脑麦克风
  → 千问 qwen3-asr-flash
  → 历史记录
  → 剪贴板输出
```

- 用户首次测试时因未配置 API Key 无法识别。
- 在设置页通过 Windows 当前用户加密方式配置百炼 API Key 后，用户确认可以识别。
- API Key 未被读取、输出、写入诊断、配置导出或 Git。
- 系统没有枚举 EasyInput 对应的 USB Audio 麦克风端点，当前录音仍来自电脑麦克风。

### Phase 3D 加固

- 更新连接页、设置页、侧栏和主交接文档：当前语音键为 `Ctrl+Shift+Space`，F22 为兼容路径。
- 新增测试，确认全局快捷键和 F22 使用相同的版本化 voice-toggle 契约。
- 新增 STT 失败先保存历史、取消处理不输出的回归测试。
- 保留现有释放触发、防抖、重复事件过滤、断线复位和输入桥崩溃重启逻辑。

### Phase 3D 主要文件

- `deskmate-ui-demo/src/App.jsx`
- `deskmate-ui-demo/src/pages.jsx`
- `deskmate-ui-demo/tests/phase3d-hardware-acceptance.test.mjs`
- `docs/PHASE3D_HARDWARE_ACCEPTANCE_STATUS.md`
- `docs/HARDWARE_CONNECTIVITY_STATUS.md`
- `docs/PHASE3_VOICE_LOOP_ACCEPTANCE.md`

## 4. 保持不变的既有能力

本轮没有破坏或替换以下 Phase 3B 能力：

- Electron 安全桌面壳和 preload/IPC 来源校验。
- F22、`Ctrl+Shift+Space`、页面按钮和系统托盘共用语音状态机。
- 电脑麦克风、音量波形、录音计时、试听和实时字幕。
- 千问 `qwen3-asr-flash` 和 `qwen3.7-flash` 智能/自定义整理。
- raw、smart、custom 三种整理模式及失败保留原文。
- 历史 schema v5、录音先保存、剪贴板和当前窗口回退。
- 正式图标、系统托盘、输入桥自包含打包和 Sites 构建。

## 5. 最后一次验证结果

在 `deskmate-ui-demo/` 执行：

- `npm ci --include=dev`：通过，安装 398 个包。当前机器 npm 全局设置偏向 production，因此显式包含 devDependencies。
- `npm test`：通过，60/60。该命令内部也执行 Vite/Sites 构建。
- `npm run build`：通过。
- `npm run test:sites`：通过，4/4。
- `npm run build:desktop`：通过，生成 `release/win-unpacked/DeskMate.exe`。
- `DeskMate.exe --deskmate-smoke-test`：退出码 0；模拟语音键、Mock STT、历史和剪贴板闭环通过。
- 打包程序实际启动：通过，主窗口不是白屏。

第一次执行 `build:desktop` 时，正在运行的 DeskMate 锁住 `release/win-unpacked`，出现 EBUSY；关闭运行中的 DeskMate 后重跑成功。这不是源码或构建配置失败。

## 6. 原台式机接手步骤

### 已有仓库

先确保原台式机自己的未提交改动已保存到独立分支或提交，然后执行：

```powershell
cd <原台式机仓库路径>
git status
git fetch origin
git switch -c codex/easyinput-desktop-continue origin/codex/easyinput-phase3d-hardware-acceptance
cd deskmate-ui-demo
npm ci --include=dev
npm test
npm run build:desktop
.\release\win-unpacked\DeskMate.exe
```

若本地已经存在 `codex/easyinput-desktop-continue`，不要再次 `-c`；切换后执行 `git pull --ff-only`。不要在 Phase 3D 交接分支上强推。

### API Key

- 百炼 API Key 使用 Windows 当前用户范围加密，不通过 Git 同步。
- 原台式机若原来已经配置且仍为同一 Windows 用户，可先检查“设置诊断 → 账户 → 千问服务”的已配置状态。
- 若未配置，在应用内重新输入；不要复制本机加密文件，不要把 Key 写进文档、命令、日志或聊天。

### 真机复验

1. 确认“设备与连接”显示输入桥运行、EasyInput HID 已连接。
2. 确认当前板子语音键 `Ctrl+Shift+Space` 第一次开始、第二次停止。
3. 连续完成 10 次短录音，记录成功/失败计数，不记录识别正文。
4. 分别验证取消、麦克风拒绝、麦克风拔出、板子拔插、最小化到托盘。
5. 在记事本、浏览器或 Codex 输入框验证当前窗口输出；焦点变化时应保留历史并回退剪贴板。
6. 导出脱敏诊断，确认不包含 API Key、音频、文本、IP、MAC、SSID、窗口标题或完整设备路径。

## 7. 明确未完成和风险

- 10 次连续真实录音尚未由当前电脑完整计数验收。
- 拒绝麦克风权限、拔出麦克风、录音中拔板、托盘和当前窗口输出矩阵仍需原台式机逐项人工确认。
- 板载麦克风没有 USB Audio 端点，真实局域网音频协议仍未确认。
- 未得到真实协议前，不扫描局域网、不猜测 IP/端口/帧格式、不显示“板载麦克风已连接”。
- 真实 Codex、Claude Code、Hermes、Workbody provider 尚未接入；现有 provider 是 mock。
- 桌宠屏幕、灯效、舵机、相机和传感器没有接入，不得依据意图映射宣称硬件已工作。
- 当前板子发 `Ctrl+Shift+Space`，可能与其他软件全局快捷键冲突；冲突时应用会保留原快捷键并显示注册失败原因。

## 8. 本机工作区边界

提交 Phase 3D 后，本机工作区仍有其他任务产生的未提交资料，包括根 README、`参考仓库/`、课程资料、固件研究和流程目录。它们没有包含在 Phase 3C/3D 软件提交中，也没有在本次 DeskMate 交接中擅自暂存。

原台式机从远程 Phase 3D 分支拉取时不会获得这些未提交内容。若这些资料也需要跨电脑同步，应先由其所属任务单独审计、独立提交，不要与 DeskMate 软件交接混在一个提交中。

## 9. 安全红线

- 不提交 API Key、Token、账号、Wi-Fi 密码、真实 IP、录音或识别正文。
- 不向未知 HID 接口发送随机数据。
- 不烧录、不擦除、不改分区、不写 eFuse。
- 不恢复重复的 VoiceWorkflow 实现，不绕过 Electron 安全校验。
- 不提交 `node_modules`、`dist`、`release` 或本机临时日志。
- 不直接向 main 或旧交接分支强推；原台式机使用新的 `codex/` 分支继续开发。
