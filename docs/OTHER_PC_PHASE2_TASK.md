# DeskMate / EasyInput 第二阶段软件开发交接

更新时间：2026-08-21
仓库：`https://github.com/zuming58/ai_hard_progect`
开发基线：`origin/codex/easyinput-app-integration`
基线合并提交：`8b8d136b1593f54c8e8a59cceaf23e98d2551503`

## 1. 这台电脑没有板子，能开发什么

可以开发本阶段绝大多数软件工作。采用“设备模拟器 + 适配器接口 + 自动化测试”完成软件闭环，回到连接真实板子的台式电脑后只替换协议适配器并做最终验收。

可以在无板电脑完成：

- 录音状态机、录音文件保存、历史记录和错误恢复。
- 设备按键事件模拟、按下开始/再次按下结束的完整流程。
- STT（语音转文字）供应商无关接口、Mock 实现和可配置 HTTP 实现。
- 原样输出、智能整理、自定义整理的管线与失败降级。
- 历史、剪贴板和安全的原输入窗口输出策略。
- 设备连接状态模型、诊断信息导出、超时和断线状态。
- Electron、Web 模式和自动化测试。

无板电脑不能声称完成：

- EasyInput 实际语音按键或组合键确认。
- `VID_303A / PID_1006` 厂商 HID 报告格式解析。
- 板子 2.4GHz Wi-Fi 麦克风的发现、握手、音频编码和分包协议。
- 屏幕、灯效、舵机、温湿度、光线传感器的真实控制。
- 真实板子端到端验收。

这些项目必须保留“待接入 / 模拟器”标识，不能用 Mock 结果冒充硬件已接通。

## 2. 本阶段目标

在不连接板子的电脑上完成一条可重复测试的软件链路：

```text
设备模拟按键
  -> 开始 / 结束录音
  -> 保存音频 Blob
  -> STT 适配器
  -> 文字整理
  -> 历史记录
  -> 剪贴板或受保护的原输入窗口
```

真实硬件接入时，只需要把模拟设备事件和模拟音频源替换为 EasyInput 协议适配器，不重写页面和业务状态机。

## 3. 必做任务

### A. 统一设备事件模型

新增版本化的设备事件定义，建议最低字段：

```js
{
  version: 1,
  type: "voice-toggle" | "key-diagnostic" | "connection-change" | "audio-status",
  source: "simulator" | "global-shortcut" | "easyinput",
  deviceId: "string-or-null",
  at: "ISO-8601",
  payload: {}
}
```

要求：

- 页面只能订阅统一事件，不直接依赖 Electron IPC、Web API 或未来硬件协议。
- 非法版本、未知事件和畸形数据必须被拒绝或安全忽略。
- 事件源必须显示为“模拟器 / 桌面快捷键 / EasyInput”，便于以后诊断。

### B. 开发模式设备模拟器

实现仅在开发或诊断模式可用的模拟器：

- 模拟“按一下开始，再按一下结束”。
- 模拟连续快速按键，验证防抖。
- 模拟断线、重连和事件重复。
- 可选择本地音频测试文件，或继续使用电脑麦克风。
- UI 明确显示“模拟器”，正式构建默认关闭模拟控制入口。
- 不新增一套独立录音逻辑，必须调用当前 `VoicePage` 正在使用的状态机。

### C. STT 适配器层

保留 `voiceAdapters.stt.transcribe(blob, options)` 作为业务入口，拆分：

- `MockSttAdapter`：测试时返回确定文本。
- `HttpSttAdapter`：连接用户配置的转写服务端点。
- 未配置服务时返回 `pending/unconfigured`，不能伪造识别结果。

统一结果：

```js
{
  status: "success" | "pending" | "error" | "cancelled",
  text: "",
  provider: "mock-or-provider-id",
  durationMs: 0,
  message: ""
}
```

要求：

