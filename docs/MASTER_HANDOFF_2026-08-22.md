# DeskMate / EasyInput 主交接文档（2026-08-22）

这份文档是当前项目的主交接入口，供台式机、笔记本和另一台开发电脑继续协作。较早的交接文档只作为历史记录；若描述冲突，以本文、当前分支代码和对应阶段状态文档为准。

## 1. 当前基线

- GitHub：`https://github.com/zuming58/ai_hard_progect`
- 当前开发分支：`codex/easyinput-phase3b-productization`
- Phase 3B 实现提交：`c76b294`
- 当前 Pull Request：`https://github.com/zuming58/ai_hard_progect/pull/9`
- PR 基线：`codex/easyinput-phase3-voice-loop`
- 桌面应用目录：`deskmate-ui-demo/`

切换电脑时，不要从聊天截图重新拼代码，也不要从打包目录复制源码；以 GitHub 上该分支的最新提交为唯一代码基线。

## 2. 已经完成的能力

### 桌面软件

- React/Vite 界面与 Electron Windows 桌面壳已经接通。
- 主要产品页面、设置、诊断、历史、设备连接、表情和未来硬件页面均已建立。
- 未来桌宠屏幕、灯效、舵机、传感器页面仍是明确的演示或待接入状态，没有伪造硬件连接。
- 主窗口关闭后可驻留系统托盘，托盘可重新打开主界面并控制语音输入。
- 正式应用图标、窗口图标、任务栏图标和托盘图标已统一为青蓝机器人脸，并带图标加载失败回退。

### EasyInput 真机按键与语音闭环

- Windows 输入桥按 `VID 303A / PID 1006` 识别 EasyInput HID，不依赖固定 COM 口或固定设备路径。
- 已确认板子的语音键通过 `F22` 触发，并支持 `Ctrl+Shift+Space` 备用快捷键。
- 语音键第一次按下开始录音，第二次按下停止；状态机、悬浮条和页面按钮共用同一录音控制器。
- 板子上的回车、退格、全选、复制、粘贴、撤销等标准键由 Windows HID 键盘路径直接生效，不需要应用逐个模拟。
- 当前录音源固定为电脑麦克风；板载麦克风的局域网音频协议尚未确认。
- 录音悬浮条位于屏幕底部中央，实时字幕向前滚动；取消、转写、整理、输出和错误状态已经接入。
- 千问 `qwen3-asr-flash` 真实语音识别已经接通。
- 识别结果先进入历史，再写入剪贴板或原目标窗口；自动输入失败时保留历史并回退剪贴板。

### Phase 3B 文本整理

- 使用同一套百炼 API Key，从 Electron 主进程调用文本模型，渲染进程无法读取密钥。
- 默认文本模型：`qwen3.7-flash`。
- 支持三种模式：
  - 原样输出：不调用文本大模型，只应用确定性替换规则。
  - 智能整理：删除口头语、无意义重复，修复明显识别错误、标点和简单分段。
  - 自定义整理：在安全整理约束内应用用户自己的要求。
- 模型失败、超时、取消、空结果或非法响应时自动保留原始转写，不阻塞历史保存。
- 历史数据已升级到 schema v5，分别保存 `rawText`、最终 `text` 和脱敏后的整理状态。

## 3. 已验证结果

Phase 3B 当前基线已经完成以下验证：

- 主测试套件：50 项通过。
- Sites 测试：4 项通过。
- Windows 桌面打包及打包产物启动冒烟测试通过。
- 使用真实百炼账号测试 `qwen3.7-flash` 整理成功，单次实测约 690 ms；网络波动时以 15 秒超时和原文回退为准。
- 台式机上 EasyInput F22 语音键、实时字幕、千问转写和文字输入已经由用户实测可用。

详细状态见：

- `docs/PHASE3B_PRODUCTIZATION_STATUS.md`
- `docs/PHASE3_VOICE_LOOP_ACCEPTANCE.md`

## 4. 关键代码地图

### Electron 与 Windows 集成

- `deskmate-ui-demo/electron/main.cjs`：窗口、托盘、IPC、全局语音入口和生命周期。
- `deskmate-ui-demo/electron/preload.cjs`：安全暴露给渲染进程的桌面接口。
- `deskmate-ui-demo/electron/input-bridge.cjs`：Windows 输入桥进程管理、事件过滤和重启。
- `deskmate-ui-demo/electron/input-bridge-protocol.cjs`：输入事件协议和校验。
- `deskmate-ui-demo/native/DeskMate.InputBridge/`：自包含 .NET 8 Raw Input 输入桥。
- `deskmate-ui-demo/electron/bailian-stt.cjs`：千问语音识别主进程调用。
- `deskmate-ui-demo/electron/bailian-organizer.cjs`：千问文本整理、超时、取消和安全回退。
- `deskmate-ui-demo/electron/credential-store.cjs`：Windows 当前用户范围的密钥加密存储。

### 前端与语音状态机

- `deskmate-ui-demo/src/App.jsx`：应用总入口和桌面事件连接。
- `deskmate-ui-demo/src/pages.jsx`：主要页面、设置、历史和诊断界面。
- `deskmate-ui-demo/src/hooks/useRecorder.js`：电脑麦克风、声波和实时识别生命周期。
- `deskmate-ui-demo/src/services/voicePipeline.js`：录音、转写、整理、历史和输出闭环。
- `deskmate-ui-demo/src/adapters/sttAdapters.js`：STT 适配器。
- `deskmate-ui-demo/src/adapters/voiceAdapters.js`：录音源与未来板载音频适配边界。
- `deskmate-ui-demo/src/store/appStore.js`：持久化设置、历史 schema 和迁移。
- `deskmate-ui-demo/src/styles.css`：主界面和悬浮条样式。

