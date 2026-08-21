# 另一台电脑任务书：Phase 3C 无硬件代码先行

## 1. 目标

在没有 EasyInput 键盘、没有真实板载麦克风协议、没有用户百炼 API Key 的电脑上，把下一阶段所有可安全完成的代码、模拟器、自动化测试和文档先做完。最终真实 HID、局域网音频和账号验收由插有键盘的笔记本完成。

本任务不是“猜一个协议让页面看起来已连接”，而是建立有证据后可快速接入的稳定边界。

## 2. 基线与分支

- 仓库：`https://github.com/zuming58/ai_hard_progect`
- 基线：`origin/codex/easyinput-phase3b-productization`
- 新分支：`codex/easyinput-phase3c-code-first`
- 工作目录：`deskmate-ui-demo/`

开始前执行：

```powershell
git fetch origin
git switch -c codex/easyinput-phase3c-code-first origin/codex/easyinput-phase3b-productization
cd deskmate-ui-demo
npm ci
npm test
npm run build
```

先阅读：

1. `AGENTS.md`
2. `docs/MASTER_HANDOFF_2026-08-22.md`
3. `docs/PHASE3B_PRODUCTIZATION_STATUS.md`
4. `docs/EASYINPUT_AUDIO_PROTOCOL_REPORT.md`
5. `docs/HARDWARE_CONNECTIVITY_STATUS.md`
6. 本任务书

## 3. 不得破坏的现有能力

- F22、`Ctrl+Shift+Space`、页面按钮共用的语音状态机。
- 电脑麦克风录音和实时滚动字幕。
- `qwen3-asr-flash` 转写、`qwen3.7-flash` 整理、安全回退和历史 schema v5。
- Windows 托盘、正式图标、目标窗口输出和剪贴板回退。
- 未来硬件功能必须显示为“待接入/协议未确认”，不能显示假连接。

## 4. P1：局域网音频适配层

将当前 `EasyInputLanAudioAdapter` 的占位逻辑整理为可测试、可注入传输层的独立模块，建议位置：

- `src/adapters/easyInputLanAudioAdapter.js`
- `src/adapters/lanAudio/` 下的协议无关组件

要求：

- 定义明确状态：`unavailable`、`discovering`、`connecting`、`streaming`、`reconnecting`、`error`、`closed`。
- 未注入已确认协议传输时必须返回 `protocol-unconfirmed`，不能对外宣称连接成功。
- 传输层通过接口/工厂注入；生产默认实现仍不可用，测试实现只喂入合成 PCM/帧数据。
- 支持 `AbortSignal`、显式关闭、幂等停止和会话资源释放。
- 实现有上限的帧缓冲或抖动队列，不允许无限积压内存。
- 处理序号、重复帧、乱序、丢帧和迟到帧，并输出不含正文的统计信息。
- 为重连实现有上限的指数退避和最大次数；用户取消后不得继续重连。
- 对单帧大小、总会话字节数、采样参数和无法识别的帧做边界校验。
- 输出统一的音频块/状态事件，使现有录音管线未来可以替换电脑麦克风而无需重写页面。
- 不把合成音频写进用户真实历史；测试使用内存适配器。

建议的协议无关接口至少覆盖：

- `discover(options)`
- `connect(candidate, options)`
- `startStream(options)`
- `stop(reason)`
- `subscribe(listener)`
- `getDiagnostics()`

具体命名可按现有代码风格调整，但要保持职责等价。

## 5. P2：网络能力与脱敏诊断

增加只读的网络环境摘要，为未来同局域网验证提供信息，但不得泄露敏感网络数据。

要求：

- Electron 主进程只返回能力类别，例如是否存在可用网卡、`ethernet/wifi/unknown`、局域网音频是否仍为协议未确认。
- 不向渲染进程和诊断导出暴露 IP、MAC、SSID、网关、完整网卡名称或设备路径。
- 网线电脑要被描述为“可能具备同局域网条件”，不能错误提示“必须使用 Wi-Fi”。
- UI 清楚区分：
  - 电脑网络可用性。
  - 键盘是否已配置网络。
  - 板载音频协议是否确认。
- 没有键盘时显示“等待真机验证”，不能使用绿色已连接状态。
- 脱敏测试必须覆盖 IPv4、IPv6、MAC、SSID、设备路径和窗口标题样本。

