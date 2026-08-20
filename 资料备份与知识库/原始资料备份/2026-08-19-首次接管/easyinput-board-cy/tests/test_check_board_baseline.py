from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CHECKER = SKILL_ROOT / "scripts" / "check_board_baseline.py"


class BoardBaselineCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.contract = self.root / "board-contract.json"
        self.contract.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "aliases": {
                        "product": "EasyInput V2.0",
                        "firmware_board_alias": "v2",
                        "pcb_silkscreen": "AI Keyboard V2.1",
                    },
                    "pins": {
                        "KEY1": {"gpio": 2},
                        "KEY2": {"gpio": 47},
                        "KEY3": {"gpio": 38},
                        "KEY4": {"gpio": 41},
                        "KEY5": {"gpio": 1},
                        "KEY6": {"gpio": 6},
                        "KEY7": {"gpio": 7},
                        "KEY8": {"gpio": 48},
                        "ENCODER_A": {"gpio": 17},
                        "ENCODER_B": {"gpio": 16},
                        "ENCODER_PRESS": {"gpio": 18},
                        "KEY_WAKE": {"gpio": 21},
                        "LED_DIN": {"gpio": 12},
                        "PERIPHERAL_POWER": {"gpio": 8, "active_level": 1},
                        "USB_DN": {"gpio": 19},
                        "USB_DP": {"gpio": 20},
                        "BOOT0": {"gpio": 0},
                    },
                    "power": {
                        "gpio": 8,
                        "active_level": 1,
                    },
                    "boot": {"gpio": 0},
                    "usb": {"dn_gpio": 19, "dp_gpio": 20},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def make_project(self, files: dict[str, str], name: str = "project") -> Path:
        project = self.root / name
        project.mkdir(exist_ok=True)
        for relative, content in files.items():
            destination = project / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        return project

    def run_checker(self, project: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CHECKER),
                str(project),
                "--contract",
                str(self.contract),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_matching_board_facts_do_not_claim_power_sequence_proof(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": """
#define BOARD_KEY1_GPIO 2
#define BOARD_ENCODER_A_GPIO 17
#define BOARD_ENCODER_B_GPIO 16
#define BOARD_ENCODER_PRESS_GPIO 18
#define BOARD_BOOT_GPIO 0
#define BOARD_USB_DN_GPIO 19
#define BOARD_USB_DP_GPIO 20
#define BOARD_SHARED_POWER_GPIO 8
#define BOARD_SHARED_POWER_ACTIVE_HIGH 1
#define BOARD_WS2812_GPIO 12
""",
                "main/power.c": """
#include "board.h"
void power_on(void) {
    prepare_outputs();
    gpio_set_level(BOARD_SHARED_POWER_GPIO, 1);
    arbitrary_wait_ms(73);
}
""",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[WARN] POWER_SEQUENCE_UNPROVEN", result.stdout)
        self.assertNotIn("POWER_SETTLE_SAFE", result.stdout)
        self.assertIn("0 FAIL", result.stdout)

    def test_pin_drift_fails(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": """
#define EASY_INPUT_KEY_3_GPIO 37
#define AUX_LED_GPIO 19
""",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("[FAIL] PIN_DRIFT", result.stdout)
        self.assertIn("GPIO38", result.stdout)
        self.assertIn("[FAIL] USB_GPIO_REUSED", result.stdout)

    def test_boot_gpio_as_user_button_fails(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": "#define USER_BUTTON_GPIO 0\n",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("[FAIL] BOOT_GPIO_REUSED", result.stdout)

    def test_shared_power_polarity_uses_level_wording(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": """
#define BOARD_SHARED_POWER_GPIO 8
#define BOARD_SHARED_POWER_ACTIVE_HIGH 0
""",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("[FAIL] PIN_DRIFT", result.stdout)
        self.assertIn("level 0", result.stdout)
        self.assertIn("level 1", result.stdout)
        self.assertNotIn("ACTIVE LEVEL=GPIO", result.stdout)

    def test_unrelated_long_delay_cannot_prove_power_sequence(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": """
#define BOARD_SHARED_POWER_GPIO 8
#define BOARD_SHARED_POWER_ACTIVE_HIGH 1
#define BOARD_WS2812_GPIO 12
""",
                "main/status_led.c": """
#include "board.h"
void led_start(void) {
    gpio_set_level(BOARD_SHARED_POWER_GPIO, 1);
    esp_rom_delay_us(1500);
    initialize_led();
}
void wait_for_unrelated_transfer(void) {
    rmt_tx_wait_all_done(channel, pdMS_TO_TICKS(100));
}
""",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[WARN] POWER_SEQUENCE_UNPROVEN", result.stdout)
        self.assertNotIn("POWER_SETTLE_SAFE", result.stdout)
        self.assertNotIn("POWER_SETTLE_TOO_SHORT", result.stdout)
        self.assertNotIn("100 ms", result.stdout)
        self.assertIn("0 FAIL", result.stdout)

    def test_project_with_no_optional_peripherals_passes_without_behavior_guessing(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/app_main.c": "void app_main(void) {}\n",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[WARN] PIN_DECLARATIONS_NOT_FOUND", result.stdout)
        self.assertNotIn("UNKNOWN_PROFILE", result.stdout)
        self.assertNotIn("Profile:", result.stdout)
        self.assertIn("0 FAIL", result.stdout)

    def test_invalid_project_path_uses_exit_code_2(self) -> None:
        missing = self.root / "does-not-exist"
        result = self.run_checker(missing)
        self.assertEqual(result.returncode, 2)
        self.assertIn("project path does not exist", result.stderr)

    def test_nested_tmp_dependency_tree_is_pruned(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/app_main.c": "void app_main(void) {}\n",
                "tmp/esp-idf/components/ghost/board.h": """
#define USER_BUTTON_GPIO 0
#define EASY_INPUT_KEY_1_GPIO 99
""",
            }
        )
        result = self.run_checker(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("ghost", result.stdout)
        self.assertIn("0 FAIL", result.stdout)

    def test_findings_do_not_depend_on_project_directory_name(self) -> None:
        files = {
            "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
            "main/board.h": """
#define BOARD_KEY1_GPIO 2
#define BOARD_BOOT_GPIO 0
#define BOARD_USB_DN_GPIO 19
#define BOARD_USB_DP_GPIO 20
""",
        }
        first_project = self.make_project(files, "alpha-firmware")
        second_project = self.make_project(files, "beta-firmware")

        first = self.run_checker(first_project)
        second = self.run_checker(second_project)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_unselected_conditional_board_branches_warn_without_false_pass(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": """
#if defined(SELECT_CURRENT_BOARD)
#define BOARD_KEY1_GPIO 2
#else
#define BOARD_KEY1_GPIO 99
#endif
""",
            }
        )

        result = self.run_checker(project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[WARN] BUILD_BRANCH_UNSELECTED", result.stdout)
        self.assertIn("[WARN] PIN_DECLARATIONS_NOT_FOUND", result.stdout)
        self.assertNotIn("[PASS] PIN_MATCH", result.stdout)
        self.assertNotIn("[FAIL] PIN_DRIFT", result.stdout)

    def test_declared_but_unused_peripherals_do_not_require_power_runtime(self) -> None:
        project = self.make_project(
            {
                "CMakeLists.txt": "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n",
                "main/board.h": """
#define BOARD_WS2812_GPIO 12
#define BOARD_MIC_BCLK_GPIO 9
#define BOARD_MIC_WS_GPIO 10
#define BOARD_MIC_DATA_GPIO 11
#define BOARD_SPEAKER_BCLK_GPIO 14
#define BOARD_SPEAKER_WS_GPIO 13
#define BOARD_SPEAKER_DATA_GPIO 15
""",
                "main/app_main.c": "void app_main(void) {}\n",
            }
        )

        result = self.run_checker(project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("SHARED_POWER_MISSING", result.stdout)
        self.assertNotIn("POWER_SETTLE", result.stdout)
        self.assertNotIn("POWER_SEQUENCE_UNPROVEN", result.stdout)
        self.assertIn("0 FAIL", result.stdout)


if __name__ == "__main__":
    unittest.main()
