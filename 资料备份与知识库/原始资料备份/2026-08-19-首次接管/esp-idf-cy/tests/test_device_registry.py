#!/usr/bin/env python3
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "device-registry.py"
MODULE_SPEC = importlib.util.spec_from_file_location("device_registry", SCRIPT)
REGISTRY_MODULE = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(REGISTRY_MODULE)


class DeviceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = Path(self.temp.name) / "registry"

    def tearDown(self):
        self.temp.cleanup()

    def run_registry(self, *arguments, expected=0, env=None):
        command = [
            sys.executable,
            str(SCRIPT),
            "--registry-dir",
            str(self.registry),
            *arguments,
        ]
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(
            expected,
            result.returncode,
            msg=f"command={command}\nstdout={result.stdout}\nstderr={result.stderr}",
        )
        if result.stdout:
            return json.loads(result.stdout)
        return None

    def remember(self, mac="7c-df-a1-12-34-56", chip="ESP32-S3", name="桌面开发板"):
        return self.run_registry(
            "remember",
            "--mac",
            mac,
            "--chip",
            chip,
            "--name",
            name,
        )

    def test_remember_is_private_and_public_views_mask_mac(self):
        result = self.remember()
        self.assertEqual("created", result["status"])
        self.assertEqual("…:34:56", result["device"]["mac_hint"])
        self.assertNotIn("7C:DF:A1:12:34:56", json.dumps(result, ensure_ascii=False))

        record_path = self.registry / "devices" / "7CDFA1123456" / "device.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual("7C:DF:A1:12:34:56", record["identity"]["value"])
        self.assertEqual("espressif.base_mac", record["identity"]["kind"])
        self.assertEqual("桌面开发板", record["alias"])
        if os.name != "nt":
            self.assertEqual(0o600, stat.S_IMODE(record_path.stat().st_mode))
            self.assertEqual(0o700, stat.S_IMODE(self.registry.stat().st_mode))

        lookup = self.run_registry("lookup", "--mac", "7C:DF:A1:12:34:56")
        self.assertTrue(lookup["found"])
        self.assertEqual("桌面开发板", lookup["device"]["name"])
        self.assertNotIn("7C:DF:A1:12:34:56", json.dumps(lookup, ensure_ascii=False))

    def test_duplicate_names_are_allowed_and_remain_ambiguous(self):
        self.remember()
        second = self.run_registry(
            "remember",
            "--mac",
            "11:22:33:44:55:66",
            "--chip",
            "ESP32-C6",
            "--name",
            "桌面开发板",
        )
        self.assertEqual("created", second["status"])
        listing = self.run_registry("list")
        self.assertEqual(2, listing["count"])
        self.assertEqual(["桌面开发板", "桌面开发板"], [item["name"] for item in listing["devices"]])
        self.assertEqual({"…:34:56", "…:55:66"}, {item["mac_hint"] for item in listing["devices"]})
        self.assertTrue(
            all(set(item) == {"name", "chip", "mac_hint"} for item in listing["devices"])
        )

    def test_rename_clear_name_and_forget_only_touch_selected_mac(self):
        self.remember()
        self.run_registry(
            "remember",
            "--mac",
            "11:22:33:44:55:66",
            "--chip",
            "ESP32-C6",
            "--name",
            "测试板",
        )
        renamed = self.run_registry(
            "rename",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--name",
            "客厅传感器",
        )
        self.assertEqual("客厅传感器", renamed["device"]["name"])
        other = self.run_registry("lookup", "--mac", "11:22:33:44:55:66")
        self.assertEqual("测试板", other["device"]["name"])

        cleared = self.run_registry("clear-name", "--mac", "7C:DF:A1:12:34:56")
        self.assertIsNone(cleared["device"]["name"])
        forgotten = self.run_registry("forget", "--mac", "7C:DF:A1:12:34:56")
        self.assertEqual("forgotten", forgotten["status"])
        missing = self.run_registry("lookup", "--mac", "7C:DF:A1:12:34:56")
        self.assertFalse(missing["found"])
        self.assertTrue(self.run_registry("lookup", "--mac", "11:22:33:44:55:66")["found"])

    def test_version_domains_stay_independent(self):
        self.remember()
        elf_hash = "ab" * 32
        snapshot = self.run_registry(
            "snapshot",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--event",
            "running_reported",
            "--environment-idf",
            "ESP-IDF v6.0.2",
            "--project-idf",
            "v5.5.4-12-g1234567",
            "--firmware-idf",
            "v5.4.3",
            "--firmware-evidence",
            "running-application",
            "--firmware-elf-sha256",
            elf_hash,
        )
        versions = snapshot["device"]["idf"]
        self.assertEqual("ESP-IDF v6.0.2", versions["environment"]["idf_version"])
        self.assertEqual("v5.5.4-12-g1234567", versions["project"]["idf_version"])
        self.assertEqual("v5.4.3", versions["firmware"]["idf_version"])
        self.assertEqual(elf_hash, versions["firmware"]["elf_sha256"])

        record = json.loads(
            (self.registry / "devices" / "7CDFA1123456" / "device.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("idf", record)
        snapshots = list(
            (self.registry / "devices" / "7CDFA1123456" / "snapshots").glob("*.json")
        )
        self.assertEqual(1, len(snapshots))
        listing = self.run_registry("list")
        self.assertEqual({"name", "chip", "mac_hint"}, set(listing["devices"][0]))
        self.assertNotIn(elf_hash, json.dumps(listing))

    def test_flash_verified_requires_firmware_evidence(self):
        self.remember()
        self.run_registry(
            "snapshot",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--event",
            "flash_verified",
            "--environment-idf",
            "v6.0.2",
            expected=64,
        )
        result = self.run_registry(
            "snapshot",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--event",
            "flash_verified",
            "--firmware-idf",
            "v6.0.2",
            "--firmware-evidence",
            "flashed-image",
        )
        self.assertEqual("v6.0.2", result["device"]["idf"]["firmware"]["idf_version"])
        self.run_registry(
            "snapshot",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--event",
            "running_reported",
            "--firmware-idf",
            "v6.0.2",
            "--firmware-evidence",
            "flashed-image",
            expected=64,
        )
        self.run_registry(
            "snapshot",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--event",
            "build_observed",
            "--firmware-idf",
            "v6.0.2",
            "--firmware-evidence",
            "running-application",
            expected=64,
        )

    def test_invalid_input_and_identity_conflict_fail_closed(self):
        self.run_registry(
            "remember",
            "--mac",
            "not-a-mac",
            "--chip",
            "ESP32-S3",
            expected=64,
        )
        self.run_registry(
            "remember",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--chip",
            "ESP32-S3",
            "--name",
            "bad\nname",
            expected=64,
        )
        self.remember()
        self.run_registry(
            "remember",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--chip",
            "ESP32-C6",
            expected=4,
        )

    def test_corrupt_record_is_not_silently_replaced(self):
        self.remember()
        record_path = self.registry / "devices" / "7CDFA1123456" / "device.json"
        record_path.write_text("{not-json", encoding="utf-8")
        self.run_registry(
            "remember",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--chip",
            "ESP32-S3",
            "--name",
            "新名字",
            expected=4,
        )
        self.assertEqual("{not-json", record_path.read_text(encoding="utf-8"))

    def test_corrupt_snapshot_fails_closed(self):
        self.remember()
        self.run_registry(
            "snapshot",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--event",
            "build_observed",
            "--project-idf",
            "v5.5.4",
        )
        snapshot_path = next(
            (self.registry / "devices" / "7CDFA1123456" / "snapshots").glob("*.json")
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["idf"] = []
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        self.run_registry(
            "lookup",
            "--mac",
            "7C:DF:A1:12:34:56",
            expected=4,
        )

    @unittest.skipIf(os.name == "nt", "POSIX mode check")
    def test_existing_wide_registry_is_rejected_without_chmod(self):
        self.registry.mkdir(mode=0o755)
        os.chmod(self.registry, 0o755)
        self.run_registry(
            "remember",
            "--mac",
            "7C:DF:A1:12:34:56",
            "--chip",
            "ESP32-S3",
            expected=4,
        )
        self.assertEqual(0o755, stat.S_IMODE(self.registry.stat().st_mode))
        self.assertFalse((self.registry / "devices").exists())

    def test_immutable_json_publish_does_not_overwrite_or_leave_partial_final(self):
        target_dir = Path(self.temp.name) / "atomic"
        target_dir.mkdir(mode=0o700)
        existing = target_dir / "existing.json"
        existing.write_text("original\n", encoding="utf-8")
        with self.assertRaises(REGISTRY_MODULE.RegistryProblem):
            REGISTRY_MODULE.atomic_write_json(
                existing,
                {"replacement": True},
                replace=False,
            )
        self.assertEqual("original\n", existing.read_text(encoding="utf-8"))

        interrupted = target_dir / "interrupted.json"
        with mock.patch.object(
            REGISTRY_MODULE.os,
            "replace",
            side_effect=OSError("simulated publish failure"),
        ):
            with self.assertRaises(REGISTRY_MODULE.RegistryProblem):
                REGISTRY_MODULE.atomic_write_json(
                    interrupted,
                    {"complete": True},
                    replace=False,
                )
        self.assertFalse(interrupted.exists())
        self.assertEqual([], list(target_dir.glob("*.tmp")))

    def test_environment_override_uses_user_data_location(self):
        override = Path(self.temp.name) / "override"
        environment = os.environ.copy()
        environment["ESP_IDF_CY_DEVICE_REGISTRY_DIR"] = str(override)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "remember",
                "--mac",
                "7C:DF:A1:12:34:56",
                "--chip",
                "ESP32-S3",
                "--name",
                "实验板",
            ],
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertTrue((override / "devices" / "7CDFA1123456" / "device.json").is_file())

    def test_read_only_commands_do_not_create_a_registry(self):
        lookup = self.run_registry("lookup", "--mac", "7C:DF:A1:12:34:56")
        self.assertFalse(lookup["found"])
        listing = self.run_registry("list")
        self.assertEqual(0, listing["count"])
        self.assertFalse(self.registry.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
