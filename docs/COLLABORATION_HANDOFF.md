# DeskMate 双电脑协作开发交接

更新时间：2026-08-21

## 1. 当前基线

- GitHub：`https://github.com/zuming58/ai_hard_progect`
- UI 原型基线：`codex/deskmate-ui-demo-handoff`
- 软件 MVP 实现：`codex/software-mvp-core`
- 当前审计修复与下一阶段基线：`codex/software-mvp-audit-fixes`
- 前端项目：`deskmate-ui-demo/`
- 技术栈：React 19、Vite 6、Tabler Icons
- 本地启动：在 `deskmate-ui-demo` 中运行 `npm install`，然后运行 `npm run dev -- --host 0.0.0.0`
- 构建验证：`npm run build`
- 当前定位：完整交互原型与软件 MVP；电脑麦克风录音、本地历史和配置持久化已实现，现有 EasyInput 板子触发、板子 Wi-Fi 麦克风、语音识别和 Windows 文字输出尚未正式接入。

当前已有 12 个页面：工作台、语音输入、历史记录、词库、按键配置、设备与连接、AI 联动、表情库、表情编辑、动作编排、环境感知、设置与诊断。

## 2. 设计与代码约束

1. 先阅读 `deskmate-ui-demo/AGENTS.md`，保留现有亮色主界面、深灰导航栏、青蓝色桌宠视觉语言。
2. 本轮重点是补齐功能和数据层，不重新设计页面，不大改布局和视觉规范。
3. 板子按键、录音来源、STT 和系统文字输出必须通过适配器接口接入；没有真实协议时使用 `mock` 或 unavailable 实现，界面必须标注 Demo/待接入。
4. 不要把 Wi-Fi 密码、账号、Token、局域网地址或带“私密”字样的资料提交到 Git。
5. 不要修改或删除 `.openai/hosting.json`、`worker/index.js`、`scripts/prepare-sites-build.mjs`、`tests/sites-worker.test.mjs`。
6. 新增数据结构时要有默认值、版本号和迁移策略，避免刷新后因为旧数据导致白屏。
7. 浏览器不支持的桌面级能力（全局快捷键、剪贴板/粘贴、系统托盘、进程侦测、USB/HID 来源识别）通过安全桌面桥实现，不伪装成已经真实可用。

## 3. 双电脑分工

### 另一台电脑：实现

- 下一轮从审计修复分支创建 `codex/easyinput-app-integration`。
- 完成 `docs/OTHER_PC_TASK_HARDWARE_CONNECTIVITY.md` 中的 EasyInput 语音链路任务。
- 运行构建和测试，自查控制台错误。
- 提交并推送 `codex/easyinput-app-integration`。
- 回传分支名、提交哈希、变更文件、测试结果和未解决事项。

### 本电脑：审计

- 获取 `origin/codex/easyinput-app-integration`。
- 审查数据模型、权限/隐私、错误处理、兼容性和 UI 回归。
- 复跑构建、交互测试与设计 QA。
- 给出分级问题清单；修复通过后再合入主线。

## 4. Git 协作规则

另一台电脑下一轮接手：

```powershell
git clone https://github.com/zuming58/ai_hard_progect.git
cd ai_hard_progect
git fetch origin
git switch -c codex/easyinput-app-integration origin/codex/software-mvp-audit-fixes
cd deskmate-ui-demo
npm install
npm run dev -- --host 0.0.0.0
```

完成后：

```powershell
git status
git add -- <本次修改的明确文件>
git commit -m "Integrate EasyInput voice workflow"
git push -u origin codex/easyinput-app-integration
```

不要直接向 `main` 推送，也不要覆盖基线分支。

## 5. 当前已知边界

- 本机已确认现有 EasyInput 板子为 `VID 303A / PID 1006` 的 HID 键盘/厂商自定义 HID 设备；这能支持按键输入，但当前 Web App 还没有全局快捷键桌面桥。
- Windows 没有枚举出该板子的 USB Audio 输入端点。原软件说明板子麦克风通过 2.4GHz Wi-Fi 发送音频，具体协议尚未确认。
- 语音转文字供应商/API 尚未确定。当前只有真实电脑麦克风采集、IndexedDB 录音保存和 STT 适配器边界。
- 本阶段目标是“板子按键—录音—转写—历史—当前输入框”；未来屏幕、灯效、舵机和传感器控制不在下一轮范围内。
- Codex、Claude Code、Hermes、Workbody 的状态读取方式尚未统一。本阶段使用标准事件模型和 mock 适配器。
- 下一轮需要加入安全的 Windows 桌面壳，优先 Electron，同时保持 Web 版可运行和安全降级。

## 6. 审计交付格式

另一台电脑完成后，请回传：

```text
分支：
提交哈希：
实现内容：
主要变更文件：
运行过的命令及结果：
已知限制：
需要审计的风险点：
```