### 自动化验证

- `deskmate-ui-demo/tests/`：状态机、输入桥、千问、历史迁移、脱敏和界面逻辑测试。
- `deskmate-ui-demo/scripts/`：构建、打包和检查辅助脚本。

## 5. 换到笔记本后的操作

### 第一次拉取

在笔记本的 PowerShell 中执行：

```powershell
git clone https://github.com/zuming58/ai_hard_progect.git
cd ai_hard_progect
git fetch origin
git switch -c codex/laptop-phase3c origin/codex/easyinput-phase3b-productization
cd deskmate-ui-demo
npm ci
npm test
npm run build:desktop
```

如果仓库已经存在：

```powershell
git status
git fetch origin
git switch codex/laptop-phase3c
git pull --ff-only
cd deskmate-ui-demo
npm ci
```

建议使用当前 Node.js LTS。只有重新编译 Windows Raw Input 输入桥时才需要 .NET 8 SDK；已打包的自包含输入桥不要求最终用户另装 .NET 运行库。

### USB 键盘迁移结论

把键盘用可传数据的 USB 线插到笔记本，通常无需修改代码：

- Windows 设备实例路径、USB 拓扑和接口路径可能变化，这是正常现象。
- 当前代码按 `VID 303A / PID 1006` 与 F22 来源识别，不绑定台式机上的具体路径。
- 不需要寻找 COM 端口。
- 如果经过集线器识别不稳定，先直接插笔记本 USB 口排除供电、线材和集线器问题。
- 如果笔记本显示不同 PID，不要直接放宽过滤条件；先在“设备与连接/系统诊断”查看只读诊断，再根据证据修改。

### 必须重新配置的本机数据

百炼 API Key 采用 Windows 当前用户加密，因此不会也不应该通过 GitHub 转移。笔记本上必须在“设置与诊断 → 账户 → 千问语音识别”重新输入一次 API Key。

以下内容不会上传 GitHub：

- API Key 和系统加密凭据。
- 录音文件和录音 Blob。
- 语音历史、识别文本、剪贴板内容。
- 用户本地缓存、`node_modules`、`dist`、`release` 和临时日志。

不要把台式机的加密密钥文件直接复制到笔记本；即使复制，Windows 用户级加密也通常无法跨用户解密。

## 6. 笔记本真机验收清单

插入键盘并重新配置 API Key 后，按顺序检查：

1. “设备与连接”显示输入桥运行，EasyInput HID 已识别。
2. 板子回车、退格、全选、复制、粘贴、撤销在普通文本框中正常。
3. 按一次语音键，底部中央悬浮条立即出现并开始实时滚动字幕。
4. 再按一次语音键，进入转写；启用智能整理时继续进入整理状态。
5. 最终文字进入记事本、浏览器输入框或 Codex 输入框；历史页能同时查看原始转写与整理结果。
6. 最小化主窗口后，托盘图标清晰可见，F22 仍能触发。
7. 连续完成 10 次短录音，无重复触发、无卡键、无丢失历史。
8. 拔掉键盘或禁用麦克风时，应用安全结束或给出错误提示，不崩溃。

如果真机失败，先导出应用的脱敏诊断，不要发送 API Key、完整设备路径、窗口标题、录音或识别正文。

## 7. 当前明确边界

- 不读取、不烧录、不逆向、不修改现有产品固件。
- 不向未知 HID 接口发送命令。
- 板载麦克风的 Wi-Fi 音频协议尚未确认；当前能用的是电脑麦克风。
- 台式机走网线本身不妨碍未来局域网通信，前提是电脑与板子处于同一路由器/同一可达局域网。
- 桌宠屏幕、灯效、舵机、温湿度、环境光、人脸朝向等硬件尚未接入。
- Codex、Claude Code、Hermes、Workbody 状态目前不能描述成全部真实连接。

## 8. 下一阶段分工

### 另一台电脑：先完成无硬件代码

按 `docs/OTHER_PC_PHASE3C_CODE_FIRST_TASK.md` 执行，主要完成：

- 板载局域网音频适配器的安全架构、模拟传输、缓冲、取消、重连和测试。
- 不泄露 IP/MAC/SSID 的网络能力诊断。
- AI 工具状态的统一事件模型与桌宠意图映射，但只接 mock provider，不伪装真实连接。
- 自动化测试、文档和 Windows 构建。

可直接复制给另一台 Codex 的完整指令见：

- `docs/OTHER_PC_PHASE3C_COPY_PROMPT.md`

### 有键盘的笔记本：只负责最终真机验证

- 验证换机后的 HID/F22 兼容性。
- 记录真实 VID/PID、F22 事件和失败现象，但不记录普通键入内容。
- 将另一台电脑的无硬件分支合并后，再进行局域网协议的只读证据验证。

### 后续路线

1. Phase 3C：板载麦克风协议准备与只读验证。
2. Phase 4A：Codex、Claude Code、Hermes、Workbody 的真实状态适配。
3. Phase 4B：状态驱动桌宠表情、屏幕和动作意图。
4. 拿到可控硬件和正式协议后，再接灯效、舵机和传感器。

## 9. 协作与提交规则

- 每台电脑使用独立 `codex/` 分支，不在同一远程分支上交替强推。
- 开始工作前先 `git status` 和 `git fetch origin`。
- 只提交源码、测试、图标源文件和文档；不提交构建产物、密钥、录音或用户数据。
- 不用“硬件未在身边”作为理由伪造测试；硬件项明确写“待有键盘电脑验收”。
- 交付必须包含：分支、提交哈希、改动文件、测试命令与结果、未验证项、已推送状态。
