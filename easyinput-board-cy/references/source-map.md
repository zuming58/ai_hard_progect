# 来源地图与快照规则

本页只用于维护板级证据的出处，不向开发者提供任何应用工程入口。详细 SHA-256、大小和快照状态见 `source-manifest.json`；机器可读硬件常量见 `board-contract.json`。

## 权威输入

| 信息 | Skill 内位置 | 用途与限制 |
| --- | --- | --- |
| 2026-08-05 当前实板确认 | `board-contract.json` 的 `boot.authority` | BOOT 操作最高优先级；覆盖旧版硬件说明 |
| 两页原理图快照 | `assets/easyinput-v2-schematic-page-{1,2}.png` | 器件、网名、连线、电源和 BOOT 电路 |
| PCB 正反面快照 | `assets/easyinput-v2-pcb-{top,bottom}.png` | 丝印、部件位置和开发板身份 |
| 机器可读板级合同 | `references/board-contract.json` | GPIO、电气语义、共享电源和启动操作的唯一结构化入口 |

这些输入是独立打包的板级资料。运行本 Skill 时不需要访问创建快照时所在的应用仓库，也不得借此搜索或推荐任何应用工程。

## 原始证据资产

`assets/` 中四张 PNG 是来源快照的逐字节副本：

- `easyinput-v2-schematic-page-1.png`
- `easyinput-v2-schematic-page-2.png`
- `easyinput-v2-pcb-top.png`
- `easyinput-v2-pcb-bottom.png`

Skill 运行时只使用打包副本。维护者替换图片时必须从新的板级权威源复制，并同步更新 `source-manifest.json`；不能只替换图片而保留旧 hash。

## 品牌展示派生版

为 README 与人工审阅提供两页品牌标题栏版本：

- `easyinput-v2-schematic-page-1-branded.svg` / `.png`
- `easyinput-v2-schematic-page-2-branded.svg` / `.png`
- `schematic-branding-preview.html`

派生版只在原理图标题栏内部放置用户提供的“物启万相”“通往 AGI 之路”品牌标识，以及有依据的 `EasyInput V2.0 / Hardware Schematic` 标题；没有权威输入的比例、审批人、日期、图号和 REV 保持空白。两张品牌 Logo 只是展示输入，不是硬件证据。

板级判断、文字识别和后续证据更新仍以未加品牌的原始 PNG 为准。最终品牌 PNG 以原始 PNG 为像素底图，只合成标题栏区域；清单记录的校验结果为标题栏外变化像素数 `0`。SVG 保留可编辑叠加层，HTML 只用于并排审阅，均不得替代原始证据快照。

## 权利与许可映射

- 两张无品牌原理图 PNG 与 README 三张原创说明图，仅在许可方拥有或有权许可的范围内按 [`CC-BY-NC-4.0`](../ASSET-LICENSE.md) 提供。
- 两张含 Logo 的 PCB 快照、由 PCB TOP 生成的 Hero／多尺寸／GitHub 页壳／审阅板渲染、四张品牌派生 SVG／PNG 与 README 桌面／手机整页预览属于混合资产，不对整文件作单一 CC 授权；原理图、PCB／图片表达、项目文字／页面代码、Logo 与二维码分别沿用各自许可或权利状态。
- `brand-wuqiwangxiang-black.png`、`brand-waytoagi-black.png` 与 `wechat-qr.jpg` 不属于上述 CC 资产授权；品牌标识的出现只用于来源识别和展示，不授予独立 Logo 或商标使用权。
- `source-manifest.json` 记录文件来源、hash、许可路径和排除状态，便于审计；它不单独证明作者身份、委托／职务作品关系或再许可权。
- 图片许可只覆盖可受著作权保护的表达，不把 GPIO、网络连接、电气关系、功能方法或制造事实变成排他权利。

其他 Skill 文件继续按根 [`LICENSE`](../LICENSE) 与 [`NOTICE`](../NOTICE) 处理。任何新资产在进入公开包前都必须先明确权利状态和路径级许可，不能只复制文件后沿用目录默认值。

## 快照与漂移

- `board-contract.json` 是板级常量唯一机器可读入口。其他 JSON、代码和 Markdown 不得维护第二套机器可读 GPIO 数组。
- references 是 2026-08-05 的可移植快照，不会自动跟随任何应用工程变化。
- drift checker 只比较用户明确指定的目标项目与 `board-contract.json`。
- 目标项目可以不使用某个板载资源，但不能重定义其物理 GPIO 或有效电平。
- 分区、协议、USB 身份、内存分配、按键动作、I2S 控制器和采样率不参与板级常量比对。
