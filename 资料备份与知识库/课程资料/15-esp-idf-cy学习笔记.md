# esp-idf-cy 学习笔记

> 整理时间：2026-08-18
> 整理人：Hermes（老王助手）
> 来源：GitHub 仓库 `CY-CHENYUE/esp-idf-cy`（当前工作副本位于 `参考仓库/esp-idf-cy/`）
> 原文：https://github.com/CY-CHENYUE/esp-idf-cy
> 协议：GPL-3.0-only（**本人消化笔记**采用 Hermes 标准许可；仓库原文保留 GPL-3.0）
> 用途：志愿者答疑依据 + 老王个人复习 + Agent 触发条件速查

---

## 一、这个东西到底是什么

`esp-idf-cy` 是 **CY 老师（AI 街溜子）为 WaytoAGI 第七期 AI 硬件训练营自研的 Agent Skill**。它不是一个普通的"安装脚本包"，而是一个**让 Agent（编程 AI）能完成 ESP32 全链路开发**的能力契约：

```
"我刚买了 ESP32-S3，Mac 上什么都没装，帮我把环境准备到 hello_world 能编译。"
```

→ Agent 读这条指令后，会**自动判断**你的环境是否装过、装没装坏、装在哪、用什么版本，并按情况：
- 复用（健康环境）
- 精确修复（EIM 管理下的坏环境）
- 从零安装（确认缺失）
- 走镜像（国内网络）
- 安全烧录 + 真实验证（不只看 flash 退出 0）

**核心定位**（来自 README.md 原话）：

> 它不把 EIM、Python、工具链、环境激活和国内镜像细节甩给新手，也不把 `flash` 退出 0 误报为应用已经运行。

---

## 二、它是 Skill，不是脚本——"Agent-first" 是什么

仓库结构（不只是脚本）：

