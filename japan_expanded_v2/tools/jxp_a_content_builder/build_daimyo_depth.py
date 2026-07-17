#!/usr/bin/env python3
"""Validate and render Agent A's authoritative 67-daimyo design matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_ROOT = SCRIPT_DIR.parents[1]
REPO_ROOT = MAIN_ROOT.parent
PLAN_PATH = SCRIPT_DIR / "daimyo_depth_plan.json"
REPORT_PATH = MAIN_ROOT / "dev_logs" / "jxp_agent_a_daimyo_design_matrix_0_29_0.md"
MAJOR_PLAN_PATH = MAIN_ROOT / "tools" / "jxp_validation" / "major_daimyo_mission_plan.json"

EXPECTED_MAIN = {
    "AKM", "AKT", "AMA", "ASA", "ASK", "CBA", "CSK", "DTE", "HJO", "HSK",
    "HTK", "IKE", "IMG", "ISK", "ITO", "KKC", "KNO", "KTB", "MAE", "MRI",
    "ODA", "OGS", "OTM", "OUC", "RFR", "SBA", "SHN", "SMZ", "SOO", "STK",
    "TKD", "TKG", "TKI", "TTI", "UES", "UTN", "YMN",
}
EXPECTED_MAP = {
    "RKK", "KYO", "WKT", "TGS", "NHT", "ANK", "HNM", "MOG", "ASN", "OSK",
    "SMA", "DHO", "MKM", "SGR", "KMP", "ARI", "MTU", "STM", "HNG", "AZI",
    "MYO", "STO", "RZJ", "UKT", "TGR", "HCS", "MTS", "KRD", "YMC", "NBS",
}
EXPECTED_TIERS = {"S": 16, "A": 13, "B": 38}
TIER_MINIMUMS = {
    "S": {"missions": (14, 20), "events": (8, 15)},
    "A": {"missions": (10, 13), "events": (5, 8)},
    "B": {"missions": (4, 6), "events": (3, 5)},
}
ALLOWED_FLAGS = {
    "jxp_iface_house_government_ready",
    "jxp_iface_house_diplomacy_ready",
    "jxp_iface_house_maritime_ready",
    "jxp_iface_house_logistics_ready",
    "jxp_iface_house_frontier_ready",
    "jxp_iface_house_religious_ready",
    "jxp_iface_house_mass_mobilization_ready",
    "jxp_iface_buddhist_diplomacy_ready",
}
REQUIRED_FIELDS = {
    "tag", "name", "surface", "tier", "political_context", "existing_missions",
    "planned_missions", "planned_events", "keywords", "internal_crisis",
    "alternate_success", "unified_legacy", "interface_flags", "sources",
    "duplication_risk",
}


def _load() -> dict[str, Any]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        raise ValueError("daimyo depth plan must use schema_version 1")
    return plan


def _existing_unique_counts() -> dict[str, int]:
    """Read the 28-branch runtime baseline instead of duplicating it in A1."""
    major_plan = json.loads(MAJOR_PLAN_PATH.read_text(encoding="utf-8"))
    counts = {
        record["tag"]: len(record["chapters"])
        for surface in ("main", "map")
        for record in major_plan[surface]
    }
    if len(counts) != 28 or set(counts.values()) != {8}:
        raise ValueError("major daimyo mission baseline must remain 28 exact eight-node branches")
    # The current mixed ODA/TOY series has six nodes, but only its first three
    # are ODA content.  The TOY conversion and two TOY nodes belong to the
    # unified-state appendix and cannot be credited to ODA's unique baseline.
    counts["ODA"] = 3
    return counts


def validate(plan: dict[str, Any]) -> None:
    records = plan.get("daimyo", [])
    existing_counts = _existing_unique_counts()
    if len(records) != 67:
        raise ValueError(f"expected 67 daimyo records, found {len(records)}")
    tags = [record.get("tag") for record in records]
    if len(tags) != len(set(tags)):
        raise ValueError("duplicate tag in daimyo design matrix")
    if set(tags) != EXPECTED_MAIN | EXPECTED_MAP:
        missing = sorted((EXPECTED_MAIN | EXPECTED_MAP) - set(tags))
        extra = sorted(set(tags) - (EXPECTED_MAIN | EXPECTED_MAP))
        raise ValueError(f"tag coverage mismatch: missing={missing}, extra={extra}")

    sources = plan.get("sources", {})
    if not sources:
        raise ValueError("source catalog is empty")
    for source_id, source in sources.items():
        if re.fullmatch(r"[a-z0-9_]+", source_id) is None:
            raise ValueError(f"unsafe source id {source_id}")
        if not source.get("title") or not source.get("url", "").startswith("https://"):
            raise ValueError(f"invalid source catalog entry {source_id}")

    tier_counts = {tier: 0 for tier in EXPECTED_TIERS}
    for record in records:
        missing_fields = REQUIRED_FIELDS - set(record)
        if missing_fields:
            raise ValueError(f"{record.get('tag', '?')} missing fields {sorted(missing_fields)}")
        tag = record["tag"]
        expected_surface = "main" if tag in EXPECTED_MAIN else "map"
        if record["surface"] != expected_surface:
            raise ValueError(f"{tag} must use surface={expected_surface}")
        tier = record["tier"]
        if tier not in EXPECTED_TIERS:
            raise ValueError(f"{tag} has invalid tier {tier}")
        tier_counts[tier] += 1
        minimums = TIER_MINIMUMS[tier]
        for field, (lower, upper) in minimums.items():
            value = record[f"planned_{field}"]
            if not lower <= value <= upper:
                raise ValueError(f"{tag} planned_{field}={value} outside Tier {tier} range {lower}-{upper}")
        existing = existing_counts.get(tag, 0)
        if record["planned_missions"] < existing:
            raise ValueError(f"{tag} target would retire existing unique missions without an explicit migration design")
        for text_field in (
            "name", "political_context", "existing_missions", "internal_crisis",
            "alternate_success", "unified_legacy", "duplication_risk",
        ):
            if not str(record[text_field]).strip():
                raise ValueError(f"{tag} has empty {text_field}")
        if len(record["keywords"]) < 3 or len(set(record["keywords"])) != len(record["keywords"]):
            raise ValueError(f"{tag} must define at least three unique keywords")
        flags = set(record["interface_flags"])
        if not flags or not flags <= ALLOWED_FLAGS:
            raise ValueError(f"{tag} has empty or unsupported interface flags: {sorted(flags)}")
        if not record["sources"] or any(source_id not in sources for source_id in record["sources"]):
            raise ValueError(f"{tag} has missing or unknown source references")
    if tier_counts != EXPECTED_TIERS:
        raise ValueError(f"tier coverage mismatch: {tier_counts}, expected {EXPECTED_TIERS}")

    toy = plan.get("unified_state_appendix", {}).get("TOY")
    if not toy or toy.get("tier") != "S" or toy.get("surface") != "main":
        raise ValueError("TOY unified-state appendix is missing or malformed")
    if set(toy.get("interface_flags", [])) - ALLOWED_FLAGS:
        raise ValueError("TOY appendix uses unsupported interface flags")


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = "、".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(plan: dict[str, Any]) -> str:
    records = plan["daimyo"]
    existing_counts = _existing_unique_counts()
    lines = [
        "# Agent A：67 大名独特化设计矩阵（0.29.0）",
        "",
        "> 本文件由 `tools/jxp_a_content_builder/build_daimyo_depth.py` 从 `daimyo_depth_plan.json` 确定性生成。请勿手改。",
        "> 这是内容实施前的静态设计合同，不代表任务、事件或游戏内运行时已经完成。",
        "",
        "## 覆盖与分层",
        "",
        "- 67 个可选大名：主 Mod 37、地图 Mod 30。",
        "- Tier S 16、Tier A 13、Tier B 38；TOY 作为统一后国家另列，不计入 67。",
        "- 所有跨 Agent 能力只写入既定 `jxp_iface_*` 接口；Agent A 私有状态继续使用 `jxp_a_*`。",
        "",
    ]
    for surface, title in (("main", "主 Mod 37 家"), ("map", "地图 Mod 30 家")):
        lines.extend(
            (
                f"## {title}",
                "",
                "| Tag / 国名 | Tier | 初始政治处境 | 已有任务 | 新增 / 目标任务；新增事件 | 独特玩法 | 内部危机 | 架空成功路线 | 统一后遗产 | 共享接口 | 史料 | 重复风险控制 |",
                "| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
            )
        )
        for record in sorted((row for row in records if row["surface"] == surface), key=lambda row: row["tag"]):
            existing = existing_counts.get(record["tag"], 0)
            new_missions = record["planned_missions"] - existing
            source_links = [
                f"[{plan['sources'][source_id]['title']}]({plan['sources'][source_id]['url']})"
                for source_id in record["sources"]
            ]
            lines.append(
                "| " + " | ".join(
                    (
                        f"`{record['tag']}` {_cell(record['name'])}",
                        record["tier"],
                        _cell(record["political_context"]),
                        _cell(record["existing_missions"]),
                        f"{new_missions} / {record['planned_missions']}；{record['planned_events']}",
                        _cell(record["keywords"]),
                        _cell(record["internal_crisis"]),
                        _cell(record["alternate_success"]),
                        _cell(record["unified_legacy"]),
                        "<br>".join(f"`{flag}`" for flag in record["interface_flags"]),
                        "<br>".join(source_links),
                        _cell(record["duplication_risk"]),
                    )
                ) + " |"
            )
        lines.append("")

    toy = plan["unified_state_appendix"]["TOY"]
    lines.extend(
        (
            "## TOY 统一后附录（不计入 67）",
            "",
            f"- 定位：{toy['political_context']}",
            f"- 规划：{toy['planned_missions']} 个独特任务、{toy['planned_events']} 个独特事件。",
            f"- 危机：{toy['internal_crisis']}",
            f"- 终局：{toy['alternate_success']}",
            f"- 遗产：{toy['unified_legacy']}",
            f"- 接口：{', '.join(f'`{flag}`' for flag in toy['interface_flags'])}",
            "",
            "## 实施纪律",
            "",
            "1. Tier B 必须取得精确 tag 节点和事件，不能只改标题或复制永久全国修正。",
            "2. Tier S/A 的历史伙伴均有动态替代条件；历史 tag 灭亡不会锁死路线。",
            "3. 失败路线必须是可玩的重建选择，不用强制统治者死亡复刻史实。",
            "4. 地图 30 家运行文件继续由地图 Mod 拥有；主 Mod 只消费语义接口，不硬引用地图 tag。",
            "5. 本矩阵通过后才允许生成 A2–A5 任务和事件；任何数量变化都必须先修改权威计划并重建本报告。",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate and fail if the generated report drifts")
    args = parser.parse_args()
    plan = _load()
    validate(plan)
    rendered = render(plan)
    if args.check:
        if not REPORT_PATH.is_file() or REPORT_PATH.read_text(encoding="utf-8") != rendered:
            print(f"DRIFT {REPORT_PATH.relative_to(REPO_ROOT)}")
            return 1
        print("PASS: 67-daimyo design matrix is valid and current")
        return 0
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(rendered, encoding="utf-8", newline="")
    print(f"Created {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
