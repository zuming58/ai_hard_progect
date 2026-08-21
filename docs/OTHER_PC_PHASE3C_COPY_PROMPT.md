# 可复制给另一台 Codex 的任务指令

把下面整段原样复制给另一台电脑上的 Codex：

```text
请接手 DeskMate / EasyInput 项目的 Phase 3C 无硬件代码先行开发，并直接完成、测试、提交和推送，不要只给计划。

仓库：
https://github.com/zuming58/ai_hard_progect

基线分支：
origin/codex/easyinput-phase3b-productization

请新建并使用分支：
codex/easyinput-phase3c-code-first

先按顺序完整阅读：
1. AGENTS.md
2. docs/MASTER_HANDOFF_2026-08-22.md
3. docs/OTHER_PC_PHASE3C_CODE_FIRST_TASK.md
4. docs/PHASE3B_PRODUCTIZATION_STATUS.md
5. docs/EASYINPUT_AUDIO_PROTOCOL_REPORT.md
6. docs/HARDWARE_CONNECTIVITY_STATUS.md

然后严格执行 docs/OTHER_PC_PHASE3C_CODE_FIRST_TASK.md 中的 P1-P4：

1. 完成协议无关、可注入、可取消、有限缓冲和有限重连的 EasyInput 局域网音频适配层；默认仍必须返回 protocol-unconfirmed，只使用合成音频和 mock transport 做测试。
2. 完成不暴露 IP、MAC、SSID、网关、设备路径和窗口标题的网络能力/脱敏诊断；网线电脑不能被误判为无法使用局域网。
3. 完成 Codex、Claude Code、Hermes、Workbody 的版本化统一状态事件、纯状态 reducer 和桌宠表情/动作/亮度/注意力意图映射；本阶段只提供明确标注的 mock provider，不伪造真实连接。
4. 补全自动化测试、状态文档、回归构建和 Windows 桌面打包。

这台电脑没有 EasyInput 键盘，也没有用户真实百炼 API Key，这是预期情况。请把硬件与账号相关项目明确列为“待有键盘电脑验收”，不要因此跳过所有可做的代码，也不要声称真机通过。

严禁：
- 猜测或硬编码未知 IP、端口、广播、WebSocket 和音频包格式。
- 主动扫描局域网、抓包、关闭防火墙、读取或烧录固件。
- 向未知 HID/USB 接口写数据。
- 把 mock、Demo、协议未知显示成真实已连接。
- 索要、写入或提交 API Key、录音、历史文本、用户网络信息。
- 破坏已经可用的 F22、电脑麦克风、实时字幕、qwen3-asr-flash、qwen3.7-flash 整理、历史 schema v5、托盘与文字输出闭环。

开始时执行基线测试；实现后必须运行：
npm test
npm run build
npm run test:sites
npm run build:desktop

所有修改请提交并推送到 origin/codex/easyinput-phase3c-code-first。保持工作区干净。除非遇到无法从仓库资料判断且会改变产品方向的真实阻塞，否则自行作合理、安全的工程判断继续完成，不要中途只返回问题。

最终请按 docs/OTHER_PC_PHASE3C_CODE_FIRST_TASK.md 第 10 节的固定格式返回：分支、提交哈希、已推送状态、实现内容、主要文件、每条测试结果、明确未验证项和下一步真机操作。
```
