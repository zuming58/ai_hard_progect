# EasyInput V2.0 开发板开源资料学习笔记

> 来源：https://github.com/CY-CHENYUE/easyinput-board-cy
> 下载时间：2026-08-15
> 用途：后续答疑、作业辅导、代码开发参考

---

## 一、硬件身份

| 项目 | 内容 |
|------|------|
| 芯片 | ESP32-S3R8（QFN56封装） |
| PSRAM | 8 MB（片内octal SPI） |
| Flash | 16 MB（W25Q128，外置） |
| 天线 | PCB板载天线 |
| 产品名 | EasyInput V2.0 |
| 固件板型 | `v2` / `V2` |
| PCB丝印 | AI Keyboard V2.1（同一块板，不是另一套pinout） |

> 结构件 V25/V26 不代表新电气版本，三个名字指向同一块硬件基线。

---

## 二、GPIO 完整映射

### 主按键 S1-S8（低有效，独立按键，非矩阵）

| 按键 | GPIO | 按下电平 |
|------|------|---------|
| S1 | 2 | 0 |
| S2 | 47 | 0 |
| S3 | 38 | 0 |
| S4 | 41 | 0 |
| S5 | 1 | 0 |
| S6 | 6 | 0 |
| S7 | 7 | 0 |
| S8 | 48 | 0 |

> ⚠️ GPIO0 不是 S5！GPIO0 是 BOOT/下载入口。

### 旋转编码器

| 功能 | GPIO | 说明 |
|------|------|------|
| A相 | 17 | 正交相位，内部上拉 |
| B相 | 16 | 正交相位，内部上拉 |
| 按压 S9 | 18 | 独立低有效按键 |

> A/B 是相位信号，静止时某一相为低是正常状态，不是按住键。

### 按键唤醒汇总

| 功能 | GPIO | 说明 |
|------|------|------|
| KEY_WAKE | 21 | 低有效，二极管OR汇总，只能说明有输入触发，不能区分具体按键 |

### LED

| 功能 | GPIO | 说明 |
|------|------|------|
| 5颗WS2812数据 | 12 | GRB格式，串联共用，不是5个独立GPIO |
| 独立绿色状态灯 | 42 | 高有效/PWM输出 |

### GPIO8 共享外设电源域

| 功能 | GPIO | 有效电平 |
|------|------|---------|
| PWR_EN | 8 | 高有效 |

**GPIO8 同时控制 LED、麦克风、扬声器的电源**，不是灯带开关。

安全上电顺序：
1. 锁存 GPIO8 为低
2. GPIO9/10/12/13/14/15 预装为低后配置为输出；GPIO11 保持浮空
3. 拉高 GPIO8
4. 等待电源稳定（**当前无统一毫秒数，项目需实测**）
5. 稳定后再初始化 WS2812、麦克风、扬声器

关断顺序：停止所有消费者 → 恢复安全引脚 → 拉低 GPIO8

### USB

| 功能 | GPIO |
|------|------|
| D- | 19 |
| D+ | 20 |

ESP32-S3 原生 USB，不是串口转USB。

### 音频

| 外设 | 信号 | GPIO |
|------|------|------|
| 麦克风 | BCLK | 9 |
| 麦克风 | WS | 10 |
| 麦克风 | DATA IN | 11 |
| 扬声器 | BCLK | 14 |
| 扬声器 | WS | 13 |
| 扬声器 | DATA OUT | 15 |

> I2S控制器编号、采样率、位宽、格式由目标项目决定，不是板级默认值。

### 电池与充电

| 功能 | GPIO | 说明 |
|------|------|------|
| 分压采样使能 | 5 | 高有效，拉高后读GPIO4 |
| 电压采样 | 4 (ADC1_CH3) | 板上分压≈VBAT/2 |
| 外部供电检测 | 40 | 低=外部供电存在 |
| 充电状态 | 39 | 仅外部供电存在时有效：1=充电中，0=充满 |

> 板上无 fuel gauge，电量百分比需基于电压估算。

### 调试UART

| 功能 | GPIO |
|------|------|
| U0RXD | 44 |
| U0TXD | 43 |

J4四针口：1=3V3, 2=RXD0, 3=TXD0, 4=GND。交叉连接。

### 保留引脚

- GPIO0：BOOT/下载专用
- GPIO26-37：Flash/PSRAM 总线，不可用

---

## 三、BOOT 操作（已纠正旧教程）

### ✅ 正确操作（2026-08-05 实板确认）

- **进入下载模式**：开机状态 → 短按一次 BOOT 并松开 → 等待电脑出现下载端口
- **退出下载模式**：关机 → 重新开机

### ❌ 已作废（禁止传播）

- "按住 BOOT 再上电"
- "按住 BOOT + 按 RESET"
- "整个烧录过程持续按住 BOOT"

> 板上没有独立的 RESET/EN 按键。

---

## 四、开发注意事项

1. **板级事实 vs 项目策略**：按键动作、编码器交互、USB协议、分区、音频参数、睡眠策略 — 这些都是目标项目决定，不是板级默认值
2. **GPIO8 稳定时间**：当前无统一值，项目需实测或依据器件规格
3. **WS2812 黑帧 ≠ 关电**：黑帧只是灯灭，GPIO8 仍可能为高
4. **电池电量**：只能读端电压，需自行校准估算
5. **已知缺口**：最终BOM、Gerber、DRC/ERC、D19/D20装配状态、V_LED电平裕量、GPIO8跨批次波形 — 均未提供