| 目录 | 作用 |
|------|------|
| **SKILL.md**（397 行） | **Agent 决策入口** —— 决策顺序、安全红线、完成标准、按需读 reference 的路由 |
| **README.md**（236 行） | 用户入口（不讲 agent 怎么读） |
| **references/**（5 份） | 平台安装、命令、镜像、排错知识——**会随 ESP-IDF/EIM 变化**，执行前以实机证据复核 |
| **scripts/**（18 个） | 确定性探针、可重入默认安装、验签、argv 传递、身份解析、超时等机械边界——**不替 Agent 决策** |
| **tests/**（24 个） | 回归与契约测试 |
| **evals/evals.json** | Agent 行为评测 |
| **assets/** | README 视觉资产 + 微信二维码 |

**三层职责（不要混淆）**：
- **Agent**：侦察证据、选路线、解释异常、取得烧录确认、持续推进
- **SKILL.md**：决策顺序 + 完成标准 + reference 路由
- **references/**：变化知识，执行前实机复核
- **scripts/**：机械边界，**不是决策者或授权门禁**

**关键认知**：脚本覆盖不了的机器差异 → Agent 继续侦察，不能把"不在默认目录"等同于"没有安装"。

---

## 三、六阶段工作流（Agent 推进 ESP32 项目的标准路径）

来自 SKILL.md §工作方式 + README.md §六阶段：

```
1. Inspect  ─→  侦察 Agent 能力、平台、项目、IDF、Python、工具链、target、串口
2. Prepare  ─→  健康可复用 / 精确修复 / 确实缺失 三态分流
3. Build    ─→  同一条命令里装配正确环境，尊重项目锁定版本 + target
4. Identify ─→  读芯片型号 + MAC，可选查用户保存的本机名称
5. Confirm + flash ─→  核对 target，用户明确确认后才写入硬件
6. Verify   ─→  处理 BOOT/RESET + USB 重枚举；只靠应用日志收口
```

**每条 idf 命令的标准写法（必须同一条命令里装配环境，因为 export.sh 只对当前 shell 生效）**：

```bash
# macOS/Linux 官方脚本安装
source <IDF_PATH>/export.sh >/dev/null 2>&1 && idf.py -C <项目目录> build

# Windows（跑在 Git Bash 里）
bash <skill>/scripts/idf-env.sh idf.py -C <项目目录> build
```

---

## 四、烧录三道门禁（核心安全规约）

来自 SKILL.md §烧录前后的三道门禁：

| 门禁 | 内容 |
|------|------|
| **1. Identity（验身）** | 读芯片型号 + MAC。烧录/复位导致 USB 重枚举时，**续写前必须再验原 MAC**；不用新端口名或设备名代替身份 |
| **2. Authority（授权）** | 核对项目 target，**明确告知将要写入的设备**，**等用户确认**才烧 |
| **3. Evidence（证据）** | 烧录命令成功 ≠ 应用已运行。最终恢复后**只有命中应用专用健康标志**且无 ROM 下载证据，才报告 `POST_FLASH_READY=yes` |

**铁律（来自 SKILL.md §五条物理事实）**：
> 烧录 = 覆盖用户硬件上的固件，板上可能跑着用户其他项目 → 未验明设备身份并经用户确认，不烧。这条不因任何理由松动。

---

## 五、环境装配的三态分流（来自 SKILL.md §安装或修复）

| 状态 | 处置 |
|------|------|
| `READY=yes` | **原样复用**，不安装、不升级、不切换版本 |
| 已精确安装但损坏 | EIM 管理 → `eim fix -p <精确路径>`；legacy → 重跑官方 install；修完对同一路径严格复检 |
| 确认不存在兼容环境 | 才新安装；**多个候选或证据冲突时继续调查或只问一个会改变结果的问题** |

**绝不**：
- ❌ 不要因为有更新的 stable 就静默升级
- ❌ 不要把"EIM 已装"误当成"所有依赖已齐"
- ❌ 不要为"能下载"绕过 hash/签名
- ❌ 不要静默安装 Homebrew 或 `curl|sh` 引入第三方 Python

**安装后门禁**：
> 仓库元数据版本 + `idf.py --version` 实际报告版本 **都必须和请求精确一致**；macOS/Linux 还要与请求安装路径一致。任一不满足都算安装失败，**不能因安装器退出 0 就报成功**。

---

## 六、平台路由速查表（README.md）

| 环境 | 默认策略 |
|------|---------|
| 已有健康 IDF | 发现并真实验证后复用，不升级、不重装 |
| Windows x64 | 优先官方 EIM；Agent 宿主没 Bash 时直接走固定 PowerShell helper，**不先要求新手学 Bash** |
| Windows 非 x64 | 先探测架构；当前官方 Windows EIM CLI 资产为 x64，**不盲下不兼容可执行文件** |
| macOS 已有 EIM 或 Homebrew | 实机验证后复用 EIM；有 Homebrew 时可按官方清单准备前置 |
| macOS 无 EIM / Homebrew | **不静默安装长期包管理器**，用仍受支持的 Command Line Tools / Python + 官方脚本路线 |
| 中国大陆网络 | IDF 仓库、工具资产和 pip 优先走乐鑫官方镜像机制，**不为"能下载"绕过 hash 或签名验证** |

**系统信任边界**：
- 密码、Touch ID、UAC、macOS 安全窗口和许可接受 → 必须由用户本人处理
- 脚本返回 `ACTION_REQUIRED`/rc=20 → 这是可恢复的人机交接，**不是安装失败**

---

## 七、烧录闭环的两阶段门禁（最容易踩坑的地方）

来自 SKILL.md §烧录后闭环：

```bash
# 阶段 1：prepare（仍在刚才确认过的烧录口上）
bash <skill>/scripts/post-flash-check.sh prepare \
  -p <烧录口> -m <用户已确认的MAC> \
  --download-entry <automatic|manual|unknown>

# 阶段 2：verify（用 prepare 输出的 session）
bash <skill>/scripts/post-flash-check.sh verify --session <POST_FLASH_SESSION> \
  -C <proj> -e '<能证明应用健康的正则>' [-p <已明确的恢复后端口>]
```

**关键约束**：
- `--download-entry` **由你显式传**，不能从端口日志猜
- `manual/unknown` 时 prepare 输出 `ACTION_REQUIRED=restore_normal_boot_for_board` 和 rc=20；这是**板级电路恢复正常启动**动作，**不是固定按键命令**
- **恢复正常启动绝不再次按 BOOT**——只有本轮确实手动拉低过 BOOT/下载 strap 才先释放它
- 有 RESET/EN 就点按一次；没有则真正断电再上电
- **重新上电必须切断这块板的全部供电**——有电池、调试器或外部 5V/3V3 时只拔 USB 可能没有产生上电复位
- **verify 阶段只做 fresh rescan + 尝试串口控制线 reset/采集，零次调用 identify/esptool**
- 只有应用 `-e` 命中时才输出 `POST_FLASH_READY=yes`/rc=0

**ROM 仍在下载模式的强证据**（rc=20 触发条件）：
- `DOWNLOAD_BOOT(...)`
- `DOWNLOAD(USB/UART0...)`
- `waiting for download`

**不确定（不能冒充 READY）**：
- 无日志
- 端口消失
- 普通 `ESP-ROM`/`rst:` 文本

---

## 八、设备命名与版本分层（学员最容易混淆的）

### 8.1 命名（显示标签，不是身份）

- **fresh MAC** 才是设备键；用户名称只是当前电脑上的显示标签
- 名称允许重复，**不能单独选择硬件、证明重枚举前后是同一设备或授权烧录**
- 首次见到时，Agent 最多提供一次非阻塞选择："要给它起一个只保存在这台电脑上的名称吗？"
- 跳过 → 不创建持久记录，不影响当前任务，本会话不重复追问
- 多块同名时全部列出芯片、当前端口、MAC 尾号让用户消歧；**不静默覆盖、不自动选一个**

### 8.2 IDF 版本三层（必须分别记录）

> IDF 版本不是设备永久属性。三者可能不同，缺哪项就保持未知，**绝不能用当前环境版本冒充板上固件版本**。

| 来源 | 取值 |
|------|------|
| **环境 IDF** | 当前实际激活环境的 `idf.py --version` |
| **项目 IDF** | 当前 build metadata 的项目构建版本 |
| **固件 IDF** | 刚烧录 app image 的 `esp_app_desc_t.idf_ver`，或运行应用主动报告的版本 |

> 设备目录底层**不得**提供一个含糊的总 `idf_version` / "主版本" 字段；外部存储只有一个通用版本格时先扩展 schema，不能三选一或把三类证据塞进同一字符串。

---

## 九、下载模式进入的板级判断（不要硬编码 GPIO0）

> BOOT 是板上标签，不是跨芯片固定引脚。

| 芯片系列 | 下载 strap 引脚 |
|---------|---------------|
| ESP32-S3 | 常用 GPIO0 |
| ESP32-C3 / C6 | GPIO9（且要满足对应芯片的其他 strap 条件） |

**板级进入动作（按板子电路）**：

| 板子条件 | 动作 |
|---------|------|
| 有 BOOT + RESET/EN | 按住 BOOT → 点按一次 RESET/EN → 松开 BOOT |
| 只有 BOOT | 按住 BOOT → **真正断电**再上电 → 松开 BOOT |
| 没有 BOOT | 查板型说明/原理图/厂商恢复方式，**不让你找不存在的按键** |
| 自动连接尚未真实尝试 | 先让用户不碰按键，由 `idf.py`/esptool 默认复位机制试 |
| 已能与 ROM 通信或刚完成手动动作 | **不要再次要求按 BOOT**，直接重扫、验身、续操作 |

---

## 十、为什么不用 `idf.py monitor`

> Agent 会话通常**没有交互 TTY**。`idf.py monitor` 强制要求 TTY，对 Agent 不可用。

Skill 附带有界 pyserial 采集器（`scripts/monitor.sh` / `serial_monitor.py`）：
- 按超时和健康正则退出
- 匹配运行在可终止子进程中
- 有采集总超时和 64 KiB 窗口限制
- 人类需要交互调试时仍可在真实终端用官方 monitor

---

## 十一、必须拦截的历史错误（10 条起步）

**这是学习笔记最关键的一节——学员来问的就是他们记错的版本。**

| # | ❌ 错误说法 | ✅ 正确事实 |
|---|---------|---------|
| 1 | "esp-idf-cy 是一个安装脚本" | 它是 **Agent Skill**，核心是让 Agent 决策，脚本只做机械边界 |
| 2 | "烧录命令退出 0 = 应用已运行" | **不等于**。必须命中应用专用健康日志且无 ROM 下载证据，才算 `POST_FLASH_READY=yes` |
| 3 | "BOOT 是 ESP32 跨芯片固定引脚" | 不是。S3 常用 GPIO0，**C3/C6 是 GPIO9**；要查板型资料 |
| 4 | "烧录失败就一直按 BOOT + 重插 USB" | 先看是不是 USB 重枚举导致端口消失；**已能与 ROM 通信时不要再按 BOOT** |
| 5 | "恢复正常启动时可以再按一次 BOOT" | **绝不**。只有本轮确实手动拉低过 BOOT 才先释放它；之后用 RESET/EN 或真正断电 |
| 6 | "用 `idf.py monitor` 让 Agent 看日志" | Agent 没 TTY；用 Skill 自带的 pyserial 采集器（`monitor.sh`） |
| 7 | "有新版本 ESP-IDF 就该升级" | **不**。健康环境复用精确版本；已有项目优先服从项目锁定的精确版本 |
| 8 | "设备名称就是硬件身份" | **不是**。fresh MAC 才是设备键；名称只是显示标签，可重复 |
| 9 | "板载 IDF 版本是设备永久属性" | 不是。三类来源（环境/项目/固件）分别记录，缺哪项保持未知 |
| 10 | "ESP-IDF 路径或项目路径里有空格也能跑" | **不能**。ESP-IDF 官方不支持；shell 引号只能保留参数边界，不能修复上游限制 |
| 11 | "EIM 装好了 = 所有依赖都齐了" | **不是**。EIM 在 POSIX 只检查前置；其余依赖需单独确认 |
| 12 | "Mac 没装 EIM 就不能用" | 可以。已有健康 IDF 复用；都没有时走官方脚本路线，**不静默安装 Homebrew** |
| 13 | "EspInput V2.0"（如果是历史资料里） | 正确是 **EasyInput V2.0**，音译错误（详见 12 号总结顶部澄清） |
| 14 | "Skill 没安装好" | 不影响 SKILL.md 本身，**`esp-idf-cy` 已在 `~/.hermes/skills/`** 已验证文件落地；新会话才会出现在 skill list |

---

## 十二、参考资料索引

### 12.1 references/ 目录按需读取

来自 SKILL.md §按任务渐进读取：

| 当前阶段 | 先读 |
|---------|------|
| 安装、修复、EIM、PowerShell-only | `references/install-playbook.md` |
| 国内网络或镜像失败 | `references/china-mirrors.md` |
| target、idf.py、esptool、EIM 命令 | `references/idf-commands.md` |
| 已有报错、驱动、BOOT/RESET、串口异常 | `references/troubleshooting.md` |
| 设备命名、收录、改名、版本快照 | `references/device-registry.md` |

### 12.2 与训练营其他资料的关联

| 本笔记提到 | 已沉淀到哪份资料 |
|---------|----------------|
| ESP-IDF 框架 / 工具链 | [07-综合知识库 §2.2](07-综合技术知识库（志愿者答疑依据）.md) |
| EasyInput V2.0 板子 / GPIO | [10-EasyInput V2.0 开源资料学习笔记](10-EasyInput%20V2.0开源资料学习笔记.md) |
| 板子名称澄清（EasyInput vs InstaInput） | [12-第1课总结顶部"📌 名称澄清"](12-第1课总结-从想法到开工.md) |
| 烧录/编译/环境操作流程（讲义范围） | [11-第1课讲义 §01-05](11-第1课讲义-从想法到开工.md) |
| 训练营规则/排错提示 | [13-第1课-会议纪要补充](13-第1课-会议纪要补充.md) |

---

## 十三、Agent 触发条件（来自 SKILL.md description YAML）

> 当用户提到以下任何词时，Skill 必须触发：

| 类别 | 触发词 |
|------|-------|
| **核心动作** | ESP-IDF、idf.py、ESP32 编译、烧录固件、flash 到板子、串口 monitor/日志 |
| **环境动作** | 装 ESP-IDF、IDF 环境配置、menuconfig、sdkconfig |
| **故障** | hello_world 跑不起来、找不到串口/COM口、esptool |
| **设备** | 给开发板命名、收录/记住这个设备、设备别名 |
| **自然语言** | "我刚买了 ESP32-S3, 电脑什么都没装, 帮我开始" / "帮我把这个 ESP32 项目编译烧录一下" / "看看板子输出了什么" |

**不做的边界**（来自 SKILL.md description）：
- ❌ Arduino-ESP32 / PlatformIO 工作流
- ❌ 具体外设驱动业务代码的编写

---

## 十四、本地安装与同步状态

- **仓库克隆**：`F:/Codex/ai hardware/参考仓库/esp-idf-cy/`（当前工作副本含 `.git/`）
- **Skill 安装**：`~/.hermes/skills/esp-idf-cy/`（`cp -r` 整个目录）
- **skill_view 验证**：复制已落地，但 Hermes skill 列表缓存未刷新 → 新会话可见
- **wiki 同步**：本笔记双位置同步到 `F:/wiki/02-AI实战知识库/projects/AI硬件训练营/15-esp-idf-cy学习笔记.md`

---

## 十五、志愿者答疑快速回答模板

> 学员问："esp-idf-cy 是什么？"

**简短版**：
> CY 老师为训练营做的 Agent Skill，让 AI 帮你完成 ESP32 全链路开发（环境准备→编译→烧录→验证），Agent-first 而不是脚本主导。

**学员问："装好了吗？我能用了吗？"**
> Skill 已复制到 `~/.hermes/skills/esp-idf-cy/`。你下次新开会话时就会被识别。或者直接说"我要编译烧录 ESP32 项目"，Skill 会被自动触发。

**学员问："怎么编译？"**
> 把项目路径告诉 Agent，比如"编译这个项目 `~/projects/my-esp32`，目标是 ESP32-S3"。Agent 会自动侦察环境、走完整流程。

**学员问："烧录安全吗？会不会写错板子？"**
> Skill 有三道门禁：**验身（读 MAC）→ 授权（等你确认）→ 证据（应用日志验证）**。未经你确认不会写任何东西。

---

> 维护说明：本笔记基于 GitHub 仓库 `CY-CHENYUE/esp-idf-cy` @ commit `307361a`（2026-08-18 抓取）。CY 老师活跃迭代中，后续如有新版可在 `F:/Codex/ai hardware/参考仓库/esp-idf-cy/` 里 `git pull`，然后按本机 Agent 的 skill 安装规则更新即可。
