# DeskMate 双电脑协作开发交接

更新时间：2026-08-21

## 1. 当前基线

- GitHub：`https://github.com/zuming58/ai_hard_progect`
- 基线分支：`codex/deskmate-ui-demo-handoff`
- 前端项目：`deskmate-ui-demo/`
- 技术栈：React 19、Vite 6、Tabler Icons
- 本地启动：在 `deskmate-ui-demo` 中运行 `npm install`，然后运行 `npm run dev -- --host 0.0.0.0`
- 构建验证：`npm run build`
- 当前定位：完整交互原型，UI 已定稿；硬件、固件、语音识别服务尚未正式接入。

当前已有 12 个页面：工作台、语音输入、历史记录、词库、按键配置、设备与连接、AI 联动、表情库、表情编辑、动作编排、环境感知、设置与诊断。

## 2. 设计与代码约束

1. 先阅读 `deskmate-ui-demo/AGENTS.md`，保留现有亮色主界面、深灰导航栏、青蓝色桌宠视觉语言。
2. 本轮重点是补齐功能和数据层，不重新设计页面，不大改布局和视觉规范。
3. 所有硬件能力必须通过适配器接口接入；没有真实协议时使用 `mock` 实现，界面必须标注 Demo/待接入。
4. 不要把 Wi-Fi 密码、账号、Token、局域网地址或带“私密”字样的资料提交到 Git。
5. 不要修改或删除 `.openai/hosting.json`、`worker/index.js`、`scripts/prepare-sites-build.mjs`、`tests/sites-worker.test.mjs`。
6. 新增数据结构时要有默认值、版本号和迁移策略，避免刷新后因为旧数据导致白屏。
7. 浏览器不支持的桌面级能力（全局快捷键、系统托盘、进程侦测、USB/串口）先定义接口和 mock，不伪装成已经真实可用。

## 3. 双电脑分工

### 另一台电脑：实现

- 从基线分支创建 `codex/software-mvp-core`。
- 完成 `docs/OTHER_PC_TASK.md` 中的第一阶段功能。
- 运行构建和测试，自查控制台错误。
- 提交并推送 `codex/software-mvp-core`。
- 回传分支名、提交哈希、变更文件、测试结果和未解决事项。

### 本电脑：审计

- 获取 `origin/codex/software-mvp-core`。
- 审查数据模型、权限/隐私、错误处理、兼容性和 UI 回归。
- 复跑构建、交互测试与设计 QA。
- 给出分级问题清单；修复通过后再合入主线。

## 4. Git 协作规则

另一台电脑首次接手：

```powershell
git clone https://github.com/zuming58/ai_hard_progect.git
cd ai_hard_progect
git fetch origin
git switch -c codex/software-mvp-core origin/codex/deskmate-ui-demo-handoff
cd deskmate-ui-demo
npm install
npm run dev -- --host 0.0.0.0
```

完成后：

```powershell
git status
git add -- <本次修改的明确文件>
git commit -m "Implement DeskMate software MVP core"
git push -u origin codex/software-mvp-core
```

不要直接向 `main` 推送，也不要覆盖基线分支。

## 5. 当前已知边界

- ESP32-S3 固件与通信协议未拿到，因此 USB HID、串口配置、灯效、屏幕、舵机和传感器均不能声称真实接通。
- 语音转文字供应商/API 尚未确定。本阶段只做真实麦克风采集与清晰的 STT 适配器接口。
- Codex、Claude Code、Hermes、Workbody 的状态读取方式尚未统一。本阶段使用标准事件模型和 mock 适配器。
- 正式桌面应用壳（Tauri/Electron）尚未决定；当前先保持 Web 可运行，并把桌面能力隔离到服务接口。

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
