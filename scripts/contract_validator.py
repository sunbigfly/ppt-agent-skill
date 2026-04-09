#!/usr/bin/env python3
"""Validate v4 workflow contracts.

Supported contracts:
- interview-qa.txt
- requirements-interview.txt
- search.txt
- search-brief.txt
- source-brief.txt
- outline.txt
- style.json
- planning image contracts
- per-page review result
- delivery-manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from planning_validator import load_jsonish, load_planning_pages


PASS_WORDS = {"pass", "passed", "通过", "已通过", "ok"}
FAIL_WORDS = {"fail", "failed", "不通过", "未通过", "reject", "rejected"}
STAGE_ORDER = {"planning": 0, "html": 1, "review": 2}
ANCHOR_LINE_PATTERN = re.compile(r"^\s*(?:[-*]\s*)?([A-Za-z_][A-Za-z0-9_-]*)\s*[：:]\s*(.+?)\s*$")
VALID_DENSITY_BIASES = {"relaxed", "balanced", "ultra_dense"}
VALID_DENSITY_LABELS = {"low", "mid_low", "medium", "high", "dashboard"}
DENSITY_ORDER = {"low": 0, "mid_low": 1, "medium": 2, "high": 3, "dashboard": 4}
VALID_RHYTHM_ACTIONS = {"铺垫", "推进", "爆发", "缓冲", "收束"}
VALID_INFO_POSTURES = {"结论页", "解释页", "证据页", "仪表盘页", "呼吸页"}
VALID_ANCHOR_TYPES = {"标题", "KPI", "图表", "表格", "图片", "引言"}
NON_DASHBOARD_PAGE_TYPES = {"cover", "section", "end"}
REQUIRED_INTERVIEW_DIMENSIONS = [
    ("scenario", ["场景", "使用场景", "应用场景", "scenario"]),
    ("audience", ["受众", "听众", "对象", "audience"]),
    ("target_action", ["目标动作", "希望动作", "行动", "target_action"]),
    ("expected_pages", ["期望页数", "页数", "expected_pages"]),
    ("page_density", ["密度", "信息密度", "page_density"]),
    ("style", ["风格", "视觉风格", "style:"]),
    ("brand", ["品牌", "logo", "品牌色", "brand:"]),
    ("must_include", ["必含", "必须包含", "必须有", "must_include"]),
    ("must_avoid", ["必避", "避免", "禁用", "must_avoid"]),
    ("language", ["语言", "中文", "英文", "中英", "language:"]),
    ("imagery", ["配图", "图片", "图像", "插图", "imagery", "image_mode"]),
    ("material_strategy", ["资料使用策略", "资料策略", "素材使用", "引用策略", "material_strategy", "materials_strategy"]),
    ("subagent_model_strategy", ["subagent_model_strategy", "后续子系统使用什么模型", "模型", "subagent model"]),
    ("subagent_thinking_effort", ["subagent_thinking_effort", "思考深度", "推理等级", "reasoning effort"]),
    ("manual_audit_mode", ["manual_audit_mode", "人工审计", "中间审计", "断点"]),
    ("manual_audit_scope", ["manual_audit_scope", "介入节点", "审计节点", "scope"]),
    ("manual_audit_assets", ["manual_audit_assets", "审计材料", "runtime 文件", "指定图片"]),
]
REQUIRED_INTERVIEW_ANCHORS = [
    "scenario",
    "audience",
    "target_action",
    "expected_pages",
    "page_density",
    "style",
    "brand",
    "must_include",
    "must_avoid",
    "language",
    "imagery",
    "material_strategy",
    "subagent_model_strategy",
    "subagent_thinking_effort",
    "manual_audit_mode",
    "manual_audit_scope",
    "manual_audit_assets",
]
REQUIRED_AUDIT_REQUEST_FIELDS = [
    "page_number",
    "start_stage",
    "end_stage",
    "user_request",
    "target_asset_path",
    "runtime_context_paths",
    "planning_output",
    "html_output",
    "png_output",
]


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_iso_timestamp(label: str, value: Any, result: ValidationResult) -> datetime | None:
    if not is_non_empty_string(value):
        result.error(f"{label}: must be a non-empty ISO timestamp string")
        return None
    raw = str(value).strip()
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        result.error(f"{label}: invalid ISO timestamp {value!r}")
        return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def basic_text_gate(path: Path, label: str, min_chars: int = 40, min_lines: int = 2) -> tuple[ValidationResult, dict[str, Any], str]:
    result = ValidationResult()
    text = read_text(path)
    if not text:
        result.error(f"{label}: file is empty")
        return result, {"chars": 0, "lines": 0, "errors": 1, "warnings": 0}, text

    chars = len(text)
    lines = len([line for line in text.splitlines() if line.strip()])
    if chars < min_chars:
        result.error(f"{label}: must contain at least {min_chars} characters")
    if lines < min_lines:
        result.error(f"{label}: must contain at least {min_lines} non-empty lines")

    summary = {
        "chars": chars,
        "lines": lines,
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }
    return result, summary, text


def contains_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def normalize_density_bias(raw: Any) -> str | None:
    if not is_non_empty_string(raw):
        return None
    lowered = str(raw).strip().lower()
    mapping = {
        "relaxed": "relaxed",
        "balanced": "balanced",
        "ultra_dense": "ultra_dense",
        "少而精": "relaxed",
        "适中": "balanced",
        "容量极大": "ultra_dense",
        "极高密度": "ultra_dense",
    }
    return mapping.get(lowered) or mapping.get(str(raw).strip())


def derive_density_bias_from_page_density(raw: Any) -> str | None:
    return normalize_density_bias(raw)


def normalize_density_label(raw: Any) -> str | None:
    if not is_non_empty_string(raw):
        return None
    lowered = str(raw).strip().lower().replace("-", "_")
    if lowered in VALID_DENSITY_LABELS:
        return lowered
    return None


def density_rank(label: str | None) -> int | None:
    if label is None:
        return None
    return DENSITY_ORDER.get(label)


def extract_named_field(text: str, names: list[str]) -> str | None:
    for name in names:
        match = re.search(rf"^\s*(?:[-*]\s*)?{re.escape(name)}\s*[：:]\s*(.+?)\s*$", text, re.M)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def parse_outline_pages(text: str) -> list[dict[str, Any]]:
    page_headers = list(re.finditer(r"^###\s*第\s*(\d+)\s*页[:：]\s*(.+?)\s*$", text, re.M))
    pages: list[dict[str, Any]] = []
    for index, match in enumerate(page_headers):
        page_num = int(match.group(1))
        page_title = match.group(2).strip()
        block_start = match.end()
        block_end = page_headers[index + 1].start() if index + 1 < len(page_headers) else len(text)
        block = text[block_start:block_end]
        page = {
            "page_number": page_num,
            "page_title": page_title,
            "page_goal": extract_named_field(block, ["页目标", "page_goal"]),
            "page_type": extract_named_field(block, ["页面类型映射", "page_type"]),
            "density_lower": normalize_density_label(extract_named_field(block, ["密度下限", "density_lower"])),
            "density_target": normalize_density_label(extract_named_field(block, ["密度目标", "density_target"])),
            "density_upper": normalize_density_label(extract_named_field(block, ["密度上限", "density_upper"])),
            "rhythm_action": extract_named_field(block, ["节奏动作", "rhythm_action"]),
            "info_posture": extract_named_field(block, ["信息姿态", "info_posture"]),
            "anchor_type": extract_named_field(block, ["锚点类型", "anchor_type"]),
        }
        pages.append(page)
    return pages


def extract_anchor_fields(text: str) -> dict[str, str]:
    anchors: dict[str, str] = {}
    for line in text.splitlines():
        matched = ANCHOR_LINE_PATTERN.match(line)
        if not matched:
            continue
        key = matched.group(1).strip().lower().replace("-", "_")
        value = matched.group(2).strip()
        if value:
            anchors[key] = value
    return anchors


def validate_required_anchor_fields(
    anchors: dict[str, str],
    required_fields: list[str],
    result: ValidationResult,
    label: str,
) -> list[str]:
    matched: list[str] = []
    for field_name in required_fields:
        if is_non_empty_string(anchors.get(field_name)):
            matched.append(field_name)
        else:
            result.error(f"{label}: missing required canonical anchor `{field_name}`")
    return matched


def validate_topics_coverage(text: str, result: ValidationResult, label: str) -> list[str]:
    # 每个维度同时支持中文标题（tpl-interview.md 规范格式）和英文键名（LLM 自由格式兼容）
    matched: list[str] = []
    for key, keywords in REQUIRED_INTERVIEW_DIMENSIONS:
        if contains_any(text, keywords):
            matched.append(key)
        else:
            result.error(f"{label}: missing required interview dimension `{key}`")
    return matched


def validate_interview(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "interview-qa", min_chars=120, min_lines=8)
    matched = validate_topics_coverage(text, result, "interview-qa")
    anchors = extract_anchor_fields(text)
    matched_anchors = validate_required_anchor_fields(anchors, REQUIRED_INTERVIEW_ANCHORS, result, "interview-qa")
    density_bias = derive_density_bias_from_page_density(anchors.get("density_bias") or anchors.get("page_density"))
    summary["matched_dimensions"] = matched
    summary["matched_anchor_fields"] = matched_anchors
    summary["anchor_fields_present"] = sorted(anchors.keys())
    summary["density_bias"] = density_bias
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def validate_requirements_interview(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "requirements-interview", min_chars=120, min_lines=8)
    matched = validate_topics_coverage(text, result, "requirements-interview")
    anchors = extract_anchor_fields(text)
    matched_anchors = validate_required_anchor_fields(anchors, REQUIRED_INTERVIEW_ANCHORS, result, "requirements-interview")
    density_bias = derive_density_bias_from_page_density(anchors.get("density_bias") or anchors.get("page_density"))

    if not contains_any(text, ["branch", "分支", "research", "直接制作", "现有资料"]):
        result.warn("requirements-interview: branch decision is not explicit")

    summary["matched_dimensions"] = matched
    summary["matched_anchor_fields"] = matched_anchors
    summary["anchor_fields_present"] = sorted(anchors.keys())
    summary["density_bias"] = density_bias
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def validate_search(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "search", min_chars=180, min_lines=8)
    if not contains_any(text, ["http://", "https://", "来源", "source"]):
        result.warn("search: no obvious source marker detected")
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def validate_search_brief(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "search-brief", min_chars=120, min_lines=6)
    if not contains_any(text, ["结论", "summary", "要点", "insight"]):
        result.warn("search-brief: no explicit summary cue detected")
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def validate_source_brief(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "source-brief", min_chars=120, min_lines=6)
    if not contains_any(text, ["主题", "topic", "适用", "风险", "限制"]):
        result.warn("source-brief: topic/risk/constraints signals look weak")
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def validate_outline(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "outline", min_chars=180, min_lines=8)

    page_markers = re.findall(r"(?:第\s*\d+\s*页|slide\s*\d+|p\d+\.|s\d+)", text, flags=re.IGNORECASE)
    if not page_markers:
        result.error("outline: no page-level marker detected (e.g. 第1页 / slide 1)")

    if not contains_any(text, ["自审通过", "SELF_REVIEW_PASS", "outline-self-review", "自审"]):
        result.warn("outline: no explicit self-review marker detected")

    density_bias = normalize_density_bias(
        extract_named_field(text, ["密度倾向", "density_bias"]) or extract_named_field(text, ["page_density"])
    )
    if density_bias is None:
        result.error("outline: missing valid `密度倾向` / `density_bias`")

    density_curve = extract_named_field(text, ["密度曲线", "density_curve"])
    if not is_non_empty_string(density_curve):
        result.error("outline: missing `密度曲线` / `density_curve`")

    pages = parse_outline_pages(text)
    if not pages:
        result.error("outline: failed to parse page blocks")

    dashboard_pages = 0
    high_pressure_streak = 0
    for index, page in enumerate(pages):
        page_label = f"outline page {page['page_number']}"
        for field_name, field_value in (
            ("密度下限", page["density_lower"]),
            ("密度目标", page["density_target"]),
            ("密度上限", page["density_upper"]),
        ):
            if field_value is None:
                result.error(f"{page_label}: missing valid `{field_name}`")

        lower_rank = density_rank(page["density_lower"])
        target_rank = density_rank(page["density_target"])
        upper_rank = density_rank(page["density_upper"])
        if None not in (lower_rank, target_rank, upper_rank) and not (lower_rank <= target_rank <= upper_rank):
            result.error(f"{page_label}: 密度窗口非法，必须满足 下限 <= 目标 <= 上限")

        rhythm_action = page["rhythm_action"]
        if not is_non_empty_string(rhythm_action):
            result.error(f"{page_label}: missing `节奏动作`")
        elif rhythm_action not in VALID_RHYTHM_ACTIONS:
            result.error(f"{page_label}: invalid 节奏动作 `{rhythm_action}`")

        info_posture = page["info_posture"]
        if not is_non_empty_string(info_posture):
            result.error(f"{page_label}: missing `信息姿态`")
        elif info_posture not in VALID_INFO_POSTURES:
            result.error(f"{page_label}: invalid 信息姿态 `{info_posture}`")

        anchor_type = page["anchor_type"]
        if not is_non_empty_string(anchor_type):
            result.error(f"{page_label}: missing `锚点类型`")
        elif anchor_type not in VALID_ANCHOR_TYPES:
            result.error(f"{page_label}: invalid 锚点类型 `{anchor_type}`")

        page_type = (page["page_type"] or "").strip().lower()
        if page_type in NON_DASHBOARD_PAGE_TYPES:
            if "dashboard" in {page["density_lower"], page["density_target"], page["density_upper"]}:
                result.error(f"{page_label}: page_type={page_type} 不允许使用 dashboard 密度")

        if density_bias == "relaxed" and page_type == "content":
            if "dashboard" in {page["density_lower"], page["density_target"], page["density_upper"]}:
                result.error(f"{page_label}: relaxed 模式 content 页禁止 dashboard")
        elif density_bias == "balanced" and page_type == "content":
            ranks = [rank for rank in (lower_rank, target_rank, upper_rank) if rank is not None]
            if ranks and min(ranks) < DENSITY_ORDER["mid_low"]:
                result.error(f"{page_label}: balanced 模式 content 页密度不得低于 mid_low")
        elif density_bias == "ultra_dense" and page_type == "content":
            ranks = [rank for rank in (lower_rank, target_rank, upper_rank) if rank is not None]
            if ranks and min(ranks) < DENSITY_ORDER["medium"]:
                result.error(f"{page_label}: ultra_dense 模式 content 页密度不得低于 medium")

        if page["density_target"] == "dashboard":
            dashboard_pages += 1
            if info_posture != "仪表盘页":
                result.error(f"{page_label}: dashboard 页必须使用 `信息姿态: 仪表盘页`")
            prev_target = pages[index - 1]["density_target"] if index > 0 else None
            next_target = pages[index + 1]["density_target"] if index + 1 < len(pages) else None
            if prev_target == "dashboard" or next_target == "dashboard":
                result.error(f"{page_label}: dashboard 前后必须至少有 1 页非 dashboard 过渡")

        if info_posture == "仪表盘页" and page["density_target"] != "dashboard":
            result.error(f"{page_label}: `信息姿态: 仪表盘页` 必须对应 `密度目标: dashboard`")

        if page["density_target"] in {"high", "dashboard"}:
            high_pressure_streak += 1
        else:
            high_pressure_streak = 0
        if high_pressure_streak >= 3:
            result.error(f"{page_label}: 禁止连续 3 页 `high/dashboard`")

    summary["page_markers"] = len(page_markers)
    summary["density_bias"] = density_bias
    summary["density_curve"] = density_curve
    summary["parsed_pages"] = len(pages)
    summary["dashboard_pages"] = dashboard_pages
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def parse_pass_fail_from_text(text: str) -> tuple[bool | None, str]:
    lowered = text.lower()
    has_pass = any(token in lowered for token in PASS_WORDS)
    has_fail = any(token in lowered for token in FAIL_WORDS)

    if has_pass and not has_fail:
        return True, "pass-token"
    if has_fail and not has_pass:
        return False, "fail-token"
    if has_pass and has_fail:
        return None, "mixed-pass-fail"
    return None, "no-pass-fail-token"


def validate_page_review(path: Path, require_pass: bool) -> tuple[ValidationResult, dict[str, Any]]:
    result = ValidationResult()
    text = read_text(path)
    verdict: str | None = None
    reason = ""

    parsed_json: Any | None = None
    if path.suffix.lower() == ".json":
        try:
            parsed_json = load_jsonish(path)
        except Exception as exc:
            result.error(f"page-review: invalid JSON payload: {exc}")

    if isinstance(parsed_json, dict):
        candidate_fields = [
            parsed_json.get("verdict"),
            parsed_json.get("status"),
            parsed_json.get("result"),
            parsed_json.get("review", {}).get("verdict") if isinstance(parsed_json.get("review"), dict) else None,
        ]
        for item in candidate_fields:
            if not is_non_empty_string(item):
                continue
            token = str(item).strip().lower()
            if token in {"pass", "passed", "ok", "通过", "已通过"}:
                verdict = "pass"
                reason = "json-verdict"
                break
            if token in {"fail", "failed", "reject", "rejected", "不通过", "未通过"}:
                verdict = "fail"
                reason = "json-verdict"
                break

    if verdict is None:
        pass_result, token_reason = parse_pass_fail_from_text(text)
        reason = token_reason
        if pass_result is True:
            verdict = "pass"
        elif pass_result is False:
            verdict = "fail"

    if verdict is None:
        result.error("page-review: could not infer pass/fail verdict")
    elif require_pass and verdict != "pass":
        result.error("page-review: verdict is not pass")

    summary = {
        "verdict": verdict,
        "reason": reason,
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }
    return result, summary


def normalize_stage(label: str, value: Any, result: ValidationResult) -> str | None:
    if not is_non_empty_string(value):
        result.error(f"{label}: must be a non-empty string")
        return None
    stage = str(value).strip().lower()
    if stage not in STAGE_ORDER:
        result.error(f"{label}: invalid stage {value!r}, expected one of {sorted(STAGE_ORDER)}")
        return None
    return stage


def split_runtime_context_paths(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(";") if item.strip()]


def validate_page_audit_request(path: Path, base_dir: Path | None) -> tuple[ValidationResult, dict[str, Any]]:
    result, summary, text = basic_text_gate(path, "page-audit-request", min_chars=80, min_lines=8)
    anchors = extract_anchor_fields(text)
    matched = validate_required_anchor_fields(anchors, REQUIRED_AUDIT_REQUEST_FIELDS, result, "page-audit-request")

    page_number_raw = anchors.get("page_number")
    page_number: int | None = None
    if is_non_empty_string(page_number_raw):
        try:
            page_number = int(str(page_number_raw).strip())
            if page_number <= 0:
                raise ValueError
        except ValueError:
            result.error("page-audit-request: page_number must be a positive integer")

    start_stage = normalize_stage("page-audit-request.start_stage", anchors.get("start_stage"), result)
    end_stage = normalize_stage("page-audit-request.end_stage", anchors.get("end_stage"), result)
    if start_stage and end_stage and STAGE_ORDER[start_stage] > STAGE_ORDER[end_stage]:
        result.error("page-audit-request: start_stage cannot be later than end_stage")

    user_request = anchors.get("user_request")
    if is_non_empty_string(user_request) and len(str(user_request).strip()) < 6:
        result.error("page-audit-request: user_request is too short")

    target_asset_path = anchors.get("target_asset_path", "")
    runtime_context_raw = anchors.get("runtime_context_paths", "")
    runtime_context_paths = split_runtime_context_paths(runtime_context_raw) if is_non_empty_string(runtime_context_raw) else []

    if is_non_empty_string(target_asset_path) and str(target_asset_path).strip().lower() != "none":
        if base_dir is None:
            result.warn("page-audit-request: cannot verify target_asset_path existence without --base-dir")
        else:
            resolved_target = resolve_artifact_path(base_dir, target_asset_path)
            if resolved_target is None or not resolved_target.exists():
                result.error(f"page-audit-request.target_asset_path: path does not exist -> {target_asset_path}")

    if runtime_context_raw and runtime_context_raw.strip().lower() != "none":
        if not runtime_context_paths:
            result.error("page-audit-request: runtime_context_paths must contain at least one path or be `none`")
        elif base_dir is None:
            result.warn("page-audit-request: cannot verify runtime_context_paths without --base-dir")
        else:
            for item in runtime_context_paths:
                resolved_item = resolve_artifact_path(base_dir, item)
                if resolved_item is None or not resolved_item.exists():
                    result.error(f"page-audit-request.runtime_context_paths: path does not exist -> {item}")

    planning_output = anchors.get("planning_output")
    html_output = anchors.get("html_output")
    png_output = anchors.get("png_output")

    if base_dir is not None and start_stage in {"html", "review"} and is_non_empty_string(planning_output):
        resolved_planning = resolve_artifact_path(base_dir, planning_output)
        if resolved_planning is None or not resolved_planning.exists():
            result.error(f"page-audit-request.planning_output: expected existing planning artifact -> {planning_output}")

    if base_dir is not None and start_stage == "review" and is_non_empty_string(html_output):
        resolved_html = resolve_artifact_path(base_dir, html_output)
        if resolved_html is None or not resolved_html.exists():
            result.error(f"page-audit-request.html_output: expected existing html artifact -> {html_output}")

    summary["matched_anchor_fields"] = matched
    summary["page_number"] = page_number
    summary["start_stage"] = start_stage
    summary["end_stage"] = end_stage
    summary["runtime_context_count"] = len(runtime_context_paths)
    summary["has_target_asset"] = bool(is_non_empty_string(target_asset_path) and target_asset_path.strip().lower() != "none")
    summary["errors"] = len(result.errors)
    summary["warnings"] = len(result.warnings)
    return result, summary


def resolve_artifact_path(base_dir: Path, raw_path: Any) -> Path | None:
    if not is_non_empty_string(raw_path):
        return None
    p = Path(str(raw_path).strip())
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def validate_delivery_manifest(path: Path, base_dir: Path | None) -> tuple[ValidationResult, dict[str, Any]]:
    result = ValidationResult()
    payload = load_jsonish(path)
    if not isinstance(payload, dict):
        raise ValueError("delivery-manifest must be a JSON object")

    manifest = payload.get("delivery_manifest") if isinstance(payload.get("delivery_manifest"), dict) else payload
    if not isinstance(manifest, dict):
        raise ValueError("delivery_manifest payload must be an object")

    for field_name in ("run_id", "generated_at", "artifacts"):
        if field_name not in manifest:
            result.error(f"missing required field: {field_name}")

    run_id = manifest.get("run_id")
    if not is_non_empty_string(run_id):
        result.error("run_id: must be a non-empty string")

    parse_iso_timestamp("generated_at", manifest.get("generated_at"), result)

    summary_obj = manifest.get("summary")
    if summary_obj is not None and not isinstance(summary_obj, dict):
        result.error("summary: must be an object when provided")
    if isinstance(summary_obj, dict):
        total_pages = summary_obj.get("total_pages")
        if total_pages is not None and (not isinstance(total_pages, int) or total_pages <= 0):
            result.error("summary.total_pages: must be a positive integer when provided")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        result.error("artifacts: must be an object")
        artifacts = {}

    required_artifacts = (
        "preview_html",
        "presentation_png_pptx",
        "presentation_svg_pptx",
    )
    existing_count = 0
    for key in required_artifacts:
        raw_path = artifacts.get(key)
        if not is_non_empty_string(raw_path):
            result.error(f"artifacts.{key}: must be a non-empty path string")
            continue
        if base_dir is None:
            continue
        resolved = resolve_artifact_path(base_dir, raw_path)
        if resolved is None or not resolved.exists():
            result.error(f"artifacts.{key}: path does not exist -> {raw_path}")
        else:
            existing_count += 1

    pages = manifest.get("pages")
    if pages is not None and not isinstance(pages, list):
        result.error("pages: must be a list when provided")

    summary = {
        "run_id": run_id,
        "artifacts_checked": list(required_artifacts),
        "existing_artifacts": existing_count,
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }
    return result, summary


def validate_style(path: Path) -> tuple[ValidationResult, dict[str, Any]]:
    """Validate style.json contains required global style fields."""
    result = ValidationResult()
    try:
        payload = load_jsonish(path)
    except Exception as exc:
        result.error(f"style: failed to parse JSON: {exc}")
        return result, {"errors": 1, "warnings": 0}

    if not isinstance(payload, dict):
        result.error("style: root must be a JSON object")
        return result, {"errors": 1, "warnings": 0}

    style_id = payload.get("style_id")
    if not is_non_empty_string(style_id):
        result.error("style: missing non-empty 'style_id'")

    style_name = payload.get("style_name")
    if not is_non_empty_string(style_name):
        result.error("style: missing non-empty 'style_name'")

    mood_keywords = payload.get("mood_keywords")
    if not isinstance(mood_keywords, list):
        result.error("style: missing 'mood_keywords' list")
        mood_count = 0
    else:
        cleaned_keywords = [item.strip() for item in mood_keywords if is_non_empty_string(item)]
        mood_count = len(cleaned_keywords)
        if mood_count != len(mood_keywords):
            result.error("style: 'mood_keywords' must contain only non-empty strings")
        if mood_count < 3 or mood_count > 5:
            result.error("style: 'mood_keywords' must contain 3-5 items")

    design_soul = payload.get("design_soul") or payload.get("soul") or payload.get("mood") or payload.get("灵魂宣言")
    if not is_non_empty_string(design_soul):
        result.error("style: missing non-empty 'design_soul'")

    variation_strategy = payload.get("variation_strategy")
    if not is_non_empty_string(variation_strategy):
        result.error("style: missing non-empty 'variation_strategy'")

    decoration = payload.get("decoration_dna") or payload.get("decoration")
    if not isinstance(decoration, dict):
        result.error("style: missing object 'decoration_dna'")
    else:
        signature_move = decoration.get("signature_move")
        if not is_non_empty_string(signature_move):
            result.error("style: decoration_dna missing non-empty 'signature_move'")

        forbidden = decoration.get("forbidden")
        if not isinstance(forbidden, list):
            result.error("style: decoration_dna missing 'forbidden' list")
        else:
            cleaned_forbidden = [item.strip() for item in forbidden if is_non_empty_string(item)]
            if len(cleaned_forbidden) != len(forbidden):
                result.error("style: decoration_dna.forbidden must contain only non-empty strings")
            if len(cleaned_forbidden) < 2 or len(cleaned_forbidden) > 5:
                result.error("style: decoration_dna.forbidden must contain 2-5 items")

        combos = decoration.get("recommended_combos")
        if not isinstance(combos, list):
            result.error("style: decoration_dna missing 'recommended_combos' list")
        else:
            cleaned_combos = [item.strip() for item in combos if is_non_empty_string(item)]
            if len(cleaned_combos) != len(combos):
                result.error("style: decoration_dna.recommended_combos must contain only non-empty strings")
            if len(cleaned_combos) < 2 or len(cleaned_combos) > 4:
                result.error("style: decoration_dna.recommended_combos must contain 2-4 items")

    css_vars = payload.get("css_variables") or payload.get("css_vars")
    required_css_keys = [
        "bg_primary",
        "bg_secondary",
        "card_bg_from",
        "card_bg_to",
        "card_border",
        "card_radius",
        "text_primary",
        "text_secondary",
        "accent_1",
        "accent_2",
        "accent_3",
        "accent_4",
    ]
    if not isinstance(css_vars, dict):
        result.error("style: missing object 'css_variables'")
    else:
        for key in required_css_keys:
            if not is_non_empty_string(css_vars.get(key)):
                result.error(f"style: css_variables missing non-empty '{key}'")

    font_family = payload.get("font_family")
    legacy_font = payload.get("font") or payload.get("fonts") or payload.get("typography")
    if not is_non_empty_string(font_family):
        if legacy_font:
            result.warn("style: prefer 'font_family' over legacy font fields")
        else:
            result.error("style: missing non-empty 'font_family'")

    css_snippets = payload.get("css_snippets")
    if css_snippets is not None and not isinstance(css_snippets, dict):
        result.error("style: 'css_snippets' must be an object when provided")

    summary = {
        "style_id": style_id if is_non_empty_string(style_id) else None,
        "style_name": style_name if is_non_empty_string(style_name) else None,
        "mood_keywords": mood_count,
        "has_design_soul": bool(is_non_empty_string(design_soul)),
        "has_variation_strategy": bool(is_non_empty_string(variation_strategy)),
        "has_css_vars": bool(css_vars),
        "has_font_family": bool(is_non_empty_string(font_family)),
        "has_decoration": isinstance(decoration, dict),
        "has_css_snippets": isinstance(css_snippets, dict),
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }
    return result, summary


def _resolve_local_path_candidates(planning_path: Path, raw: str) -> list[Path]:
    source = raw.strip()
    candidate = Path(source)
    if candidate.is_absolute():
        return [candidate]

    planning_dir = planning_path if planning_path.is_dir() else planning_path.parent
    output_dir = planning_dir.parent
    return [
        (planning_dir / source).resolve(),
        (output_dir / source).resolve(),
    ]


def validate_images(path: Path, require_paths: bool) -> tuple[ValidationResult, dict[str, Any]]:
    """Validate image contracts from planning payload(s).

    - default mode: ensure image contract objects are structurally complete
    - --require-paths: for image.needed=true, require local source_hint path exists
    """
    result = ValidationResult()
    pages = load_planning_pages(path)
    if not pages:
        result.error("images: no planning pages found")
        return result, {"errors": 1, "warnings": 0}

    total_cards = 0
    needed_cards = 0
    hinted_cards = 0
    resolved_hints = 0

    for page in pages:
        slide_number = page.get("slide_number")
        page_label = f"slide {slide_number if slide_number is not None else '?'}"
        cards = page.get("cards") if isinstance(page.get("cards"), list) else []

        for index, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                continue
            total_cards += 1
            card_label = f"{page_label} card[{index}]"
            image = card.get("image")
            if not isinstance(image, dict):
                result.error(f"{card_label}: missing image contract")
                continue

            if not image.get("needed"):
                source_hint = image.get("source_hint")
                if source_hint not in (None, "", "null"):
                    result.warn(f"{card_label}: image.needed=false so image.source_hint should be null")
                continue

            needed_cards += 1
            for field_name in ("usage", "placement", "content_description", "source_hint"):
                if not is_non_empty_string(image.get(field_name)):
                    result.error(f"{card_label}: image.needed=true but image.{field_name} is empty")

            source_hint_raw = image.get("source_hint")
            if is_non_empty_string(source_hint_raw):
                hinted_cards += 1
            else:
                continue

            if not require_paths:
                continue

            source_hint = str(source_hint_raw).strip()
            lowered = source_hint.lower()
            if lowered.startswith(("http://", "https://", "data:")):
                result.error(f"{card_label}: image.source_hint must be a local file path when --require-paths")
                continue

            candidates = _resolve_local_path_candidates(path, source_hint)
            if any(item.exists() and item.is_file() for item in candidates):
                resolved_hints += 1
            else:
                result.error(f"{card_label}: image.source_hint path does not exist -> {source_hint}")

    summary = {
        "pages": len(pages),
        "cards": total_cards,
        "image_needed_cards": needed_cards,
        "cards_with_source_hint": hinted_cards,
        "resolved_source_hints": resolved_hints,
        "require_paths": require_paths,
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }
    return result, summary


def validate_html(path: Path, page_type: str) -> tuple[ValidationResult, dict[str, Any]]:
    result = ValidationResult()
    text = read_text(path)
    if not text:
        result.error("html: file is empty")
        return result, {"errors": 1, "warnings": 0}

    # Only enforce header/footer for 'content', 'toc', 'section' page types.
    if page_type in ("content", "toc", "section"):
        has_header = bool(re.search(r'<header[^>]*class=([\'"])[^\'"]*\bslide-header\b[^\'"]*\1[^>]*>', text, re.IGNORECASE))
        if not has_header:
            result.error(f"html: page type '{page_type}' must contain a <header class=\"slide-header\"> DOM element")
        
        has_footer = bool(re.search(r'<footer[^>]*class=([\'"])[^\'"]*\bslide-footer\b[^\'"]*\1[^>]*>', text, re.IGNORECASE))
        if not has_footer:
            result.error(f"html: page type '{page_type}' must contain a <footer class=\"slide-footer\"> DOM element")
    elif page_type not in ("cover", "end"):
        result.warn(f"html: unrecognized page_type '{page_type}'")

    summary = {
        "page_type": page_type,
        "errors": len(result.errors),
        "warnings": len(result.warnings),
    }
    return result, summary


def print_messages(result: ValidationResult) -> None:
    for item in result.errors:
        print(f"ERROR: {item}")
    for item in result.warnings:
        print(f"WARN:  {item}")


def write_report(path: str | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate v4 workflow contracts")
    subparsers = parser.add_subparsers(dest="command")

    text_contracts = {
        "interview": "Validate interview-qa.txt",
        "requirements-interview": "Validate requirements-interview.txt",
        "search": "Validate search.txt",
        "search-brief": "Validate search-brief.txt",
        "source-brief": "Validate source-brief.txt",
        "outline": "Validate outline.txt",
    }
    for name, help_text in text_contracts.items():
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("path", help="Path to the target text file")
        sub.add_argument("--strict", action="store_true", help="Treat warnings as failures")
        sub.add_argument("--report", help="Optional JSON report path")

    style_parser = subparsers.add_parser("style", help="Validate style.json")
    style_parser.add_argument("path", help="Path to style.json")
    style_parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    style_parser.add_argument("--report", help="Optional JSON report path")

    images = subparsers.add_parser("images", help="Validate image contracts in planning JSON")
    images.add_argument("path", help="Path to planning JSON file or directory")
    images.add_argument(
        "--require-paths",
        action="store_true",
        help="Require local source_hint file paths for cards with image.needed=true",
    )
    images.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    images.add_argument("--report", help="Optional JSON report path")

    review = subparsers.add_parser("page-review", help="Validate one review round result")
    review.add_argument("path", help="Path to review result (.txt or .json)")
    review.add_argument("--require-pass", action="store_true", help="Fail unless verdict=pass")
    review.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    review.add_argument("--report", help="Optional JSON report path")

    audit_request = subparsers.add_parser("page-audit-request", help="Validate one Step 4 audit patch request")
    audit_request.add_argument("path", help="Path to page-audit-request.txt")
    audit_request.add_argument("--base-dir", help="Base directory for resolving relative artifact paths")
    audit_request.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    audit_request.add_argument("--report", help="Optional JSON report path")

    manifest = subparsers.add_parser("delivery-manifest", help="Validate delivery-manifest.json")
    manifest.add_argument("path", help="Path to delivery-manifest.json")
    manifest.add_argument("--base-dir", help="Base directory for resolving relative artifact paths")
    manifest.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    manifest.add_argument("--report", help="Optional JSON report path")

    html_parser = subparsers.add_parser("html", help="Validate page html structure")
    html_parser.add_argument("path", help="Path to html file")
    html_parser.add_argument("--page-type", required=True, help="Type of the page (cover, content, toc, etc.)")
    html_parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    html_parser.add_argument("--report", help="Optional JSON report path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    target = Path(args.path)
    if not target.exists():
        print(f"ERROR: path not found: {target}", file=sys.stderr)
        return 1

    try:
        if args.command == "interview":
            result, payload = validate_interview(target)
        elif args.command == "requirements-interview":
            result, payload = validate_requirements_interview(target)
        elif args.command == "search":
            result, payload = validate_search(target)
        elif args.command == "search-brief":
            result, payload = validate_search_brief(target)
        elif args.command == "source-brief":
            result, payload = validate_source_brief(target)
        elif args.command == "outline":
            result, payload = validate_outline(target)
        elif args.command == "style":
            result, payload = validate_style(target)
        elif args.command == "images":
            result, payload = validate_images(target, bool(args.require_paths))
        elif args.command == "page-review":
            result, payload = validate_page_review(target, bool(args.require_pass))
        elif args.command == "page-audit-request":
            base_dir = Path(args.base_dir).resolve() if getattr(args, "base_dir", None) else None
            result, payload = validate_page_audit_request(target, base_dir)
        elif args.command == "html":
            result, payload = validate_html(target, getattr(args, "page_type", ""))
        else:
            base_dir = Path(args.base_dir).resolve() if args.base_dir else target.parent.resolve()
            result, payload = validate_delivery_manifest(target, base_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print_messages(result)
    if not result.errors and not result.warnings:
        print("OK")

    ok = result.ok and (not args.strict or not result.warnings)
    write_report(
        args.report,
        {
            "command": args.command,
            "ok": ok,
            "summary": payload,
            "errors": result.errors,
            "warnings": result.warnings,
        },
    )

    if result.errors:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
