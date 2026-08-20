#!/usr/bin/env python3
"""Local, opt-in ESP device registry.

The registry keeps a stable MAC identity separate from a user-facing alias and
from IDF version observations. It never identifies hardware by itself and must
not be used as flash authorization.
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
IDENTITY_KIND = "espressif.base_mac"
MAX_ALIAS_LENGTH = 64
MAX_TEXT_LENGTH = 128
LOCK_WAIT_SECONDS = 5.0
STALE_LOCK_SECONDS = 60.0
EVENT_FIRMWARE_EVIDENCE = {
    "flash_verified": "flashed-image",
    "running_reported": "running-application",
}
DOMAIN_SOURCES = {
    "environment": {"idf.py --version in selected environment"},
    "project": {"build/project_description.json git_revision"},
    "firmware": {
        "esp_app_desc.idf_ver from verified flashed app image",
        "current application esp_app_desc.idf_ver",
    },
}


class RegistryProblem(Exception):
    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code


class UsageParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"ERROR={message}", file=sys.stderr)
        raise SystemExit(64)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def normalize_mac(value):
    compact = re.sub(r"[:-]", "", value.strip())
    if not re.fullmatch(r"[0-9A-Fa-f]{12}", compact):
        raise RegistryProblem(f"无效 MAC: {value}", 64)
    compact = compact.upper()
    return ":".join(compact[index:index + 2] for index in range(0, 12, 2))


def mac_key(mac):
    return mac.replace(":", "")


def mac_hint(mac):
    return f"…:{mac[-5:]}"


def clean_text(value, field, maximum=MAX_TEXT_LENGTH):
    text = value.strip()
    if not text:
        raise RegistryProblem(f"{field} 不能为空", 64)
    if len(text) > maximum:
        raise RegistryProblem(f"{field} 最长 {maximum} 个字符", 64)
    if any(unicodedata.category(char).startswith("C") for char in text):
        raise RegistryProblem(f"{field} 不能含控制字符", 64)
    return text


def clean_hash(value, field):
    text = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise RegistryProblem(f"{field} 必须是 64 位十六进制 SHA256", 64)
    return text


def registry_root(explicit):
    raw = explicit or os.environ.get("ESP_IDF_CY_DEVICE_REGISTRY_DIR")
    if raw:
        return Path(raw).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "esp-idf-cy" / "device-registry-v1"
    return Path.home() / ".esp-idf-cy" / "device-registry-v1"


def ensure_private_dir(path):
    if path.is_symlink():
        raise RegistryProblem(f"注册表路径不能是符号链接: {path}", 4)
    created = False
    try:
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=False, mode=0o700)
                created = True
            except FileExistsError:
                pass
        if path.is_symlink() or not path.is_dir():
            raise RegistryProblem(f"注册表路径不是安全目录: {path}", 4)
        if os.name != "nt" and created:
            os.chmod(path, 0o700)
    except OSError as exc:
        raise RegistryProblem(f"无法准备注册表目录: {exc}", 4) from exc
    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:
            raise RegistryProblem(
                f"注册表目录权限过宽({mode:03o}),拒绝修改现有目录: {path}",
                4,
            )


def devices_root(root, create=True):
    path = root / "devices"
    if create:
        ensure_private_dir(root)
        ensure_private_dir(path)
    else:
        if root.exists() and root.is_symlink():
            raise RegistryProblem(f"注册表路径不能是符号链接: {root}", 4)
        if path.exists() and path.is_symlink():
            raise RegistryProblem(f"设备目录不能是符号链接: {path}", 4)
    return path


def device_dir(root, mac, create_base=True):
    return devices_root(root, create=create_base) / mac_key(mac)


def validate_device_record(data, expected_mac=None):
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise RegistryProblem("设备记录 schema 不受支持或已损坏", 4)
    identity = data.get("identity")
    if not isinstance(identity, dict) or identity.get("kind") != IDENTITY_KIND:
        raise RegistryProblem("设备记录缺少受支持的身份类型", 4)
    stored_mac = normalize_mac(str(identity.get("value", "")))
    if expected_mac and stored_mac != expected_mac:
        raise RegistryProblem("设备目录与记录中的 MAC 冲突", 4)
    chip = clean_text(str(data.get("chip", "")), "chip")
    alias = data.get("alias")
    if alias is not None:
        alias = clean_text(str(alias), "设备名称", MAX_ALIAS_LENGTH)
    return stored_mac, chip, alias


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryProblem(f"无法读取注册表记录 {path.name}: {exc}", 4) from exc


def read_device(path, expected_mac=None):
    if path.exists() and path.is_symlink():
        raise RegistryProblem(f"设备记录目录不能是符号链接: {path}", 4)
    record_path = path / "device.json"
    if not record_path.exists():
        return None
    if record_path.is_symlink():
        raise RegistryProblem("device.json 不能是符号链接", 4)
    data = read_json(record_path)
    validate_device_record(data, expected_mac)
    return data


def atomic_write_json(path, data, *, replace=True):
    ensure_private_dir(path.parent)
    if not replace and path.exists():
        raise RegistryProblem(f"不可变记录已存在,拒绝覆盖: {path.name}", 4)
    descriptor = None
    temp_name = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if not replace and path.exists():
            raise RegistryProblem(f"不可变记录已存在,拒绝覆盖: {path.name}", 4)
        os.replace(temp_name, path)
        temp_name = None
        if os.name != "nt":
            os.chmod(path, 0o600)
    except OSError as exc:
        raise RegistryProblem(f"无法原子写入注册表: {exc}", 4) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


@contextmanager
def device_lock(path):
    ensure_private_dir(path)
    lock_path = path / ".update.lock"
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            lock_path.mkdir(mode=0o700)
            break
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > STALE_LOCK_SECONDS
            except OSError:
                stale = False
            if stale:
                try:
                    lock_path.rmdir()
                    continue
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                raise RegistryProblem("设备记录正被另一个进程更新", 4)
            time.sleep(0.05)
        except OSError as exc:
            raise RegistryProblem(f"无法锁定设备记录: {exc}", 4) from exc
    try:
        yield
    finally:
        try:
            lock_path.rmdir()
        except OSError:
            pass


def latest_idf_observations(path):
    snapshots = path / "snapshots"
    latest = {}
    if not snapshots.is_dir() or snapshots.is_symlink():
        return latest
    for snapshot_path in snapshots.glob("*.json"):
        if snapshot_path.is_symlink():
            raise RegistryProblem(f"快照不能是符号链接: {snapshot_path.name}", 4)
        data = read_json(snapshot_path)
        expected_mac = ":".join(path.name[index:index + 2] for index in range(0, 12, 2))
        device = read_device(path, expected_mac)
        if device is None:
            raise RegistryProblem("版本快照缺少对应设备记录", 4)
        _, expected_chip, _ = validate_device_record(device, expected_mac)
        idf = validate_snapshot_record(data, snapshot_path, expected_mac, expected_chip)
        captured_at = str(data.get("captured_at", ""))
        for domain, observation in idf.items():
            current = latest.get(domain)
            ordering = (captured_at, str(data.get("snapshot_id", "")))
            if current is None or ordering > current["_ordering"]:
                latest[domain] = {
                    "idf_version": observation.get("idf_version"),
                    "source": observation.get("source"),
                    "captured_at": captured_at,
                    "_ordering": ordering,
                }
                if observation.get("elf_sha256"):
                    latest[domain]["elf_sha256"] = observation["elf_sha256"]
    for observation in latest.values():
        observation.pop("_ordering", None)
    return latest


def validate_snapshot_record(data, path, expected_mac, expected_chip):
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise RegistryProblem(f"快照 {path.name} schema 不受支持或已损坏", 4)
    snapshot_id = str(data.get("snapshot_id", ""))
    try:
        uuid.UUID(snapshot_id)
    except (ValueError, AttributeError) as exc:
        raise RegistryProblem(f"快照 {path.name} ID 无效", 4) from exc
    if path.stem != snapshot_id:
        raise RegistryProblem(f"快照 {path.name} 的文件名与 ID 不一致", 4)
    clean_text(str(data.get("captured_at", "")), "captured_at")
    event = str(data.get("event", ""))
    if event not in ("identified", "build_observed", "flash_verified", "running_reported"):
        raise RegistryProblem(f"快照 {path.name} 的 event 无效", 4)
    device = data.get("device")
    if not isinstance(device, dict) or device.get("kind") != IDENTITY_KIND:
        raise RegistryProblem(f"快照 {path.name} 缺少设备身份", 4)
    if normalize_mac(str(device.get("value", ""))) != expected_mac:
        raise RegistryProblem(f"快照 {path.name} 的 MAC 与设备目录不一致", 4)
    chip = clean_text(str(data.get("chip", "")), "chip")
    if chip.casefold() != expected_chip.casefold():
        raise RegistryProblem(f"快照 {path.name} 的芯片与设备记录不一致", 4)
    idf = data.get("idf")
    if not isinstance(idf, dict) or not idf or not set(idf).issubset(DOMAIN_SOURCES):
        raise RegistryProblem(f"快照 {path.name} 的 IDF 版本域无效", 4)
    for domain, observation in idf.items():
        if not isinstance(observation, dict) or observation.get("status") != "observed":
            raise RegistryProblem(f"快照 {path.name} 的 {domain} 证据无效", 4)
        clean_text(str(observation.get("idf_version", "")), "IDF 版本")
        if observation.get("source") not in DOMAIN_SOURCES[domain]:
            raise RegistryProblem(f"快照 {path.name} 的 {domain} 来源无效", 4)
        if "elf_sha256" in observation:
            if domain != "firmware":
                raise RegistryProblem(f"快照 {path.name} 的 ELF SHA256 来源域无效", 4)
            clean_hash(str(observation["elf_sha256"]), "ELF SHA256")
    firmware = idf.get("firmware")
    expected_evidence = EVENT_FIRMWARE_EVIDENCE.get(event)
    if expected_evidence:
        expected_source = {
            "flashed-image": "esp_app_desc.idf_ver from verified flashed app image",
            "running-application": "current application esp_app_desc.idf_ver",
        }[expected_evidence]
        if not firmware or firmware.get("source") != expected_source:
            raise RegistryProblem(f"快照 {path.name} 的 event 与固件证据不一致", 4)
    elif firmware:
        raise RegistryProblem(f"快照 {path.name} 的 event 不能携带固件证据", 4)
    return idf


def public_device_summary(data):
    mac, chip, alias = validate_device_record(data)
    return {
        "name": alias,
        "chip": chip,
        "mac_hint": mac_hint(mac),
    }


def public_device(path, data):
    result = public_device_summary(data)
    result.update(
        {
        "idf": latest_idf_observations(path),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "last_seen_at": data.get("last_seen_at"),
        }
    )
    return result


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def command_remember(args, root):
    mac = normalize_mac(args.mac)
    chip = clean_text(args.chip, "chip")
    alias = clean_text(args.name, "设备名称", MAX_ALIAS_LENGTH) if args.name else None
    path = device_dir(root, mac)
    with device_lock(path):
        existing = read_device(path, mac)
        now = utc_now()
        if existing:
            _, old_chip, old_alias = validate_device_record(existing, mac)
            if old_chip.casefold() != chip.casefold():
                raise RegistryProblem(
                    f"同一 MAC 已记录为 {old_chip},本次却识别为 {chip};拒绝覆盖",
                    4,
                )
            record = existing
            if alias is not None:
                record["alias"] = alias
            elif "alias" not in record:
                record["alias"] = old_alias
            record["updated_at"] = now
            record["last_seen_at"] = now
            status = "updated"
        else:
            record = {
                "schema_version": SCHEMA_VERSION,
                "identity": {"kind": IDENTITY_KIND, "value": mac},
                "chip": chip,
                "alias": alias,
                "created_at": now,
                "updated_at": now,
                "last_seen_at": now,
            }
            status = "created"
        atomic_write_json(path / "device.json", record)
    emit({"status": status, "device": public_device(path, record)})
    return 0


def command_lookup(args, root):
    mac = normalize_mac(args.mac)
    path = device_dir(root, mac, create_base=False)
    data = read_device(path, mac)
    if data is None:
        emit({"found": False})
        return 0
    emit({"found": True, "device": public_device(path, data)})
    return 0


def iter_devices(root):
    base = devices_root(root, create=False)
    if not base.is_dir():
        return []
    records = []
    for path in base.iterdir():
        if not path.is_dir() or path.is_symlink() or not re.fullmatch(r"[0-9A-F]{12}", path.name):
            continue
        expected_mac = ":".join(path.name[index:index + 2] for index in range(0, 12, 2))
        data = read_device(path, expected_mac)
        if data is not None:
            records.append((path, data))
    return records


def command_list(_args, root):
    devices = [public_device_summary(data) for _path, data in iter_devices(root)]
    devices.sort(key=lambda item: ((item["name"] or "").casefold(), item["chip"].casefold(), item["mac_hint"]))
    emit({"count": len(devices), "devices": devices})
    return 0


def command_rename(args, root):
    mac = normalize_mac(args.mac)
    alias = clean_text(args.name, "设备名称", MAX_ALIAS_LENGTH)
    path = device_dir(root, mac, create_base=False)
    if not path.is_dir() or path.is_symlink():
        raise RegistryProblem("没有找到这个 MAC 的设备记录", 2)
    with device_lock(path):
        data = read_device(path, mac)
        if data is None:
            raise RegistryProblem("没有找到这个 MAC 的设备记录", 2)
        data["alias"] = alias
        data["updated_at"] = utc_now()
        atomic_write_json(path / "device.json", data)
    emit({"status": "renamed", "device": public_device(path, data)})
    return 0


def command_clear_name(args, root):
    mac = normalize_mac(args.mac)
    path = device_dir(root, mac, create_base=False)
    if not path.is_dir() or path.is_symlink():
        raise RegistryProblem("没有找到这个 MAC 的设备记录", 2)
    with device_lock(path):
        data = read_device(path, mac)
        if data is None:
            raise RegistryProblem("没有找到这个 MAC 的设备记录", 2)
        data["alias"] = None
        data["updated_at"] = utc_now()
        atomic_write_json(path / "device.json", data)
    emit({"status": "name_cleared", "device": public_device(path, data)})
    return 0


def observed_domain(version, source, elf_sha256=None):
    observation = {
        "status": "observed",
        "idf_version": clean_text(version, "IDF 版本"),
        "source": source,
    }
    if elf_sha256:
        observation["elf_sha256"] = clean_hash(elf_sha256, "ELF SHA256")
    return observation


def command_snapshot(args, root):
    mac = normalize_mac(args.mac)
    path = device_dir(root, mac, create_base=False)
    if not path.is_dir() or path.is_symlink():
        raise RegistryProblem("请先在用户同意后收录这块设备", 2)
    with device_lock(path):
        data = read_device(path, mac)
        if data is None:
            raise RegistryProblem("请先在用户同意后收录这块设备", 2)
        idf = {}
        if args.environment_idf:
            idf["environment"] = observed_domain(
                args.environment_idf,
                "idf.py --version in selected environment",
            )
        if args.project_idf:
            idf["project"] = observed_domain(
                args.project_idf,
                "build/project_description.json git_revision",
            )
        if args.firmware_idf:
            if not args.firmware_evidence:
                raise RegistryProblem("--firmware-idf 必须同时提供 --firmware-evidence", 64)
            source = {
                "flashed-image": "esp_app_desc.idf_ver from verified flashed app image",
                "running-application": "current application esp_app_desc.idf_ver",
            }[args.firmware_evidence]
            idf["firmware"] = observed_domain(
                args.firmware_idf,
                source,
                args.firmware_elf_sha256,
            )
        elif args.firmware_evidence or args.firmware_elf_sha256:
            raise RegistryProblem("固件证据必须与 --firmware-idf 一起提供", 64)
        if not idf:
            raise RegistryProblem("快照至少需要一种独立取得的 IDF 版本证据", 64)
        expected_evidence = EVENT_FIRMWARE_EVIDENCE.get(args.event)
        if expected_evidence and args.firmware_evidence != expected_evidence:
            raise RegistryProblem(
                f"{args.event} 必须包含 {expected_evidence} 固件证据",
                64,
            )
        if not expected_evidence and args.firmware_evidence:
            raise RegistryProblem(f"{args.event} 不能携带固件版本证据", 64)

        snapshot_id = str(uuid.uuid4())
        captured_at = utc_now()
        _, chip, _ = validate_device_record(data, mac)
        snapshot = {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": snapshot_id,
            "captured_at": captured_at,
            "event": args.event,
            "device": {"kind": IDENTITY_KIND, "value": mac},
            "chip": chip,
            "idf": idf,
        }
        snapshots = path / "snapshots"
        ensure_private_dir(snapshots)
        snapshot_path = snapshots / f"{snapshot_id}.json"
        atomic_write_json(snapshot_path, snapshot, replace=False)
    emit(
        {
            "status": "snapshot_created",
            "snapshot_id": snapshot_id,
            "event": args.event,
            "device": public_device(path, data),
        }
    )
    return 0


def command_forget(args, root):
    mac = normalize_mac(args.mac)
    path = device_dir(root, mac, create_base=False)
    if not path.is_dir() or path.is_symlink():
        raise RegistryProblem("没有找到这个 MAC 的设备记录", 2)
    with device_lock(path):
        data = read_device(path, mac)
        if data is None:
            raise RegistryProblem("没有找到这个 MAC 的设备记录", 2)
        public = public_device(path, data)
        try:
            shutil.rmtree(path)
        except OSError as exc:
            raise RegistryProblem(f"无法删除设备记录: {exc}", 4) from exc
    emit({"status": "forgotten", "device": public})
    return 0


def build_parser():
    parser = UsageParser(description="esp-idf-cy 本机设备目录")
    parser.add_argument(
        "--registry-dir",
        help="覆盖设备目录根路径；默认用 ESP_IDF_CY_DEVICE_REGISTRY_DIR 或当前用户数据目录",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    remember = commands.add_parser("remember", help="按 fresh MAC 收录或刷新设备")
    remember.add_argument("--mac", required=True)
    remember.add_argument("--chip", required=True)
    remember.add_argument("--name", help="可选本机显示名称；允许与其他设备重名")
    remember.set_defaults(handler=command_remember)

    lookup = commands.add_parser("lookup", help="fresh MAC 识别后查本机显示信息")
    lookup.add_argument("--mac", required=True)
    lookup.set_defaults(handler=command_lookup)

    listing = commands.add_parser("list", help="列出已收录设备；默认只显示 MAC 尾号")
    listing.set_defaults(handler=command_list)

    rename = commands.add_parser("rename", help="修改本机显示名称")
    rename.add_argument("--mac", required=True)
    rename.add_argument("--name", required=True)
    rename.set_defaults(handler=command_rename)

    clear_name = commands.add_parser("clear-name", help="清除名称但保留设备记录")
    clear_name.add_argument("--mac", required=True)
    clear_name.set_defaults(handler=command_clear_name)

    snapshot = commands.add_parser("snapshot", help="记录相互独立的 IDF 版本证据")
    snapshot.add_argument("--mac", required=True)
    snapshot.add_argument(
        "--event",
        required=True,
        choices=("identified", "build_observed", "flash_verified", "running_reported"),
    )
    snapshot.add_argument("--environment-idf")
    snapshot.add_argument("--project-idf")
    snapshot.add_argument("--firmware-idf")
    snapshot.add_argument(
        "--firmware-evidence",
        choices=("flashed-image", "running-application"),
    )
    snapshot.add_argument("--firmware-elf-sha256")
    snapshot.set_defaults(handler=command_snapshot)

    forget = commands.add_parser("forget", help="删除本机设备记录与版本快照")
    forget.add_argument("--mac", required=True)
    forget.set_defaults(handler=command_forget)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    root = registry_root(args.registry_dir)
    try:
        if root.exists() and not root.is_dir():
            raise RegistryProblem("设备目录根路径不是目录", 4)
        return args.handler(args, root)
    except RegistryProblem as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
