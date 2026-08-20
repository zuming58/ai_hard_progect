#!/usr/bin/env python3
"""Read-only EasyInput V2 board-contract audit for ESP-IDF projects.

The checker deliberately audits board facts only.  It does not require a
project to implement every peripheral, infer runtime use from declarations,
or inspect application behavior.

Exit codes:
    0: no FAIL findings (WARN findings may be present)
    1: one or more board-contract violations
    2: command-line, path, or contract configuration error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".inc"}
SPECIAL_SOURCE_NAMES = {"CMakeLists.txt", "sdkconfig", "sdkconfig.defaults"}
EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".venv",
    "__pycache__",
    "dist",
    "managed_components",
    "node_modules",
    "output",
    "tmp",
    "vendor",
}
MAX_SOURCE_BYTES = 1_000_000
LEVEL_FACTS = {
    "peripheral_power_active_level",
    "external_power_active_level",
    "charge_status_active_level",
    "keys_active_low",
}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    location: str | None = None


@dataclass(frozen=True)
class Occurrence:
    fact: str
    value: int
    symbol: str
    path: Path
    line: int

    def location(self, root: Path) -> str:
        try:
            relative = self.path.relative_to(root)
        except ValueError:
            relative = self.path
        return f"{relative}:{self.line}"


@dataclass
class BoardContract:
    path: Path
    expected: dict[str, int]
    board_aliases: list[str]
    raw: Mapping[str, Any] = field(repr=False)


@dataclass
class SourceFile:
    path: Path
    text: str


@dataclass
class AuditReport:
    root: Path
    contract: BoardContract
    findings: list[Finding] = field(default_factory=list)
    _dedupe: set[tuple[str, str, str, str | None]] = field(default_factory=set)

    def add(
        self, level: str, code: str, message: str, location: str | None = None
    ) -> None:
        key = (level, code, message, location)
        if key not in self._dedupe:
            self._dedupe.add(key)
            self.findings.append(Finding(level, code, message, location))

    @property
    def failed(self) -> bool:
        return any(item.level == "FAIL" for item in self.findings)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _fact_for_name(name: str, *, contract_path: bool = False) -> str | None:
    """Map common C/C++ names or JSON paths to board-level fact IDs."""

    token = _normalized(name)
    if not token:
        return None

    # Values such as KEY1.active_level are not the key's GPIO.
    if token.endswith(("activelevel", "activehigh", "activelow")):
        if "peripheralpower" in token or "sharedpower" in token or "pwren" in token:
            return "peripheral_power_active_level"
        if "keys" in token or "buttons" in token:
            return "keys_active_low"
        if "externalpower" in token or "vin" in token:
            return "external_power_active_level"
        if "charge" in token or "chrg" in token:
            return "charge_status_active_level"
        return None

    if "ws2812" in token and "count" in token:
        return "ws2812_count"

    key_match = re.search(r"(?:key|button|btn|switch|s)([1-8])(?:gpio|pin)?$", token)
    if key_match:
        return f"key{key_match.group(1)}"
    if contract_path:
        key_match = re.search(
            r"(?:keys|buttons)(?:key|button|btn|switch|s)?([1-8])(?:gpio|pin)?$",
            token,
        )
        if key_match:
            return f"key{key_match.group(1)}"

    if "encoder" in token:
        if re.search(r"encoder(?:pin)?a(?:gpio|pin)?$", token) or token.endswith(
            ("encoderagpio", "encoderapin")
        ):
            return "encoder_a"
        if re.search(r"encoder(?:pin)?b(?:gpio|pin)?$", token) or token.endswith(
            ("encoderbgpio", "encoderbpin")
        ):
            return "encoder_b"
        if any(word in token for word in ("press", "push", "button", "switch")):
            return "encoder_press"

    if "keywake" in token or ("wake" in token and "gpio" in token):
        return "key_wake"
    if "boot" in token and any(word in token for word in ("gpio", "pin", "boot0")):
        return "boot0"

    if "usb" in token:
        if any(word in token for word in ("dn", "dminus", "dmgpio", "dmpin")):
            return "usb_dn"
        if any(word in token for word in ("dp", "dplus", "dpgpio", "dppin")):
            return "usb_dp"

    if "ws2812" in token or "leddin" in token or "leddata" in token:
        if "count" not in token:
            return "ws2812"
    if "statusled" in token and any(word in token for word in ("gpio", "pin")):
        return "status_led"

    if "battery" in token or "vbat" in token:
        if any(word in token for word in ("enable", "senen")):
            return "battery_sense_enable"
        if any(word in token for word in ("adc", "sense", "vbat")):
            return "battery_sense_adc"
    if "externalpower" in token or "vinsense" in token or "senvin" in token:
        return "external_power_sense"
    if "charge" in token or "chrg" in token:
        if any(word in token for word in ("gpio", "pin", "status", "sense", "chrg")):
            return "charge_status"

    if (
        ("peripheral" in token and "power" in token)
        or "sharedpower" in token
        or "sharedrail" in token
        or "pwren" in token
    ):
        if "active" in token:
            return "peripheral_power_active_level"
        if any(word in token for word in ("gpio", "pin", "enable")):
            return "peripheral_power"

    if "mic" in token or "microphone" in token:
        if "bclk" in token or "bck" in token:
            return "mic_bclk"
        if "ws" in token or "lrclk" in token:
            return "mic_ws"
        if "data" in token or "din" in token:
            return "mic_data"
    if "speaker" in token or "spk" in token:
        if "bclk" in token or "bck" in token:
            return "speaker_bclk"
        if "ws" in token or "lrclk" in token:
            return "speaker_ws"
        if "data" in token or "dout" in token or "sdout" in token:
            return "speaker_data"

    return None


def _flatten_numbers(
    value: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], int]]:
    if isinstance(value, bool):
        yield path, int(value)
        return
    if isinstance(value, int):
        yield path, value
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten_numbers(item, path + (str(index),))
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _flatten_numbers(item, path + (str(key),))


def _integer_at(mapping: Mapping[str, Any], names: Sequence[str]) -> int | None:
    for name in names:
        value = mapping.get(name)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
    return None


def _aliases_from_contract(raw: Mapping[str, Any]) -> list[str]:
    aliases: list[str] = []
    candidates: list[Any] = [raw.get("aliases")]
    board = raw.get("board")
    if isinstance(board, Mapping):
        candidates.extend(
            [board.get("aliases"), board.get("name"), board.get("canonical_name")]
        )
    for candidate in candidates:
        if isinstance(candidate, str):
            aliases.append(candidate)
        elif isinstance(candidate, list):
            aliases.extend(item for item in candidate if isinstance(item, str))
        elif isinstance(candidate, Mapping):
            for item in candidate.values():
                if isinstance(item, str):
                    aliases.append(item)
                elif isinstance(item, list):
                    aliases.extend(part for part in item if isinstance(part, str))
    return list(dict.fromkeys(aliases))


def load_contract(path: Path) -> BoardContract:
    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"board contract does not exist: {path}") from error
    except OSError as error:
        raise ValueError(f"cannot read board contract {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid JSON in board contract {path}:{error.lineno}:{error.colno}: "
            f"{error.msg}"
        ) from error
    if not isinstance(raw_value, Mapping):
        raise ValueError("board contract root must be a JSON object")
    raw: Mapping[str, Any] = raw_value

    expected: dict[str, int] = {}
    sources: dict[str, str] = {}

    def register(fact: str | None, value: int, source: str) -> None:
        if fact is None:
            return
        if fact in expected and expected[fact] != value:
            raise ValueError(
                f"conflicting {fact} values in board contract: "
                f"{expected[fact]} ({sources[fact]}) vs {value} ({source})"
            )
        expected[fact] = value
        sources[fact] = source

    pins = raw.get("pins")
    if isinstance(pins, Mapping) or isinstance(pins, list):
        for parts, value in _flatten_numbers(pins, ("pins",)):
            leaf = _normalized(parts[-1]) if parts else ""
            if leaf in {
                "charginglevel",
                "fulllevel",
                "silkscreen",
                "count",
                "i2sport",
                "sampleratehz",
            }:
                continue
            # Support compact arrays: {"keys": [2, 47, ...]}.
            if len(parts) >= 2 and parts[-1].isdigit() and "keys" in {
                _normalized(part) for part in parts
            }:
                index = int(parts[-1])
                if 0 <= index < 8:
                    register(f"key{index + 1}", value, ".".join(parts))
                    continue
            register(
                _fact_for_name(".".join(parts), contract_path=True),
                value,
                ".".join(parts),
            )

    power = raw.get("power")
    if isinstance(power, Mapping):
        power_gpio = _integer_at(power, ("gpio", "enable_gpio", "pin"))
        if power_gpio is not None:
            register("peripheral_power", power_gpio, "power.gpio")
        active = _integer_at(
            power, ("active_level", "enable_active_level", "active_high")
        )
        if active is not None:
            register("peripheral_power_active_level", active, "power.active_level")

    boot = raw.get("boot")
    if isinstance(boot, Mapping):
        gpio = _integer_at(boot, ("gpio", "pin", "boot_gpio"))
        if gpio is not None:
            register("boot0", gpio, "boot.gpio")

    usb = raw.get("usb")
    if isinstance(usb, Mapping):
        dn = _integer_at(usb, ("dn_gpio", "d_minus_gpio", "dminus_gpio", "dn"))
        dp = _integer_at(usb, ("dp_gpio", "d_plus_gpio", "dplus_gpio", "dp"))
        if dn is not None:
            register("usb_dn", dn, "usb.dn_gpio")
        if dp is not None:
            register("usb_dp", dp, "usb.dp_gpio")

    required = {
        "boot0",
        "peripheral_power",
        "peripheral_power_active_level",
        "usb_dn",
        "usb_dp",
    }
    missing = sorted(required - expected.keys())
    if missing:
        raise ValueError(
            "board contract is missing required fields: " + ", ".join(missing)
        )

    return BoardContract(
        path=path.resolve(),
        expected=expected,
        board_aliases=_aliases_from_contract(raw),
        raw=raw,
    )


def collect_sources(root: Path) -> list[SourceFile]:
    sources: list[SourceFile] = []
    paths: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name.lower() not in EXCLUDED_DIR_NAMES
            and not name.lower().startswith("build")
        ]
        base = Path(directory)
        for filename in filenames:
            path = base / filename
            if (
                path.suffix.lower() in SOURCE_SUFFIXES
                or path.name in SPECIAL_SOURCE_NAMES
            ):
                paths.append(path)
    for path in sorted(paths):
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sources.append(SourceFile(path=path, text=text))
    return sources


def _conditional_compilation_lines(text: str) -> set[int]:
    """Return lines whose build inclusion cannot be proven statically.

    The checker intentionally does not guess preprocessor values.  Declarations
    inside any conditional block are excluded from PASS/FAIL decisions and are
    surfaced as an explicit warning instead.  A future compile-commands aware
    frontend can select those branches without teaching this board checker any
    project-private macro names.
    """

    conditional: set[int] = set()
    depth = 0
    directive_re = re.compile(r"\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b")
    for line_number, line in enumerate(text.splitlines(), start=1):
        directive = directive_re.match(line)
        if directive:
            conditional.add(line_number)
            kind = directive.group(1)
            if kind in {"if", "ifdef", "ifndef"}:
                depth += 1
            elif kind == "endif":
                depth = max(0, depth - 1)
            continue
        if depth > 0:
            conditional.add(line_number)
    return conditional


def _strip_comments(text: str) -> str:
    def blank(match: re.Match[str]) -> str:
        value = match.group(0)
        return "".join("\n" if char == "\n" else " " for char in value)

    return re.sub(r"//[^\n]*|/\*.*?\*/", blank, text, flags=re.DOTALL)


_NUMBER = r"\(?\s*(?:GPIO_NUM_)?\s*(-?\d+)\s*[uUlL]*\s*\)?"


def _line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def extract_occurrences(
    sources: Sequence[SourceFile],
) -> tuple[list[Occurrence], list[Occurrence], list[Occurrence]]:
    facts: list[Occurrence] = []
    raw_pin_declarations: list[Occurrence] = []
    conditional_declarations: list[Occurrence] = []
    seen: set[tuple[Path, int, str, int]] = set()
    conditional_seen: set[tuple[Path, int, str, int]] = set()

    def add(
        path: Path,
        text: str,
        offset: int,
        symbol: str,
        value: int,
        conditional_lines: set[int],
    ) -> None:
        line = _line_at(text, offset)
        raw_fact = _fact_for_name(symbol)
        is_pin_declaration = bool(
            re.search(r"(?:^|_)(?:gpio|pin)s?(?:_|$)", symbol, flags=re.IGNORECASE)
            or re.search(r"(?:GPIO|Pins?)(?:[A-Z0-9_]|$)", symbol)
        )
        is_board_scalar = raw_fact in LEVEL_FACTS or raw_fact == "ws2812_count"
        if line in conditional_lines and (is_pin_declaration or is_board_scalar):
            conditional_key = (path, line, symbol, value)
            if conditional_key not in conditional_seen:
                conditional_declarations.append(
                    Occurrence(raw_fact or "", value, symbol, path, line)
                )
                conditional_seen.add(conditional_key)
            return
        if is_pin_declaration:
            raw_key = (path, line, symbol, value)
            if raw_key not in seen:
                raw_pin_declarations.append(
                    Occurrence(raw_fact or "", value, symbol, path, line)
                )
                seen.add(raw_key)
        if raw_fact and (is_pin_declaration or is_board_scalar):
            fact_key = (path, line, raw_fact, value)
            if fact_key not in seen:
                facts.append(Occurrence(raw_fact, value, symbol, path, line))
                seen.add(fact_key)

    macro_re = re.compile(
        rf"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+{_NUMBER}(?=\s|$)"
    )
    assignment_re = re.compile(
        rf"\b([A-Za-z_]\w*)\s*=\s*{_NUMBER}(?=\s*[,;}}])"
    )
    named_key_re = re.compile(
        r"\{\s*[\"'](?:KEY|S)([1-8])[\"']\s*,\s*(?:GPIO_NUM_)?\s*(\d+)\s*[uUlL]*\s*\}",
        flags=re.IGNORECASE,
    )
    for source in sources:
        text = _strip_comments(source.text)
        conditional_lines = _conditional_compilation_lines(text)
        for pattern in (macro_re, assignment_re):
            for match in pattern.finditer(text):
                add(
                    source.path,
                    text,
                    match.start(),
                    match.group(1),
                    int(match.group(2)),
                    conditional_lines,
                )

        for match in named_key_re.finditer(text):
            add(
                source.path,
                text,
                match.start(),
                f"KEY{match.group(1)}_GPIO",
                int(match.group(2)),
                conditional_lines,
            )

    return facts, raw_pin_declarations, conditional_declarations


def _is_idf_project(sources: Sequence[SourceFile]) -> bool:
    for source in sources:
        if source.path.name == "CMakeLists.txt" and (
            "IDF_PATH" in source.text or "project.cmake" in source.text
        ):
            return True
        if source.path.name.startswith("sdkconfig") and "CONFIG_IDF_TARGET" in source.text:
            return True
    return False


def _format_fact(fact: str) -> str:
    return fact.upper().replace("_", " ")


def _format_fact_value(fact: str, value: int) -> str:
    if fact in LEVEL_FACTS:
        return f"level {value}"
    if fact == "ws2812_count":
        return str(value)
    return f"GPIO{value}"


def _audit_pin_facts(
    report: AuditReport,
    occurrences: Sequence[Occurrence],
    raw_declarations: Sequence[Occurrence],
) -> None:
    by_fact: dict[str, list[Occurrence]] = {}
    for occurrence in occurrences:
        by_fact.setdefault(occurrence.fact, []).append(occurrence)

    checked = 0
    for fact, expected in report.contract.expected.items():
        present = by_fact.get(fact, [])
        if not present:
            continue
        checked += 1
        wrong = [item for item in present if item.value != expected]
        if wrong:
            for item in wrong:
                report.add(
                    "FAIL",
                    "PIN_DRIFT",
                    f"{item.symbol} is {_format_fact_value(fact, item.value)}; "
                    f"board contract requires {_format_fact(fact)}="
                    f"{_format_fact_value(fact, expected)}",
                    item.location(report.root),
                )
        else:
            representative = present[0]
            report.add(
                "PASS",
                "PIN_MATCH",
                f"{_format_fact(fact)} matches {_format_fact_value(fact, expected)}",
                representative.location(report.root),
            )

    if checked == 0:
        report.add(
            "WARN",
            "PIN_DECLARATIONS_NOT_FOUND",
            "No recognizable EasyInput board-pin declarations were found; "
            "unused peripherals are allowed, but pin drift cannot be assessed.",
        )

    boot_gpio = report.contract.expected["boot0"]
    usb_gpios = {
        report.contract.expected["usb_dn"],
        report.contract.expected["usb_dp"],
    }
    for item in raw_declarations:
        symbol = _normalized(item.symbol)
        if item.value == boot_gpio:
            allowed_boot = any(
                word in symbol for word in ("boot", "download", "strap", "gpio0")
            )
            ordinary_input = any(
                word in symbol
                for word in ("key", "button", "btn", "encoder", "input", "switch")
            )
            if ordinary_input and not allowed_boot:
                report.add(
                    "FAIL",
                    "BOOT_GPIO_REUSED",
                    f"{item.symbol} assigns BOOT GPIO{boot_gpio} to an ordinary input",
                    item.location(report.root),
                )
        if item.value in usb_gpios:
            allowed_usb = any(
                word in symbol
                for word in (
                    "usb",
                    "dplus",
                    "dminus",
                    "dpgpio",
                    "dppin",
                    "dngpio",
                    "dnpin",
                    "jtag",
                )
            )
            if not allowed_usb:
                report.add(
                    "FAIL",
                    "USB_GPIO_REUSED",
                    f"{item.symbol} uses reserved native-USB GPIO{item.value}",
                    item.location(report.root),
                )

    power_gpio = report.contract.expected["peripheral_power"]
    for item in raw_declarations:
        symbol = _normalized(item.symbol)
        if item.value == power_gpio and "led" in symbol and "power" in symbol:
            if not any(word in symbol for word in ("peripheral", "shared", "rail")):
                report.add(
                    "WARN",
                    "GPIO8_LED_ONLY_ALIAS",
                    f"{item.symbol} describes GPIO{power_gpio} as LED-only; it powers "
                    "the shared LED/MIC/speaker rail. The name alone does not prove a "
                    "runtime electrical violation.",
                    item.location(report.root),
                )


def _power_related(text: str) -> bool:
    token = _normalized(text)
    return any(
        marker in token
        for marker in (
            "peripheralpower",
            "sharedrail",
            "sharedpower",
            "pwren",
            "powerenablepin",
            "powerenablegpio",
        )
    )


def _audit_power(
    report: AuditReport,
    sources: Sequence[SourceFile],
    occurrences: Sequence[Occurrence],
) -> None:
    by_fact: dict[str, list[Occurrence]] = {}
    for occurrence in occurrences:
        by_fact.setdefault(occurrence.fact, []).append(occurrence)

    has_power_declaration = "peripheral_power" in by_fact
    if not has_power_declaration:
        # Pin declarations are inventory, not proof that an application enables
        # or drives the corresponding peripheral.  Without an explicit usage
        # declaration or selected build graph, no runtime power claim is safe.
        return

    expected_power = report.contract.expected["peripheral_power"]
    expected_active = report.contract.expected["peripheral_power_active_level"]
    power_values = {item.value for item in by_fact.get("peripheral_power", [])}
    if power_values == {expected_power}:
        report.add(
            "PASS",
            "SHARED_POWER_GPIO",
            f"Shared LED/MIC/speaker rail enable matches GPIO{expected_power}.",
        )

    active_values = {
        item.value for item in by_fact.get("peripheral_power_active_level", [])
    }
    if active_values:
        if active_values == {expected_active}:
            report.add(
                "PASS",
                "SHARED_POWER_POLARITY",
                f"GPIO{expected_power} shared power is declared active-high.",
            )
        # A mismatched value is already reported by PIN_DRIFT.
    else:
        report.add(
            "WARN",
            "SHARED_POWER_POLARITY_UNKNOWN",
            f"GPIO{expected_power} is declared, but its active-high polarity is not explicit.",
        )

    power_sources = [source for source in sources if _power_related(source.text)]
    enable_sources = [
        source
        for source in power_sources
        if re.search(r"\bgpio_set_level\s*\(", _strip_comments(source.text))
    ]
    if enable_sources:
        source = enable_sources[0]
        text = _strip_comments(source.text)
        match = re.search(r"\bgpio_set_level\s*\(", text)
        location: str | None = None
        if match is not None:
            try:
                relative = source.path.relative_to(report.root)
            except ValueError:
                relative = source.path
            location = f"{relative}:{_line_at(text, match.start())}"
        report.add(
            "WARN",
            "POWER_SEQUENCE_UNPROVEN",
            "Shared-rail GPIO control was found, but this static checker does not infer "
            "power-up ordering or settle time from unrelated delays, helper names, or "
            "comments. Verify the selected runtime path by code review or HIL.",
            location,
        )


def audit_project(root: Path, contract: BoardContract) -> AuditReport:
    sources = collect_sources(root)
    report = AuditReport(root=root, contract=contract)
    if _is_idf_project(sources):
        report.add("PASS", "ESP_IDF_PROJECT", "ESP-IDF project markers found.")
    else:
        report.add(
            "WARN",
            "ESP_IDF_MARKER_NOT_FOUND",
            "No ESP-IDF project marker was found; source files were still audited.",
        )

    occurrences, raw_declarations, conditional_declarations = extract_occurrences(sources)
    if conditional_declarations:
        representative = conditional_declarations[0]
        report.add(
            "WARN",
            "BUILD_BRANCH_UNSELECTED",
            f"Found {len(conditional_declarations)} recognizable board declaration(s) "
            "inside conditional compilation. No build configuration was supplied, so "
            "those declarations were excluded from PASS/FAIL decisions.",
            representative.location(root),
        )

    _audit_pin_facts(report, occurrences, raw_declarations)
    _audit_power(report, sources, occurrences)
    return report


def print_report(report: AuditReport) -> None:
    print("EasyInput board baseline audit")
    print(f"Contract: {report.contract.path}")
    print()
    for finding in report.findings:
        suffix = f" ({finding.location})" if finding.location else ""
        print(f"[{finding.level}] {finding.code}: {finding.message}{suffix}")
    counts = {
        level: sum(item.level == level for item in report.findings)
        for level in ("PASS", "WARN", "FAIL")
    }
    print()
    print(
        "Summary: "
        f"{counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL"
    )


def build_parser() -> argparse.ArgumentParser:
    default_contract = (
        Path(__file__).resolve().parent.parent / "references" / "board-contract.json"
    )
    parser = argparse.ArgumentParser(
        description="Audit an ESP-IDF project against the EasyInput V2 board contract."
    )
    parser.add_argument("project", type=Path, help="project or repository directory")
    parser.add_argument(
        "--contract",
        type=Path,
        default=default_contract,
        help=f"board-contract JSON (default: {default_contract})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project.expanduser()
    if not project.exists():
        parser.error(f"project path does not exist: {project}")
    if not project.is_dir():
        parser.error(f"project path is not a directory: {project}")
    contract_path = args.contract.expanduser()
    try:
        contract = load_contract(contract_path)
    except ValueError as error:
        parser.error(str(error))

    report = audit_project(project.resolve(), contract)
    print_report(report)
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
