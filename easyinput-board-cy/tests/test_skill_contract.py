#!/usr/bin/env python3
"""Deterministic contract checks for easyinput-board-cy."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
DESIGN = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
ASSET_LICENSE = (ROOT / "ASSET-LICENSE.md").read_text(encoding="utf-8")
NOTICE = (ROOT / "NOTICE").read_text(encoding="utf-8")
SOURCE_MAP = (ROOT / "references" / "source-map.md").read_text(encoding="utf-8")
IDENTITY = (ROOT / "references" / "identity-and-authority.md").read_text(
    encoding="utf-8"
)
OPENAI = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
EVALS = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
SOURCE_MANIFEST = json.loads(
    (ROOT / "references" / "source-manifest.json").read_text(encoding="utf-8")
)
RENDER_MANIFEST = json.loads(
    (ROOT / "assets" / "readme" / "render" / "manifest.json").read_text(
        encoding="utf-8"
    )
)
PAGE_MANIFEST = json.loads(
    (ROOT / "assets" / "readme" / "page" / "manifest.json").read_text(
        encoding="utf-8"
    )
)
HERO_SOURCE = (ROOT / "assets" / "readme" / "source" / "hero.html").read_text(
    encoding="utf-8"
)


def require(text: str) -> None:
    if text not in SKILL:
        raise AssertionError(f"missing skill contract: {text}")


def main() -> None:
    match = re.match(r"\A---\n(.*?)\n---\n", SKILL, flags=re.DOTALL)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    frontmatter = match.group(1)
    if "name: easyinput-board-cy" not in frontmatter:
        raise AssertionError("wrong skill name")

    license_bytes = (ROOT / "LICENSE").read_bytes()
    license_text = license_bytes.decode("utf-8")
    for license_marker in (
        "# PolyForm Noncommercial License 1.0.0",
        "https://polyformproject.org/licenses/noncommercial/1.0.0",
        "## Noncommercial Purposes",
        "## Personal Uses",
        "## Noncommercial Organizations",
        "## Distribution License",
        "## Changes and New Works License",
    ):
        if license_marker not in license_text:
            raise AssertionError(f"missing PolyForm license marker: {license_marker}")
    expected_license_sha256 = (
        "c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5"
    )
    if hashlib.sha256(license_bytes).hexdigest() != expected_license_sha256:
        raise AssertionError("PolyForm license text must remain the unmodified official text")
    if "Apache License" in license_text:
        raise AssertionError("current LICENSE must not imply Apache-2.0 dual licensing")

    for release_marker in (
        "https://github.com/CY-CHENYUE/easyinput-board-cy.git",
        "[PolyForm-Noncommercial-1.0.0](LICENSE)",
        "本项目属于 source-available，不是 OSI 开源项目",
        "本次换证不撤回既有许可",
        "法定合理使用不受影响",
        "基于这些事实独立编写的固件不会仅因参考本 Skill 自动受该许可约束",
        "[CC BY-NC 4.0](ASSET-LICENSE.md)",
        "[NOTICE](NOTICE)",
        "含 Logo 的 PCB 快照及其 Hero／审阅渲染",
        "品牌版原理图与整页预览属于混合资产",
        'src="assets/wechat-qr.jpg"',
    ):
        if release_marker not in README:
            raise AssertionError(f"missing public release marker: {release_marker}")
    public_readme = README.casefold()
    for internal_marker in (
        "唯一编辑源",
        "公开发布镜像",
        "canonical source",
        "cc-skills",
        "本地总库",
        "总库维护",
        "发布镜像",
        "同步产物",
        "软链接",
        "symlink",
        "ln -s",
        "如果你在维护完整的 `cc-skills` 总库",
    ):
        if internal_marker.casefold() in public_readme:
            raise AssertionError(
                f"public README leaked internal repository governance: {internal_marker}"
            )
    if not (ROOT / "assets" / "wechat-qr.jpg").is_file():
        raise AssertionError("missing README QR asset")

    exact_notice = (
        "Required Notice: Copyright © 2026 CY-CHENYUE. Software and "
        "documentation use PolyForm-Noncommercial-1.0.0; image and diagram "
        "assets listed as covered in ASSET-LICENSE.md use CC-BY-NC-4.0.\n"
    )
    if NOTICE != exact_notice:
        raise AssertionError("NOTICE must preserve the exact Required Notice line")

    covered_asset_paths = {
        "assets/easyinput-v2-schematic-page-1.png",
        "assets/easyinput-v2-schematic-page-2.png",
        "assets/readme/sections/boot-flow.svg",
        "assets/readme/sections/gpio8-shared-rail.svg",
        "assets/readme/sections/verification-ladder.svg",
    }
    mixed_asset_paths = {
        "assets/easyinput-v2-schematic-page-1-branded.svg",
        "assets/easyinput-v2-schematic-page-2-branded.svg",
        "assets/easyinput-v2-schematic-page-1-branded.png",
        "assets/easyinput-v2-schematic-page-2-branded.png",
        "assets/easyinput-v2-pcb-top.png",
        "assets/easyinput-v2-pcb-bottom.png",
        "assets/readme/render/hero.png",
        "assets/readme/render/review-board.png",
        "assets/readme/render/github-light.png",
        "assets/readme/render/github-dark.png",
        "assets/readme/render/preview-900.png",
        "assets/readme/render/preview-360.png",
        "assets/readme/render/preview-240.png",
        "assets/readme/page/desktop.png",
        "assets/readme/page/mobile.png",
    }
    excluded_asset_paths = {
        "assets/brand-wuqiwangxiang-black.png",
        "assets/brand-waytoagi-black.png",
        "assets/wechat-qr.jpg",
    }
    for asset_marker in (
        "https://creativecommons.org/licenses/by-nc/4.0/legalcode",
        "`CC-BY-NC-4.0`",
        "Attribution: **EasyInput / CY-CHENYUE**",
        "indicating changes",
        "do not have one license for the file as a whole",
        "Standard license texts remain governed by their own notices",
    ):
        if asset_marker not in ASSET_LICENSE:
            raise AssertionError(f"missing asset-license marker: {asset_marker}")
    covered_section = ASSET_LICENSE.split(
        "## Covered project-authored rights", 1
    )[1].split("## Mixed assets", 1)[0]
    mixed_section = ASSET_LICENSE.split("## Mixed assets", 1)[1].split(
        "## Excluded assets and rights", 1
    )[0]
    excluded_section = ASSET_LICENSE.split("## Excluded assets and rights", 1)[
        1
    ].split("## Hardware and factual boundaries", 1)[0]

    def listed_paths(section: str) -> set[str]:
        return set(re.findall(r"^- `([^`]+)`$", section, flags=re.MULTILINE))

    if listed_paths(covered_section) != covered_asset_paths:
        raise AssertionError("ASSET-LICENSE covered section scope drift")
    if listed_paths(mixed_section) != mixed_asset_paths:
        raise AssertionError("ASSET-LICENSE mixed section scope drift")
    if listed_paths(excluded_section) != excluded_asset_paths:
        raise AssertionError("ASSET-LICENSE excluded section scope drift")
    image_suffixes = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
    public_image_inventory = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "assets").rglob("*")
        if path.is_file() and path.suffix.casefold() in image_suffixes
    }
    classified_image_inventory = (
        covered_asset_paths | mixed_asset_paths | excluded_asset_paths
    )
    if public_image_inventory != classified_image_inventory:
        missing = sorted(public_image_inventory - classified_image_inventory)
        stale = sorted(classified_image_inventory - public_image_inventory)
        raise AssertionError(
            f"public image license inventory drift: unclassified={missing}, stale={stale}"
        )

    for phrase in (
        "EasyInput 当前开发板知识与 AI 上下文",
        "本 Skill 的职责在交付开发板硬件事实、证据边界和安全约束时结束。",
        "作为开发上下文时，把整理结果交还给总体开发任务",
        "本 Skill 不创建或初始化 ESP-IDF 工程，不编写或修改业务代码，不选择项目架构，也不负责 build、flash、monitor 或 HIL。",
        "产品/课程名称：`EasyInput V2.0`",
        "固件板型别名：`v2`",
        "PCB 丝印：`AI Keyboard V2.1`",
        "短按并松开一次 BOOT",
        "不需要按住 BOOT",
        "退出下载模式只需关机一次，再重新开机",
        "板上没有独立的用户 RESET/EN 按键",
        "S1–S8 固定为 GPIO `2, 47, 38, 41, 1, 6, 7, 48`",
        "GPIO8 是高有效的 LED/MIC/SPK 共享电源域",
        "当前资料不能证明统一的最短稳定时间",
        "原生 USB 使用 GPIO19/20",
        "本 Skill 只提供当前板专属事实，不构成执行或写入授权",
        "没有相应证据时不要升级结论",
    ):
        require(phrase)

    for phrase in (
        "EasyInput V2.0 开发板知识与 AI 开发上下文",
        "它本身不负责创建项目、编写或修改代码、安装工具链、构建、烧录或监视串口。",
        "创建项目、写代码和后续验证仍属于外部开发任务",
        "将开发板上下文交还给查询者或外部开发任务",
    ):
        if phrase not in README:
            raise AssertionError(f"missing README context-only contract: {phrase}")

    for forbidden in (
        "按住 BOOT →",
        "KEY5=GPIO0",
        "PWR_EN=GPIO7",
        "/dev/cu.usbmodem101` 作为",
    ):
        if forbidden in SKILL:
            raise AssertionError(f"stale contract leaked into skill: {forbidden}")

    legacy_execution_claims = (
        "项目中立板级固件开发 Skill",
        "**实现最小板级改动**",
        "先跑项目已有 host/unit tests，再构建目标工程",
        "为当前板建立一个独立的硬件自检项目",
        "基于板级硬件合同设计一个独立 ESP-IDF 项目",
    )
    for claim in legacy_execution_claims:
        for name, content in (
            ("SKILL.md", SKILL),
            ("README.md", README),
            ("agents/openai.yaml", OPENAI),
        ):
            if claim in content:
                raise AssertionError(
                    f"{name} still treats the context skill as an execution skill: {claim}"
                )

    for phrase in (
        "开发板知识、硬件资料与 AI 开发上下文，不是开发执行 Skill",
        "EasyInput V2.0 开发板的硬件资料、板级安全边界与 AI 开发上下文",
        "PolyForm-Noncommercial-1.0.0 与 CC-BY-NC-4.0 描述的是使用许可，不是 Skill 的售价",
        "source-available，不是 OSI 开源项目",
        "既有 Apache-2.0 版本继续按原许可有效",
        "品牌派生图与含 README 文字、Logo 或二维码的整页预览属于混合资产",
    ):
        if phrase not in DESIGN:
            raise AssertionError(f"missing durable design contract: {phrase}")

    forbidden_license_claims = (
        "仅限自然人",
        "只能自然人",
        "个人专用",
        "开源协议",
        "开源许可",
        "本项目开源",
    )
    for name, content in (("README.md", README), ("DESIGN.md", DESIGN)):
        for claim in forbidden_license_claims:
            if claim in content:
                raise AssertionError(
                    f"{name} contains a misleading PolyForm claim: {claim}"
                )

    legacy_board_card_term = "\u677f\u5361"
    terminology_surfaces = [
        ROOT / "SKILL.md",
        ROOT / "README.md",
        ROOT / "DESIGN.md",
        ROOT / "agents" / "openai.yaml",
        ROOT / "evals" / "evals.json",
        ROOT / "assets" / "readme" / "source" / "hero.html",
        ROOT / "assets" / "readme" / "visual-review.json",
        ROOT / "assets" / "readme" / "render" / "manifest.json",
        ROOT / "assets" / "readme" / "page" / "index.html",
        *(ROOT / "references").glob("*.md"),
    ]
    for path in terminology_surfaces:
        if legacy_board_card_term in path.read_text(encoding="utf-8"):
            raise AssertionError(
                f"{path.relative_to(ROOT)} still uses the retired product noun"
            )

    authority_sections = {
        "SKILL.md": SKILL.split("## 事实冲突处理", 1)[1].split("## 项目边界", 1)[0],
        "identity-and-authority.md": IDENTITY.split("## 冲突时的优先级", 1)[1].split(
            "## 不属于板级合同的内容", 1
        )[0],
    }
    for name, section in authority_sections.items():
        original_evidence = section.index(
            "可追溯的当前批次 ECAD/BOM/装配资料与板级专项测试"
        )
        machine_contract = section.index("board-contract.json")
        if original_evidence > machine_contract or "不能自证正确" not in section:
            raise AssertionError(
                f"{name} must keep original evidence above the normalized machine contract"
            )

    cases = EVALS["evals"]
    ids = [case["id"] for case in cases]
    if ids != list(range(1, 9)):
        raise AssertionError(f"unexpected eval ids: {ids}")
    for case in cases:
        if len(case.get("assertions", [])) < 4:
            raise AssertionError(f"eval {case['id']} needs at least four assertions")
        if case.get("files") != []:
            raise AssertionError(
                f"eval {case['id']} must remain context-only and produce no files"
            )

    for case_id in (1, 7, 8):
        case = cases[case_id - 1]
        expected = case["expected_output"]
        if "交还" not in expected or "本 Skill 不" not in expected:
            raise AssertionError(
                f"eval {case_id} must hand context back without claiming execution"
            )

    for reference in (
        "identity-and-authority.md",
        "pinout.md",
        "boot-flash-recovery.md",
        "power-and-peripherals.md",
        "project-boundaries.md",
        "known-gaps-and-errata.md",
        "source-map.md",
        "source-manifest.json",
        "board-contract.json",
    ):
        if not (ROOT / "references" / reference).is_file():
            raise AssertionError(f"missing reference: {reference}")

    expected_manifest_group_paths = {
        "packaged_assets": {
            "../assets/easyinput-v2-schematic-page-1.png",
            "../assets/easyinput-v2-schematic-page-2.png",
            "../assets/easyinput-v2-pcb-top.png",
            "../assets/easyinput-v2-pcb-bottom.png",
        },
        "branding_inputs": {
            "../assets/brand-wuqiwangxiang-black.png",
            "../assets/brand-waytoagi-black.png",
        },
        "presentation_derivatives": {
            "../assets/easyinput-v2-schematic-page-1-branded.svg",
            "../assets/easyinput-v2-schematic-page-2-branded.svg",
            "../assets/easyinput-v2-schematic-page-1-branded.png",
            "../assets/easyinput-v2-schematic-page-2-branded.png",
            "../assets/schematic-branding-preview.html",
        },
        "excluded_asset_records": {"../assets/wechat-qr.jpg"},
    }

    def png_dimensions(payload: bytes) -> list[int]:
        if payload[:8] != b"\x89PNG\r\n\x1a\n":
            raise AssertionError("expected PNG payload")
        return [
            int.from_bytes(payload[16:20], "big"),
            int.from_bytes(payload[20:24], "big"),
        ]

    for group in (
        "packaged_assets",
        "branding_inputs",
        "presentation_derivatives",
        "excluded_asset_records",
    ):
        actual_group_paths = {asset["path"] for asset in SOURCE_MANIFEST[group]}
        if (
            actual_group_paths != expected_manifest_group_paths[group]
            or len(SOURCE_MANIFEST[group]) != len(expected_manifest_group_paths[group])
        ):
            raise AssertionError(f"source-manifest {group} path-set drift")
        for asset in SOURCE_MANIFEST[group]:
            path = (ROOT / "references" / asset["path"]).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError as exc:
                raise AssertionError(f"asset escapes skill root: {asset['path']}") from exc
            if not path.is_file():
                raise AssertionError(f"missing manifested asset: {asset['path']}")
            payload = path.read_bytes()
            if len(payload) != asset["bytes"]:
                raise AssertionError(f"asset size drift: {asset['path']}")
            digest = hashlib.sha256(payload).hexdigest()
            if digest != asset["sha256"]:
                raise AssertionError(f"asset hash drift: {asset['path']}")
            if path.suffix.casefold() == ".png" and "width" in asset:
                if png_dimensions(payload) != [asset["width"], asset["height"]]:
                    raise AssertionError(f"asset dimension drift: {asset['path']}")

    licensing = SOURCE_MANIFEST["rights_and_licensing"]
    if SOURCE_MANIFEST["schema_version"] != 2:
        raise AssertionError("source manifest must use the path-license schema v2")
    if licensing["software_spdx"] != "PolyForm-Noncommercial-1.0.0":
        raise AssertionError("wrong software license in source manifest")
    if licensing["asset_spdx"] != "CC-BY-NC-4.0":
        raise AssertionError("wrong covered-asset license in source manifest")
    expected_licensing_contract = {
        "software_license_path": "../LICENSE",
        "software_spdx": "PolyForm-Noncommercial-1.0.0",
        "required_notice_path": "../NOTICE",
        "asset_license_path": "../ASSET-LICENSE.md",
        "asset_spdx": "CC-BY-NC-4.0",
        "asset_spdx_scope": "covered_project_authored_rights_and_mixed_asset_components_only",
        "attribution": "EasyInput / CY-CHENYUE",
        "scope_limit": "only_to_the_extent_the_repository_licensor_owns_or_is_authorized_to_license_the_applicable_rights",
    }
    for key, expected in expected_licensing_contract.items():
        if licensing.get(key) != expected:
            raise AssertionError(f"source-manifest licensing contract drift: {key}")
    for key in ("software_license_path", "required_notice_path", "asset_license_path"):
        if not (ROOT / "references" / licensing[key]).resolve().is_file():
            raise AssertionError(f"source-manifest license path is missing: {key}")
    manifested_mixed = {
        Path(path).as_posix().removeprefix("../")
        for path in licensing["mixed_assets"]
    }
    manifested_excluded = {
        Path(path).as_posix().removeprefix("../")
        for path in licensing["excluded_assets"]
    }
    if manifested_mixed != mixed_asset_paths:
        raise AssertionError("mixed-asset manifest scope drift")
    if manifested_excluded != excluded_asset_paths:
        raise AssertionError("excluded-asset manifest scope drift")
    if licensing.get("excluded_rights_categories") != [
        "brand_and_trademark_rights",
        "contact_qr_reuse_rights",
        "third_party_embedded_material",
    ]:
        raise AssertionError("excluded rights-category manifest drift")

    manifested_covered = set()
    for asset in SOURCE_MANIFEST["packaged_assets"]:
        normalized = Path(asset["path"]).as_posix().removeprefix("../")
        if normalized in {
            "assets/easyinput-v2-schematic-page-1.png",
            "assets/easyinput-v2-schematic-page-2.png",
        }:
            if asset["license"] != "CC-BY-NC-4.0" or asset["asset_license_scope"] != "covered":
                raise AssertionError(f"schematic asset lost CC scope: {asset['path']}")
            if asset.get("attribution") != "EasyInput / CY-CHENYUE":
                raise AssertionError(f"schematic attribution drift: {asset['path']}")
            if asset.get("rights_status") != "license_grant_limited_to_licensor_owned_or_authorized_components":
                raise AssertionError(f"schematic rights limit drift: {asset['path']}")
            manifested_covered.add(normalized)
        elif normalized in {
            "assets/easyinput-v2-pcb-top.png",
            "assets/easyinput-v2-pcb-bottom.png",
        }:
            if asset["license"] != "NOASSERTION" or asset["asset_license_scope"] != "mixed":
                raise AssertionError(f"PCB with embedded Logo must remain mixed: {asset['path']}")
            if asset.get("rights_status") != "mixed_asset_components_retain_separate_rights":
                raise AssertionError(f"PCB rights status drift: {asset['path']}")
            if asset.get("component_licenses") != {
                "project_authored_pcb_and_snapshot_expression": "CC-BY-NC-4.0",
                "embedded_brand_mark_and_other_third_party_components": "NOASSERTION",
            }:
                raise AssertionError(f"PCB component license drift: {asset['path']}")
            if asset.get("attribution_for_cc_components") != "EasyInput / CY-CHENYUE":
                raise AssertionError(f"PCB component attribution drift: {asset['path']}")
        else:
            raise AssertionError(f"unexpected packaged asset: {asset['path']}")

    for asset in SOURCE_MANIFEST["branding_inputs"]:
        if asset["license"] != "NOASSERTION" or asset["asset_license_scope"] != "excluded":
            raise AssertionError(f"brand input must remain excluded: {asset['path']}")
        if asset.get("rights_status") != "separate_brand_and_trademark_rights_not_granted":
            raise AssertionError(f"brand rights status drift: {asset['path']}")

    for asset in SOURCE_MANIFEST["presentation_derivatives"]:
        if asset["path"].endswith((".svg", ".png")):
            if asset["license"] != "NOASSERTION" or asset["asset_license_scope"] != "mixed":
                raise AssertionError(f"branded derivative must remain mixed: {asset['path']}")
            if asset.get("rights_status") != "mixed_asset_components_retain_separate_rights":
                raise AssertionError(f"branded derivative rights drift: {asset['path']}")
            components = asset.get("component_licenses", {})
            if components != {
                "underlying_schematic_and_project_authored_treatment": "CC-BY-NC-4.0",
                "brand_marks": "NOASSERTION",
            }:
                raise AssertionError(f"branded derivative component map drift: {asset['path']}")
            if asset.get("excluded_components") != [
                "../assets/brand-wuqiwangxiang-black.png",
                "../assets/brand-waytoagi-black.png",
            ]:
                raise AssertionError(f"branded derivative exclusions drift: {asset['path']}")
        elif (
            asset["license"] != "PolyForm-Noncommercial-1.0.0"
            or asset.get("asset_license_scope") != "software"
            or asset.get("required_notice") != "../NOTICE"
            or asset.get("role") != "local_side_by_side_review_only"
        ):
            raise AssertionError(
                f"preview source software-license contract drift: {asset['path']}"
            )

    section_visual_paths = {
        "assets/readme/sections/boot-flow.svg",
        "assets/readme/sections/gpio8-shared-rail.svg",
        "assets/readme/sections/verification-ladder.svg",
    }
    mixed_render_paths = {
        "assets/readme/render/hero.png",
        "assets/readme/render/review-board.png",
        "assets/readme/render/github-light.png",
        "assets/readme/render/github-dark.png",
        "assets/readme/render/preview-900.png",
        "assets/readme/render/preview-360.png",
        "assets/readme/render/preview-240.png",
    }
    mixed_page_paths = {
        "assets/readme/page/desktop.png",
        "assets/readme/page/mobile.png",
    }
    if len(SOURCE_MANIFEST["generated_visual_asset_rules"]) != 3:
        raise AssertionError("generated visual license-rule count drift")
    seen_generated_rule_paths: set[frozenset[str]] = set()
    for rule in SOURCE_MANIFEST["generated_visual_asset_rules"]:
        paths = {Path(path).as_posix().removeprefix("../") for path in rule["paths"]}
        seen_generated_rule_paths.add(frozenset(paths))
        for path in rule["paths"]:
            resolved = (ROOT / "references" / path).resolve()
            if not resolved.is_file():
                raise AssertionError(f"missing generated visual asset: {path}")
        if paths == section_visual_paths:
            if rule["asset_license_scope"] != "covered" or rule["license"] != "CC-BY-NC-4.0":
                raise AssertionError("covered explanation visual lost CC license")
            if rule.get("rights_status") != "license_grant_limited_to_licensor_owned_or_authorized_components":
                raise AssertionError("explanation visual rights limit drift")
            if rule.get("attribution") != "EasyInput / CY-CHENYUE":
                raise AssertionError("explanation visual attribution drift")
            manifested_covered |= paths
        elif paths == mixed_render_paths:
            if rule["license"] != "NOASSERTION" or rule["asset_license_scope"] != "mixed":
                raise AssertionError("PCB-based render mixed scope drift")
            if rule.get("rights_status") != "mixed_asset_components_retain_separate_rights":
                raise AssertionError("PCB-based render rights status drift")
            if rule.get("component_licenses") != {
                "project_authored_render_and_pcb_expression": "CC-BY-NC-4.0",
                "embedded_brand_mark_and_other_unlicensed_components": "NOASSERTION",
            }:
                raise AssertionError("PCB-based render component map drift")
            if rule.get("attribution_for_cc_components") != "EasyInput / CY-CHENYUE":
                raise AssertionError("PCB-based render attribution drift")
        elif paths == mixed_page_paths:
            if rule["license"] != "NOASSERTION" or rule["asset_license_scope"] != "mixed":
                raise AssertionError("full-page preview mixed scope drift")
            if rule.get("component_licenses") != {
                "readme_text_and_page_code": "PolyForm-Noncommercial-1.0.0",
                "project_authored_visual_components": "CC-BY-NC-4.0",
                "logos_and_qr": "NOASSERTION",
            }:
                raise AssertionError("full-page preview component map drift")
            if rule.get("rights_status") != "mixed_asset_components_retain_separate_rights":
                raise AssertionError("full-page preview rights status drift")
        else:
            raise AssertionError("unknown generated visual path or license scope")

    if seen_generated_rule_paths != {
        frozenset(section_visual_paths),
        frozenset(mixed_render_paths),
        frozenset(mixed_page_paths),
    }:
        raise AssertionError("generated visual license-rule path-set drift")

    if manifested_covered != covered_asset_paths:
        raise AssertionError("covered-asset manifest scope drift")
    qr_record = SOURCE_MANIFEST["excluded_asset_records"]
    if len(qr_record) != 1 or qr_record[0]["path"] != "../assets/wechat-qr.jpg":
        raise AssertionError("excluded QR record drift")
    if qr_record[0]["license"] != "NOASSERTION":
        raise AssertionError("QR must not inherit a repository content license")
    if qr_record[0].get("asset_license_scope") != "excluded":
        raise AssertionError("QR scope must remain excluded")
    if qr_record[0].get("rights_status") != "contact_qr_separate_rights_not_granted":
        raise AssertionError("QR rights status drift")

    def verify_built_artifact(base: Path, record: dict) -> None:
        path = base / record["path"]
        payload = path.read_bytes()
        if len(payload) != record["bytes"]:
            raise AssertionError(f"generated artifact size drift: {path.relative_to(ROOT)}")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise AssertionError(f"generated artifact hash drift: {path.relative_to(ROOT)}")
        if "pixel_dimensions" in record and record["pixel_dimensions"] is not None:
            actual_dimensions = png_dimensions(payload)
            if actual_dimensions != record["pixel_dimensions"]:
                raise AssertionError(
                    f"generated artifact dimensions drift: {path.relative_to(ROOT)}"
                )

    render_base = ROOT / "assets" / "readme" / "render"
    render_artifacts = RENDER_MANIFEST["artifacts"]
    render_output_records = (
        render_artifacts["hero"],
        *render_artifacts["previews"],
        *render_artifacts["github_pages"]["themes"].values(),
        render_artifacts["review_board"],
    )
    if set(render_artifacts["github_pages"]["themes"]) != {"light", "dark"}:
        raise AssertionError("GitHub render theme set drift")
    expected_render_outputs = {
        "hero.png",
        "preview-900.png",
        "preview-360.png",
        "preview-240.png",
        "github-light.png",
        "github-dark.png",
        "review-board.png",
    }
    if (
        {record["path"] for record in render_output_records} != expected_render_outputs
        or len(render_output_records) != len(expected_render_outputs)
    ):
        raise AssertionError("Hero bundle output-set drift")
    for record in render_output_records:
        verify_built_artifact(render_base, record)
    expected_page_outputs = {
        "index.html",
        "desktop.png",
        "mobile.png",
    }
    if (
        {record["path"] for record in PAGE_MANIFEST["outputs"]}
        != expected_page_outputs
        or len(PAGE_MANIFEST["outputs"]) != len(expected_page_outputs)
    ):
        raise AssertionError("full-page preview output-set drift")
    for record in PAGE_MANIFEST["outputs"]:
        verify_built_artifact(ROOT / "assets" / "readme" / "page", record)
    for record in RENDER_MANIFEST["inputs"]["resources"]:
        verify_built_artifact(ROOT, record)
    expected_page_images = {
        "assets/easyinput-v2-pcb-bottom.png",
        "assets/easyinput-v2-pcb-top.png",
        "assets/easyinput-v2-schematic-page-1-branded.png",
        "assets/easyinput-v2-schematic-page-2-branded.png",
        "assets/readme/render/hero.png",
        "assets/readme/sections/boot-flow.svg",
        "assets/readme/sections/gpio8-shared-rail.svg",
        "assets/readme/sections/verification-ladder.svg",
        "assets/wechat-qr.jpg",
    }
    if {record["path"] for record in PAGE_MANIFEST["source"]["images"]} != expected_page_images:
        raise AssertionError("full-page preview image-input scope drift")
    for record in PAGE_MANIFEST["source"]["images"]:
        path = ROOT / record["path"]
        payload = path.read_bytes()
        if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise AssertionError(f"full-page input drift: {record['path']}")

    readme_sha256 = hashlib.sha256((ROOT / "README.md").read_bytes()).hexdigest()
    if RENDER_MANIFEST["inputs"]["readme"]["sha256"] != readme_sha256:
        raise AssertionError("Hero bundle is not bound to the current README")
    if PAGE_MANIFEST["source"]["readme"]["sha256"] != readme_sha256:
        raise AssertionError("full-page preview is not bound to the current README")
    render_resource_paths = {
        record["path"] for record in RENDER_MANIFEST["inputs"]["resources"]
    }
    if render_resource_paths != {
        "assets/easyinput-v2-pcb-top.png",
        "assets/readme/source/hero.html",
        "references/source-manifest.json",
    }:
        raise AssertionError("Hero bundle resource-input set drift")
    forbidden_render_inputs = {
        "assets/brand-wuqiwangxiang-black.png",
        "assets/brand-waytoagi-black.png",
        "assets/wechat-qr.jpg",
    }
    if render_resource_paths & forbidden_render_inputs:
        raise AssertionError("Hero render directly includes an excluded source asset")
    for marker in ("brand-wuqiwangxiang", "brand-waytoagi", "wechat-qr", "data:image"):
        if marker in HERO_SOURCE:
            raise AssertionError(f"Hero source embeds an excluded or opaque asset: {marker}")

    for marker in (
        "两张含 Logo 的 PCB 快照、由 PCB TOP 生成的 Hero／多尺寸／GitHub 页壳／审阅板渲染",
        "它不单独证明作者身份、委托／职务作品关系或再许可权",
    ):
        if marker not in SOURCE_MAP:
            raise AssertionError(f"source map omits licensing boundary: {marker}")

    if '$easyinput-board-cy' not in OPENAI:
        raise AssertionError("default prompt must mention $easyinput-board-cy")
    for phrase in ("开发板硬件事实、未知项和板级安全边界", "交还给总体任务"):
        if phrase not in OPENAI:
            raise AssertionError(
                f"default prompt must preserve context-only positioning: {phrase}"
            )

    project_leaks = (
        "easy-input-keyboard",
        "easy-input-model",
        "easy-input-music",
        "esp32-cn-llm",
        "production-keyboard",
        "production keyboard",
        "CAPS_ALLOC",
        "MALLOC_CAP",
        '"awake_level"',
        '"direction_multiplier"',
        '"i2s_port"',
        '"verified_sample_rate_hz"',
        '"cold_boot_settle_min_ms"',
    )
    runtime_paths = [
        ROOT / "SKILL.md",
        ROOT / "agents" / "openai.yaml",
        ROOT / "evals" / "evals.json",
        ROOT / "scripts" / "check_board_baseline.py",
        *(ROOT / "references").glob("*"),
    ]
    for path in runtime_paths:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for leak in project_leaks:
            if leak.casefold() in content.casefold():
                raise AssertionError(f"project-specific content leaked into {path.name}: {leak}")

    print("PASS: easyinput-board-cy skill contract")


if __name__ == "__main__":
    main()
