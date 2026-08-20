# esp-idf-cy · 本机设备目录与 IDF 版本证据

> 只在用户明确同意“收录 / 记住 / 命名设备”时使用。设备目录是本机显示辅助，不是设备身份、
> 烧录授权或 post-flash session。执行前仍以本次真实识别结果为准。

## 三种信息不要混在一起

| 信息 | 含义 | 能否用于烧录身份 |
|---|---|---|
| Espressif base MAC | 本 Skill 当前使用的稳定设备键 | 可以，但每次写入前仍要 fresh 读取并匹配 |
| 用户名称 | 本机可读标签，例如“桌面 S3” | 不可以；允许重名，也不能代替 MAC |
| IDF 版本快照 | 某次环境、项目构建或固件的版本证据 | 不可以；它描述软件上下文，不描述硬件身份 |

端口名只是一条临时运输通道。名称只用于显示。真正写入前始终重新运行设备验身、核对完整 MAC、
芯片与项目 target，并取得本轮明确确认。

## 什么时候收录

1. 先通过 `identify-device.sh` 得到本次真实 `CHIP` 与标准化 `MAC`。
2. 若用户未主动要求，可在首次成功识别后只提供一次非阻塞选择：
   “要给它起一个只保存在这台电脑上的名称吗？也可以跳过。”
3. 用户跳过时不创建记录，不影响当前编译、识别或烧录任务；当前会话不重复追问。
4. 用户同意后才调用：

   ```bash
   python <skill>/scripts/device-registry.py remember \
     --mac <fresh-MAC> --chip <fresh-CHIP> --name '<用户给的名称>'
   ```

5. 再次见到设备时，必须先 fresh 读取 MAC，再按 MAC 查询名称：

   ```bash
   python <skill>/scripts/device-registry.py lookup --mac <fresh-MAC>
   ```

普通设备列表只显示名称、芯片和 MAC 尾号。名称相同时全部列出，让用户按芯片、当前端口和 MAC 尾号
消歧；不会附带 IDF 版本、时间戳或 ELF SHA256。`lookup --mac` 是已用 fresh MAC 定位后的详细查询，
可能包含这些版本证据，不要把详细输出原样贴到公开 Issue。不要静默覆盖、自动选中或把名称重新绑定到
另一 MAC。

改名、清除名称和忘记设备只修改本机目录，不触碰开发板：

```bash
python <skill>/scripts/device-registry.py rename --mac <fresh-or-confirmed-MAC> --name '<新名称>'
python <skill>/scripts/device-registry.py clear-name --mac <fresh-or-confirmed-MAC>
python <skill>/scripts/device-registry.py forget --mac <用户明确要删除的MAC>
```

## IDF 版本是三个独立事实

### 当前环境版本

在本次实际选择并激活的 IDF 环境运行 `idf.py --version`。它只证明当前命令环境，不证明旧 build，
也不证明板上固件。需要时用 `snapshot --environment-idf '<原始输出>'` 单独记录。

### 项目构建版本

有现成 build 时读取 `build/project_description.json` 的 `git_revision` 与 `idf_path`，并确认元数据
属于当前产物。它描述构建上下文；若元数据与本地 app image 冲突，先报告冲突，不要用当前环境值覆盖。

ESP-IDF 官方构建系统将 `IDF_VER` 作为精确 Git 描述，并生成项目 metadata：
[Build System](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/build-system.html)、
[`project_description.json.in`](https://github.com/espressif/esp-idf/blob/master/tools/cmake/project_description.json.in)。

### 固件版本

只有以下证据能写入 `firmware` 域：

- 刚刚实际烧录的 app image：从该 `.bin` 的 `esp_app_desc_t.idf_ver` 读取，并且 post-flash
  已对同一 MAC 得到 `POST_FLASH_READY=yes`。
- 当前运行应用主动返回 `esp_app_get_description()->idf_ver` 或 `esp_get_idf_version()`。

本地 image 只证明这个文件；在烧录与应用验证完成前不能写成设备当前固件。普通 `idf.py --version`、
项目 README、bootloader 版本或 esptool 的芯片识别结果都不能代填。

标准 ESP-IDF app image 可用所选实际 esptool 版本的 `image-info` / `image_info` 读取：
[App Image Format](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/app_image_format.html)、
[esptool image-info](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html)。
运行应用描述见
[Miscellaneous System APIs](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/misc_system_api.html)。

若应用没有上报能力、没有可确认的本地 app image，固件 IDF 就保持未知。不要为了补齐设备目录而
额外读整片 flash、进入下载模式、复位设备或覆盖用户的“不再运行设备识别/写入命令”边界。

## 写入版本快照

三类版本必须分别传入，缺哪类就不写哪类，绝不互相复制：

底层存储不要设计单一 `idf_version`、`primary_idf` 或“设备 IDF 版本”字段。外部存储只有一个
通用版本格时停止写入并扩展 schema；不得选择任意一个充当总版本，也不要把三类证据拼进同一字符串。
面向人的设备卡片可以把来源充分的 firmware 域显示为“当前固件 IDF”摘要，但 environment/project
仍保存在详情中。三个值不同只证明三个来源的观测不同，不能据此断言某份 build 更旧、某次烧录
已经发生或环境需要升级。

```bash
python <skill>/scripts/device-registry.py snapshot \
  --mac <已收录且本轮确认的MAC> \
  --event build_observed \
  --environment-idf '<idf.py --version 原始输出>' \
  --project-idf '<project_description.json git_revision>'
```

只有刚烧录的 app image 已与同一设备完成应用验证，才写：

```bash
python <skill>/scripts/device-registry.py snapshot \
  --mac <已收录且本轮确认的MAC> \
  --event flash_verified \
  --firmware-idf '<app image 中的 idf_ver>' \
  --firmware-evidence flashed-image \
  [--firmware-elf-sha256 <64位SHA256>]
```

设备运行时主动报告版本时，使用 `--event running_reported --firmware-evidence running-application`。

## 存储与隐私

- 默认目录：macOS/Linux 为 `~/.esp-idf-cy/device-registry-v1`；Windows 为当前用户
  `LOCALAPPDATA\esp-idf-cy\device-registry-v1`。
- 可用 `ESP_IDF_CY_DEVICE_REGISTRY_DIR` 覆盖，但不要放进项目、Git、云同步或共享目录。
- 自定义到一个已经存在的 POSIX 目录时，脚本不会擅自 `chmod`；若该目录允许 group/other 访问，
  写入会失败并要求改用专用私有目录。普通 `list` / 未命中的 `lookup` 不创建目录或改变权限。
- 每个 MAC 使用独立目录；名称不进入文件名。设备 metadata 原子替换，版本快照不可变追加。
- POSIX 目录和文件使用当前用户权限。Windows 使用当前用户 profile 的继承 ACL；企业环境覆盖路径时，
  先确认该目录不是多人共享。
- 不保存项目绝对路径、串口日志、Wi-Fi、凭据或业务数据。公开列表只显示 MAC 尾号。
- 名称允许中文、空格和路径分隔符，但拒绝控制字符；它始终只作为 JSON 数据，不能拼进 shell 命令。