- 支持 `AbortSignal`、请求超时、单次安全重试和取消。
- 限制音频文件大小，返回中文可理解错误。
- STT 失败时仍保留本地录音和历史记录。
- 不把 API Key、Token、账户、固定局域网 IP 提交到 Git。
- 供应商尚未确定，不要把业务层写死到某一家服务。

### D. 文字整理与输出管线

- `raw`：保持原意，只做词库替换和必要标点。
- `smart`：通过可替换的整理适配器处理；未配置服务时安全退回 `raw`。
- `custom`：读取用户本地规则；没有规则时提示并退回 `raw`。
- 输出失败不能删除历史和原始转写。
- 原输入窗口输出继续遵守当前安全限制：焦点窗口变化时拒绝粘贴。

### E. 诊断与可交接证据

在“设置诊断”或现有设备连接页补充最小诊断能力：

- 当前运行模式：Web / Electron。
- 全局快捷键及注册结果。
- 麦克风权限和选中设备。
- 设备事件源及最后一次事件时间。
- STT 适配器状态、最近一次耗时和错误类型。
- LAN 音频保持 `protocol-unconfirmed`，不要伪造连接。
- 导出脱敏诊断 JSON；不得包含录音正文、Wi-Fi 密码、Token 和完整本地路径。

## 4. 测试要求

至少增加以下自动化覆盖：

1. 模拟器触发开始/结束，生成一条录音历史。
2. 连续重复事件不会启动两个 `MediaRecorder`。
3. Mock STT 成功后，文字进入历史。
4. STT 超时、取消、错误时，录音仍被保留。
5. `raw/smart/custom` 的降级行为。
6. 未配置真实服务时不能显示“已接通”。
7. 配置迁移：旧版本数据打开后不白屏。
8. Electron 桌面桥不可用时 Web 模式安全降级。
9. 诊断导出内容已脱敏。

完成前必须运行：

```powershell
npm ci
npm test
npm run build
npm run build:desktop
```

并实际启动 `release/win-unpacked/DeskMate.exe`，确认不是白屏。

## 5. 禁止事项

- 不大改现有 UI 风格、导航结构和视觉规范。
- 不删除或绕过现有 Electron 安全校验。
- 不恢复已经移除的重复 `VoiceWorkflow` 业务实现。
- 不提交 `node_modules`、`dist`、`release`、录音文件、账号或密钥。
- 不硬编码本地路径、用户邮箱、Wi-Fi 密码或 `192.168.x.x` 地址。
- 不反编译或覆盖当前正常工作的板子固件。
- 不实现尚未确认协议的灯效、屏幕、舵机命令。

## 6. Git 操作

在另一台电脑执行：

```powershell
git clone https://github.com/zuming58/ai_hard_progect.git
cd ai_hard_progect
git fetch origin
git switch -c codex/easyinput-phase2-software origin/codex/easyinput-app-integration
cd deskmate-ui-demo
npm ci
npm test
```

完成后：

```powershell
git status
git add -- <本次明确修改的文件>
git commit -m "Implement EasyInput software integration simulator"
git push -u origin codex/easyinput-phase2-software
```

不要直接向 `main` 或 `codex/easyinput-app-integration` 推送。

## 7. 回传格式

```text
分支：
提交哈希：
实现内容：
主要变更文件：
测试命令与结果：
桌面打包及启动结果：
模拟器演示步骤：
已知限制：
仍需真实板子确认的项目：
需要本机审计的风险点：
```

## 8. 回到有板电脑后的验收清单

另一台电脑完成后，本机只做真实硬件补充验收：

1. 实际按每个板子按键，记录真实键值和组合键。
2. 对照事件诊断确认语音键能触发同一录音状态机。
3. 确认台式机网线和板子 2.4GHz Wi-Fi 位于同一局域网。
4. 在获得协议资料或授权抓包后确认音频发现、端口、编码和分包。
5. 用真实板子完成“按键 -> 录音 -> 转写 -> 历史/输入框”端到端测试。
