# 另一台电脑开发任务：EasyInput 板子与 DeskMate 语音链路

## 分支

从审计修复分支创建：

```powershell
git fetch origin
git switch -c codex/easyinput-app-integration origin/codex/software-mvp-audit-fixes
```

开始前阅读：

- `docs/COLLABORATION_HANDOFF.md`
- `docs/HARDWARE_CONNECTIVITY_STATUS.md`
- `deskmate-ui-demo/AGENTS.md`

## 目标

让现有 EasyInput 板子的按键能够驱动 DeskMate 的录音界面，并建立后续接入板子 Wi-Fi 麦克风、真实转写与系统文字输出所需的桌面桥和适配器。

本轮不开发未来桌宠的屏幕、灯效、舵机或传感器控制。

## 必须完成

### A. Windows 桌面运行时

1. 在现有 React/Vite 项目外增加轻量桌面壳。优先采用 Electron；若选择 Tauri，必须在报告中说明维护和打包收益。
2. 使用安全 preload + IPC：关闭 `nodeIntegration`，启用 `contextIsolation`，渲染进程不能直接访问 Node API。
3. 提供统一 `DesktopBridgeAdapter`，Web 环境下自动退化为 unavailable/mock，不让页面白屏。
4. 增加开发启动、生产构建和 Windows 打包命令；`npm test`、`npm run build` 仍须可在全新克隆中运行。

### B. 板子按键触发录音

1. 实现用户可配置的全局语音快捷键，默认 `Ctrl+Shift+Space`。
2. 桌面桥收到快捷键后向 React 发送 `voice-toggle` 事件：
   - 空闲时开始录音；
   - 录音时结束录音；
   - 权限拒绝或设备不可用时显示明确错误。
3. 页面手动按钮与板子/全局快捷键必须调用同一套录音状态机，禁止维护两套逻辑。
4. 增加“按键诊断”模式，只记录按键名称、修饰键和时间，不记录用户输入内容；用于确认板子语音键实际发送的组合键。
5. 不要声称能区分普通键盘和 EasyInput HID，除非已通过厂商自定义 HID 接口或桌面原生 API 得到设备来源证据。

### C. 录音、转写与输出管线

实现可测试的统一管线：

```text
VoiceTriggerAdapter
  → RecorderService
  → SttAdapter
  → TextOrganizerAdapter
  → HistoryStore
  → TextOutputAdapter
```

要求：

1. 将现有 `useRecorder` 的开始/停止能力抽成可被 UI 和桌面事件共同调用的服务或控制器。
2. 保留现有 IndexedDB 录音 Blob 持久化；失败时不得丢失整条历史元数据。
3. 建立 `SttAdapter` 接口与 mock/test 实现；没有用户确认的 API/密钥时，不得把假文本标成真实转写。
4. `TextOutputAdapter` 至少支持：
   - 仅保存到历史；
   - 复制到剪贴板；
   - 用户启用后粘贴到当前 Windows 输入框。
5. 剪贴板与模拟粘贴必须有开关、可见状态和失败回退；失败时文字仍保留在历史中。

### D. 板子麦克风的证据与边界

1. 本机已确认 EasyInput 为 `VID 303A / PID 1006` 的 HID 设备，但没有对应 USB Audio 输入端点。
2. 新增 `EasyInputLanAudioAdapter` 接口和未配置实现，不得在未知协议上伪造“键盘麦克风已连接”。
3. 如能在用户自己的电脑与板子上安全验证原 EasyInput 软件，只做只读网络观察，输出 `docs/EASYINPUT_AUDIO_PROTOCOL_REPORT.md`：
   - 使用 TCP、UDP、WebSocket 还是 HTTP；
   - 连接由板子还是电脑发起；
   - 端口、握手、帧边界、编码/采样率的证据；
   - 报告内必须把真实 IP、Wi-Fi、Token、账号、序列号与音频内容脱敏。
4. 如果无法确认协议，明确报告“板子麦克风待协议资料”，但仍要完成板子快捷键 + 电脑麦克风的可测试链路。

### E. UI 与诊断

1. “设备与连接”页分开显示四个真实状态：
   - 板子/HID 触发；
   - 当前录音来源；
   - STT 服务；
   - 文字输出方式。
2. 语音页收到板子触发时要有与手动按钮一致的录音、声波、计时和错误反馈。
3. 增加脱敏诊断导出，不包含密码、Token、IP、序列号和语音文本。
4. 不改变已确认的亮色主界面、深灰侧栏与青蓝视觉语言。

### F. 测试与人工验收

自动化测试至少覆盖：

- 全局快捷键开始/停止共用同一录音状态机；
- 重复快捷键、防抖和录音中的设备断开；
- 麦克风权限拒绝；
- STT 成功、失败、超时；
- 历史保存与音频 Blob 丢失回退；
- 剪贴板/粘贴失败时文字不丢失；
- Web 无桌面桥时安全降级；
- 配置导入导出兼容旧版本。

人工验收分两层：

1. 无板子：真实电脑麦克风 + 键盘快捷键完整跑通。
2. 有板子：板子语音键触发同一流程；若板子麦克风协议已确认，再验证板子音频，否则使用电脑麦克风并如实标记。

## 禁止事项

- 不开发未来桌宠屏幕、灯效、舵机和传感器控制。
- 不把“Windows 识别到 HID”写成“板子麦克风已连接”。
- 不提交任何 API Key、Wi-Fi 密码、真实 IP、抓包原件、录音、账号或 Token。
- 不向未知厂商 HID 接口发送随机报告，不烧录、不擦除、不改分区、不写 eFuse。
- 不用硬编码假状态冒充真实设备或真实转写结果。

## 完成后回传

```text
分支：
提交哈希：
桌面壳与选择理由：
板子语音键实际发送的快捷键：
板子触发录音结果：
电脑麦克风录音结果：
板子麦克风协议结论：
STT 接入状态：
文字输出到历史/剪贴板/当前窗口结果：
自动化测试结果：
Windows 打包结果：
仍然缺少的资料：
需要审计的风险点：
```