## 6. P3：AI 状态与桌宠意图引擎

先实现与硬件无关的纯状态层，为后续 Codex、Claude Code、Hermes、Workbody 接入准备统一模型。

要求：

- 定义版本化的规范事件，例如：
  - `version`
  - `provider`
  - `sessionId`（本地短期 ID）
  - `state`
  - `activity`
  - `progress`（可选）
  - `time`
  - `sequence`
- 首批统一状态：`offline`、`idle`、`listening`、`thinking`、`working`、`waiting`、`completed`、`error`。
- 实现纯 reducer/状态机，处理乱序事件、重复事件、旧会话事件和 provider 断开。
- 建立桌宠意图映射，而不是直接调用硬件：
  - `faceExpression`
  - `motionIntent`
  - `screenBrightnessIntent`
  - `attentionIntent`
- 规定优先级与恢复行为，例如错误、等待用户、倾听、工作、完成、空闲之间如何抢占和回落。
- 提供 Codex、Claude Code、Hermes、Workbody 的 mock provider/fixtures，只用于 Demo 和测试。
- 页面必须明确标注模拟数据；没有真实 provider 时不能显示“已连接”。
- 不调用或控制屏幕、灯、舵机、相机、传感器。

## 7. P4：自动化、构建和文档

至少覆盖以下测试：

### 局域网音频适配器

- 未确认协议默认不可用。
- 正常帧流、重复帧、乱序、丢帧、超大帧和会话上限。
- 取消、关闭、连接失败、重连上限和重连期间取消。
- 多次 start/stop 不泄漏监听器或定时器。
- 诊断不包含音频内容、IP、MAC、SSID 和设备路径。

### AI 状态引擎

- 合法/非法事件校验。
- 重复、乱序、旧会话事件。
- provider 切换、断开、错误、完成后回到空闲。
- 表情/动作意图优先级。
- mock 状态与真实连接状态在 UI 中不混淆。

### 回归与构建

必须运行：

```powershell
npm test
npm run build
npm run test:sites
npm run build:desktop
```

如果打包所需的 .NET 8 SDK 缺失，先按项目现有说明安装或使用已有自包含产物构建路径；若最终仍无法执行，交付报告必须写清环境原因，不能写“通过”。

同时更新：

- `docs/EASYINPUT_AUDIO_PROTOCOL_REPORT.md`：只写新增的软件边界，协议仍标注未确认。
- 新增 `docs/PHASE3C_CODE_FIRST_STATUS.md`：列出完成项、测试、未验证项和真机验收步骤。
- 必要时更新主交接文档链接，但不要把“待真机验证”改成“已完成”。

## 8. 明确禁止

- 不猜测、硬编码或扫描未知 IP、端口、广播包、WebSocket 地址和音频包格式。
- 不抓取用户网络流量，不主动扫描局域网，不要求关闭防火墙。
- 不烧录、读取或修改固件。
- 不向未知 HID/USB 接口写数据。
- 不伪造板载麦克风、AI 工具或未来硬件已连接。
- 不索要、不提交真实 API Key；测试只使用 mock。
- 不提交 `node_modules`、`dist`、`release`、录音、历史、密钥和本地日志。
- 不重写已经通过真机验证的 F22/ASR/悬浮条闭环，除非有失败测试证明必须修改。

## 9. 完成标准

- P1 至 P4 所有不依赖硬件的内容完成。
- 新模块具有明确接口、边界限制、取消语义、脱敏诊断和自动化测试。
- 没有任何 UI 或日志把 mock/unknown 显示成真实连接。
- 所有可运行测试和构建通过。
- 分支已提交并推送到 `origin/codex/easyinput-phase3c-code-first`。
- 工作区干净。

## 10. 返回报告格式

完成后只需返回：

```text
分支：
最新提交：
已推送：是/否

实现内容：
- （填写）

主要文件：
- （填写）

测试结果：
- npm test：
- npm run build：
- npm run test:sites：
- npm run build:desktop：

明确未验证：
- EasyInput 真机 HID/F22：待有键盘电脑验收
- 板载麦克风真实协议：未确认
- 真实 AI provider：本阶段未接入

风险与下一步真机操作：
- （填写）
```