---

## 五、事实优先级（答疑时遇到冲突按这个顺序判）

1. 用户对当前实板的明确确认（最新操作行为）
2. 当前批次可追溯的 ECAD/BOM/装配资料 + 专项测试
3. Skill 打包的原理图、PCB 快照
4. `board-contract.json`（机器副本，与原始证据冲突时必须修订原证据）
5. 目标项目声明（只能描述项目选择，不能覆盖物理连线）
6. 历史迁移文档、旧代码、网络通用教程 — **最低优先级，只供线索**

低优先级不能覆盖高优先级；没证据时标 `unknown`，不要"按 ESP32 常规做法"猜。

---

## 六、必须拦截的 10 条历史错误（学员/同事说这些时立刻纠正）

| ❌ 错误说法 | ✅ 正确事实 |
|------|------|
| S1=GPIO1 | S1=GPIO2 |
| S5=GPIO0 | S5=GPIO1；GPIO0 只用于 BOOT |
| S6/S7=GPIO5/GPIO6 | S6/S7=GPIO6/GPIO7 |
| PWR_EN=GPIO7 | PWR_EN=GPIO8，高有效 |
| GPIO8 只是 LED 开关 | GPIO8 是 LED/MIC/SPK **共享电源生命周期信号** |
| 发黑帧 = 关电 | 黑帧只熄灯，GPIO8 状态不变 |
| SEN_CHRG 高=已充满 | 外部供电存在时，高=充电中，低=充满 |
| KEY_WAKE 能识别具体按键 | KEY_WAKE 只汇总唤醒，之后必须重扫各输入 |
| PCB V2.1 是独立板型 | 与 EasyInput V2.0 / 固件别名 v2 是同一基线 |
| BOOT 必须按住并配合上电 | 当前板开机状态短按并松开即可 |
| 板上有单独 RESET 键 | 没有供用户操作的独立 RESET/EN 键 |

---

## 七、答疑速查（学员问"这块板是什么"）

**一句话定位**：CY 老师把 EasyInput V2.0 开发板整理成了 Agent Skill（Codex/Claude Code 都能用），只回答"板子是什么、连了什么、哪些边界不能破坏"，**不写代码、不烧录、不建工程**。后续如果要做 ESP-IDF 开发，还需要加载另一个 `esp-idf-cy` Skill（环境/构建/烧录）。

**典型查询入口**：
- 学员问引脚/BOOT/外设/原理图 → 加载 `easyinput-board-cy`
- 学员问"怎么编译烧录" → 加载 `esp-idf-cy`
- 学员问"业务逻辑怎么做"（按键动作、协议、分区） → 由学员自己的目标项目决定，Skill 不提供默认值

---

## 五、资料清单

| 文件 | 内容 |
|------|------|
| `README.md` | 项目总览、30秒入门、硬合同 |
| `SKILL.md` | AI Agent 使用流程、禁止事项 |
| `DESIGN.md` | 设计契约、术语模型（"开发板" / "板级" / "当前板"） |
| `references/pinout.md` | 完整引脚映射 |
| `references/boot-flash-recovery.md` | BOOT 操作详解 |
| `references/power-and-peripherals.md` | 电源与外设合同（GPIO8 时序） |
| `references/board-contract.json` | 机器可读合同（**唯一机器版 GPIO 真值源**） |
| `references/identity-and-authority.md` | 身份别名 + 证据优先级 |
| `references/project-boundaries.md` | 板级事实 vs 项目策略（边界划清） |
| `references/known-gaps-and-errata.md` | 已知缺口 + 必须拦截的历史错误 |
| `references/source-map.md` | 来源地图 + 快照规则 |
| `references/source-manifest.json` | 资产 hash/快照日期审计 |
| `assets/` | 原理图 2 页、PCB 正反面、品牌派生图、二维码 |
| `scripts/check_board_baseline.py` | 只读静态扫描器（PASS≠真机验收） |
| `tests/test_skill_contract.py` | Skill 合同测试（含 PolyForm LICENSE SHA-256 锁定） |
| `tests/test_check_board_baseline.py` | checker 单测（11 项，本机通过） |
| `agents/openai.yaml` | OpenAI Codex 注册元数据 |
| `evals/evals.json` | 评测用例 |

---

## 六、自测结果（2026-08-16 本机）

- ✅ `python tests/test_check_board_baseline.py` → 11/11 通过
- ⚠️ `python tests/test_skill_contract.py` → 在校验 PolyForm LICENSE 原文 SHA-256 时失败（`c0ea4a89...` 对不上）。原因是 Windows 下 git clone 会把 LF 转 CRLF，文件头多了 3 字节 BOM/CRLF 偏移。**这是仓库自带的出厂守护**，不是我们环境问题。CY 老师那边用 Linux/原版 git 拉是能通过的。本机不动 LICENSE 原文。
- ✅ `board-contract.json` 解析正常：`pins` 30 个，`verified_at=2026-08-05`