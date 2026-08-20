#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail() { echo "FAIL=agent-first-contract:$1" >&2; exit 1; }
require() { rg -Fq "$2" "$1" || fail "$3"; }

require "$ROOT/SKILL.md" '不要把示例路径当事实' dynamic-path-policy
require "$ROOT/SKILL.md" 'build/project_description.json' project-metadata-discovery
require "$ROOT/SKILL.md" '有界搜索' bounded-search
require "$ROOT/SKILL.md" 'GUI 不是默认依赖' gui-optional
require "$ROOT/SKILL.md" '密码、Touch ID、UAC' secure-ui-user-gate
require "$ROOT/SKILL.md" '不支持 IDF 路径或' whitespace-policy
require "$ROOT/SKILL.md" 'Windows 没有 Git Bash' powershell-bootstrap
require "$ROOT/SKILL.md" '已有可用 EIM 时直接复用' adaptive-mac-existing-eim
require "$ROOT/SKILL.md" '已有 Homebrew 且' adaptive-mac-homebrew
require "$ROOT/SKILL.md" '三层职责不要混淆' three-layer-agent-first
require "$ROOT/SKILL.md" 'FixIdf' exact-repair-route
require "$ROOT/SKILL.md" 'idf.py --list-targets' dynamic-target-discovery
require "$ROOT/SKILL.md" '不会把项目路径、正则或用户数据直接拼成 shell 命令' eim-data-code-boundary
require "$ROOT/SKILL.md" '芯片型号相同不代表开发板下载/复位电路相同' board-circuit-dynamic
require "$ROOT/SKILL.md" '恢复正常启动绝不再次按 BOOT' boot-entry-only
require "$ROOT/SKILL.md" '有电池或外部供电时拔 USB 不等于断电' complete-power-cycle
require "$ROOT/SKILL.md" 'IDF 版本不是设备永久属性' device-idf-domain-boundary
require "$ROOT/SKILL.md" '底层不得提供一个含糊的总 `idf_version`' no-single-idf-version
require "$ROOT/SKILL.md" '名称允许重复,不能单独选择硬件' duplicate-name-not-identity
require "$ROOT/SKILL.md" '能自动列全时' agent-lists-all-devices-first
require "$ROOT/README.md" 'Skill 会根据实机动态分流' readme-dynamic-route
require "$ROOT/README.md" 'Agent 会操作 EIM GUI 吗？' readme-gui-boundary
require "$ROOT/README.md" '健康可复用 / 已安装但损坏 / 确实未安装' readme-three-state
require "$ROOT/README.md" '每块板烧录时都要按 BOOT / RESET 吗？' readme-board-controls
require "$ROOT/README.md" '可以给开发板起名字吗？收录时要记 IDF 版本吗？' readme-device-registry
require "$ROOT/references/idf-commands.md" 'NUL 分隔' eim-fixed-argv-relay
require "$ROOT/references/idf-commands.md" '已经在下载模式 / 板子没有 DTR、RTS' already-download-mode
require "$ROOT/references/device-registry.md" '三种信息不要混在一起' registry-three-domains
require "$ROOT/scripts/device-registry.py" 'espressif.base_mac' registry-stable-identity
require "$ROOT/scripts/post-flash-check.sh" 'CURRENT_PORT_IDENTITY=unverified' honest-post-reset-identity
require "$ROOT/scripts/post-flash-check.sh" 'restore_normal_boot_for_board' neutral-recovery-action

if rg -n '/Users/cychenyue|C:\\Users\\cychenyue' "$ROOT" \
  --glob '!**/tests/**' --glob '!**/evals/**' --glob '!**/LICENSE' >/dev/null; then
  fail hardcoded-local-user-path
fi

python3 - "$ROOT/evals/evals.json" <<'PY' || exit $?
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
by_id = {item["id"]: item for item in data["evals"]}
required = {
    14: "Computer Use",
    15: "project_description.json",
    16: "PowerShell",
    17: "NUL",
    18: "FixIdf",
    19: "OSArchitecture",
    20: "CURRENT_PORT_IDENTITY=unverified",
    21: "idf.py --list-targets",
    22: "真正切断",
    23: "automatic",
    24: "下载 strap",
    25: "桌面开发板",
    26: "fresh MAC",
    27: "同名候选",
    28: "本机显示名称",
    29: "MAC 尾号",
    30: "二者不匹配",
    31: "environment",
}
for eval_id, text in required.items():
    item = by_id.get(eval_id)
    if not item or text not in (item["prompt"] + item["expected_output"]):
        print(f"FAIL=agent-first-contract:eval-{eval_id}", file=sys.stderr)
        raise SystemExit(1)
print("PASS=agent-first-evals")
PY

echo PASS=agent-first-contract
