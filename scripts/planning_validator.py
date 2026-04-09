#!/usr/bin/env python3
"""Validate Step 4 planning JSON files against the current deck schema.

The validator is intentionally conservative:
- supports wrapped deck payloads and single-page payloads
- validates current schema first, while tolerating a few legacy aliases
- checks referenced resources against the local references registry
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# resource_registry removed in v4 refactor; resource lookup inlined below
from workflow_versions import (
    PLANNING_CONTINUITY_VERSION,
    PLANNING_PACKET_VERSION,
    PLANNING_SCHEMA_VERSION,
    WORKFLOW_VERSION,
)


VALID_PAGE_TYPES = {"cover", "toc", "section", "content", "end"}
VALID_NARRATIVE_ROLES = {
    "cover", "toc", "section", "opening", "orientation", "transition", "setup", "evidence", "comparison",
    "framework", "process", "case", "quote", "breath", "close", "cta",
}
VALID_CARD_ROLES = {"anchor", "support", "context"}
VALID_CARD_TYPES = {
    "text", "data", "list", "process", "tag_cloud", "data_highlight",
    "timeline", "diagram", "quote", "comparison", "people", "image_hero",
    "matrix_chart",
}
VALID_CARD_STYLES = {"accent", "elevated", "filled", "outline", "glass", "transparent"}
VALID_ARGUMENT_ROLES = {
    "claim", "evidence", "contrast", "constraint", "method", "synthesis",
    "prerequisite", "framework",
}
VALID_LAYOUT_HINTS = {
    "single-focus", "symmetric", "asymmetric", "three-column", "primary-secondary",
    "hero-top", "mixed-grid", "l-shape", "t-shape", "waterfall", "free-cover",
    "free-section", "free-end", "toc-route",
}
VALID_DENSITY_BIASES = {"relaxed", "balanced", "ultra_dense"}
VALID_DENSITY_LABELS = {"low", "mid_low", "medium", "high", "dashboard"}
DENSITY_ORDER = {"low": 0, "mid_low": 1, "medium": 2, "high": 3, "dashboard": 4}
VALID_IMAGE_POLICIES = {"flexible", "support_only", "decorate_only"}
VALID_DECORATION_BUDGETS = {"generous", "medium", "low", "minimal"}
VALID_OVERFLOW_STRATEGIES = {
    "rebalance_layout", "tighten_budget", "table_or_microchart", "rollback_planning",
}
VALID_CHART_TYPES = {
    "kpi", "metric_row", "sparkline", "comparison_bar", "ring", "stacked_bar",
    "timeline", "funnel", "radar", "treemap", "waffle", "progress_bar", "rating",
}
VALID_IMAGE_USAGES = {
    "hero-background", "inline-illustration", "icon-accent", "data-visualization-bg",
}
VALID_IMAGE_PLACEMENTS = {"full-bleed", "left-half", "right-half", "card-bg", "inline"}

DENSITY_DEFAULTS = {
    "low": {
        "max_cards": 2,
        "max_charts": 1,
        "min_body_font_px": 24,
        "max_lines_per_card": 3,
        "image_policy": "flexible",
        "decoration_budget": "generous",
        "overflow_strategy": "rebalance_layout",
    },
    "mid_low": {
        "max_cards": 3,
        "max_charts": 1,
        "min_body_font_px": 20,
        "max_lines_per_card": 4,
        "image_policy": "flexible",
        "decoration_budget": "medium",
        "overflow_strategy": "rebalance_layout",
    },
    "medium": {
        "max_cards": 4,
        "max_charts": 2,
        "min_body_font_px": 18,
        "max_lines_per_card": 5,
        "image_policy": "support_only",
        "decoration_budget": "medium",
        "overflow_strategy": "tighten_budget",
    },
    "high": {
        "max_cards": 6,
        "max_charts": 2,
        "min_body_font_px": 16,
        "max_lines_per_card": 4,
        "image_policy": "support_only",
        "decoration_budget": "low",
        "overflow_strategy": "table_or_microchart",
    },
    "dashboard": {
        "max_cards": 8,
        "max_charts": 4,
        "min_body_font_px": 14,
        "max_lines_per_card": 3,
        "image_policy": "decorate_only",
        "decoration_budget": "minimal",
        "overflow_strategy": "rollback_planning",
    },
}


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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_wrapped_json(text: str) -> Any:
    text = text.strip()
    if not text:
        raise ValueError("Empty JSON input")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return json.loads(fenced.group(1))

    for tag in ("PPT_OUTLINE", "PPT_PLANNING"):
        pattern = rf"\[{tag}\]\s*```json\s*(\{{.*?\}})\s*```\s*\[/{tag}\]"
        match = re.search(pattern, text, re.S)
        if match:
            return json.loads(match.group(1))

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return json.loads(text[first:last + 1])
    raise ValueError("Could not parse JSON payload")


def load_jsonish(path: Path) -> Any:
    return extract_wrapped_json(read_text(path))


def natural_sort_key(path: Path) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", path.name)
    key: list[Any] = []
    for part in parts:
        key.append(int(part) if part.isdigit() else part.lower())
    return tuple(key)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_density_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower().replace("-", "_")
    return lowered if lowered in VALID_DENSITY_LABELS else None


def density_rank(label: str | None) -> int | None:
    return DENSITY_ORDER.get(label) if label else None


def normalize_page(page: dict[str, Any]) -> dict[str, Any]:
    """Accept a few legacy aliases without mutating the source payload."""
    normalized = dict(page)
    if "slide_number" not in normalized and "page_number" in normalized:
        normalized["slide_number"] = normalized["page_number"]
    if "page_goal" not in normalized and "goal" in normalized:
        normalized["page_goal"] = normalized["goal"]
    if "resources" not in normalized and "required_resources" in normalized:
        legacy = normalized.get("required_resources")
        if isinstance(legacy, dict):
            layout_refs = []
            if isinstance(legacy.get("layout"), str):
                layout_refs.append(legacy["layout"])
            layout_refs.extend(item for item in as_list(legacy.get("layout_refs")) if isinstance(item, str))

            principle_refs = list(as_list(legacy.get("principles")))
            principle_refs.extend(item for item in as_list(legacy.get("principle_refs")) if isinstance(item, str))

            normalized["resources"] = {
                "page_template": legacy.get("page_template"),
                "layout_refs": layout_refs,
                "block_refs": list(as_list(legacy.get("block_refs"))),
                "chart_refs": list(as_list(legacy.get("chart_refs"))),
                "principle_refs": principle_refs,
            }
    return normalized


def load_planning_pages(path: Path) -> list[dict[str, Any]]:
    def from_payload(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and "ppt_planning" in payload:
            deck = payload["ppt_planning"]
            return [normalize_page(page) for page in as_list(deck.get("pages")) if isinstance(page, dict)]
        if isinstance(payload, dict):
            page = payload.get("page") if isinstance(payload.get("page"), dict) else payload
            if isinstance(page, dict) and ("slide_number" in page or "page_number" in page):
                return [normalize_page(page)]
        return []

    if path.is_dir():
        pages: list[dict[str, Any]] = []
        files = sorted(path.glob("planning*.json"), key=natural_sort_key)
        if not files:
            raise ValueError(f"No planning*.json files found in {path}")
        for file_path in files:
            pages.extend(from_payload(load_jsonish(file_path)))
        return sorted(pages, key=lambda item: int(item.get("slide_number") or 0))

    pages = from_payload(load_jsonish(path))
    if not pages:
        raise ValueError(f"Unsupported planning payload: {path}")
    return pages


# Group name -> subdirectory mapping for resource lookup
_GROUP_DIRS = {
    "page_template": "page-templates",
    "layout_refs": "layouts",
    "block_refs": "blocks",
    "chart_refs": "charts",
    "principle_refs": "principles",
}


def resource_exists(refs_dir: Path, group: str, value: str) -> bool:
    if not value:
        return True
    raw = str(value).strip()
    direct = Path(raw)
    if direct.is_absolute():
        return direct.exists()
    if raw.startswith("references/"):
        return (refs_dir / raw.removeprefix("references/")).exists()
    # Resolve via group -> subdirectory mapping
    subdir = _GROUP_DIRS.get(group)
    if not subdir:
        return False
    # Try exact filename first, then with .md extension
    base_dir = refs_dir / subdir
    candidate = base_dir / raw
    if candidate.exists():
        return True
    candidate_md = base_dir / f"{raw}.md"
    if candidate_md.exists():
        return True
    # Try normalized: underscores to hyphens
    normalized = raw.replace("_", "-")
    candidate_norm = base_dir / f"{normalized}.md"
    return candidate_norm.exists()


def validate_card(
    card: dict[str, Any],
    page: dict[str, Any],
    page_label: str,
    index: int,
    refs_dir: Path | None,
    result: ValidationResult,
) -> None:
    card_label = f"{page_label} card[{index}]"
    card_id = card.get("card_id")
    if not isinstance(card_id, str) or not card_id.strip():
        result.error(f"{card_label}: missing card_id")
    role = card.get("role")
    if role not in VALID_CARD_ROLES:
        result.error(f"{card_label}: invalid role '{role}'")
    card_type = card.get("card_type")
    if card_type not in VALID_CARD_TYPES:
        result.error(f"{card_label}: invalid card_type '{card_type}'")
    style = card.get("card_style")
    if style not in VALID_CARD_STYLES:
        result.error(f"{card_label}: invalid card_style '{style}'")
    argument_role = card.get("argument_role")
    if argument_role and argument_role not in VALID_ARGUMENT_ROLES:
        result.warn(f"{card_label}: unknown argument_role '{argument_role}'")

    has_headline = isinstance(card.get("headline"), str) and card.get("headline").strip()
    has_body = bool([item for item in as_list(card.get("body")) if isinstance(item, str) and item.strip()])
    has_data = bool([item for item in as_list(card.get("data_points")) if isinstance(item, dict)])
    chart = card.get("chart") if isinstance(card.get("chart"), dict) else {}
    has_chart = bool(chart.get("chart_type"))
    if not any([has_headline, has_body, has_data, has_chart]):
        result.error(f"{card_label}: empty card payload")

    if has_chart and chart.get("chart_type") not in VALID_CHART_TYPES:
        result.error(f"{card_label}: invalid chart_type '{chart.get('chart_type')}'")

    budget = card.get("content_budget")
    if not isinstance(budget, dict):
        result.error(f"{card_label}: missing content_budget")
    else:
        max_lines = budget.get("body_max_lines")
        density_contract = page.get("density_contract") if isinstance(page.get("density_contract"), dict) else {}
        contract_max_lines = density_contract.get("max_lines_per_card")
        if isinstance(max_lines, int) and isinstance(contract_max_lines, int) and max_lines > contract_max_lines:
            result.error(
                f"{card_label}: content_budget.body_max_lines={max_lines} exceeds density_contract.max_lines_per_card={contract_max_lines}"
            )

    image = card.get("image")
    if not isinstance(image, dict):
        result.error(f"{card_label}: missing image contract")
    elif image.get("needed"):
        for field_name in ("usage", "placement", "content_description", "source_hint"):
            if not image.get(field_name):
                result.error(f"{card_label}: image.needed=true but image.{field_name} is empty")
        usage = image.get("usage")
        if usage not in VALID_IMAGE_USAGES:
            result.error(f"{card_label}: invalid image.usage '{usage}'")
        placement = image.get("placement")
        if placement not in VALID_IMAGE_PLACEMENTS:
            result.error(f"{card_label}: invalid image.placement '{placement}'")
    elif isinstance(image, dict):
        for field_name in ("usage", "placement", "content_description", "source_hint"):
            value = image.get(field_name)
            if value not in (None, "null"):
                result.warn(f"{card_label}: image.needed=false so image.{field_name} should be null")

    density_contract = page.get("density_contract") if isinstance(page.get("density_contract"), dict) else {}
    image_policy = density_contract.get("image_policy")
    if image_policy == "support_only":
        if isinstance(image, dict) and image.get("needed") and image.get("usage") == "hero-background":
            result.error(f"{card_label}: image_policy=support_only forbids hero-background images")
        if card.get("card_type") == "image_hero":
            result.error(f"{card_label}: image_policy=support_only forbids image_hero cards")
    elif image_policy == "decorate_only":
        if isinstance(image, dict) and image.get("needed"):
            result.error(f"{card_label}: image_policy=decorate_only forbids image.needed=true")
        if card.get("card_type") == "image_hero":
            result.error(f"{card_label}: image_policy=decorate_only forbids image_hero cards")

    if refs_dir:
        resource_ref = card.get("resource_ref")
        if isinstance(resource_ref, dict):
            mapping = {
                "block": "block_refs",
                "chart": "chart_refs",
                "principle": "principle_refs",
            }
            for key, group in mapping.items():
                value = resource_ref.get(key)
                if isinstance(value, str) and value.strip() and not resource_exists(refs_dir, group, value):
                    result.error(f"{card_label}: resource_ref.{key} not found: {value}")


def validate_workflow_metadata(page: dict[str, Any], label: str, result: ValidationResult) -> None:
    metadata = page.get("workflow_metadata")
    if metadata is None:
        result.warn(f"{label}: missing workflow_metadata")
        return
    if not isinstance(metadata, dict):
        result.warn(f"{label}: workflow_metadata should be an object")
        return

    checks = {
        "workflow_version": WORKFLOW_VERSION,
        "planning_schema_version": PLANNING_SCHEMA_VERSION,
        "planning_packet_version": PLANNING_PACKET_VERSION,
        "planning_continuity_version": PLANNING_CONTINUITY_VERSION,
    }
    for field_name, expected in checks.items():
        actual = metadata.get(field_name)
        if actual is None:
            result.warn(f"{label}: workflow_metadata.{field_name} is missing")
        elif actual != expected:
            result.warn(f"{label}: workflow_metadata.{field_name}={actual!r} != expected {expected!r}")


def validate_density_contract(page: dict[str, Any], label: str, result: ValidationResult) -> tuple[str | None, dict[str, Any]]:
    density_label = normalize_density_label(page.get("density_label"))
    if density_label is None:
        result.error(f"{label}: invalid density_label '{page.get('density_label')}'")

    density_reason = page.get("density_reason")
    if not isinstance(density_reason, str) or len(density_reason.strip()) < 4:
        result.error(f"{label}: missing meaningful density_reason")

    density_contract = page.get("density_contract")
    if not isinstance(density_contract, dict):
        result.error(f"{label}: missing density_contract")
        return density_label, {}

    deck_bias = density_contract.get("deck_bias")
    if deck_bias not in VALID_DENSITY_BIASES:
        result.error(f"{label}: density_contract.deck_bias must be one of {sorted(VALID_DENSITY_BIASES)}")

    lower = normalize_density_label(density_contract.get("page_lower_bound"))
    upper = normalize_density_label(density_contract.get("page_upper_bound"))
    if lower is None:
        result.error(f"{label}: density_contract.page_lower_bound is invalid")
    if upper is None:
        result.error(f"{label}: density_contract.page_upper_bound is invalid")
    lower_rank = density_rank(lower)
    upper_rank = density_rank(upper)
    label_rank = density_rank(density_label)
    if None not in (lower_rank, upper_rank) and lower_rank > upper_rank:
        result.error(f"{label}: density_contract.page_lower_bound cannot be greater than page_upper_bound")
    if None not in (lower_rank, upper_rank, label_rank) and not (lower_rank <= label_rank <= upper_rank):
        result.error(f"{label}: density_label must stay within density_contract page bounds")

    for field_name in ("max_cards", "max_charts", "min_body_font_px", "max_lines_per_card"):
        value = density_contract.get(field_name)
        if not isinstance(value, int) or value <= 0:
            result.error(f"{label}: density_contract.{field_name} must be a positive integer")

    image_policy = density_contract.get("image_policy")
    if image_policy not in VALID_IMAGE_POLICIES:
        result.error(f"{label}: density_contract.image_policy must be one of {sorted(VALID_IMAGE_POLICIES)}")

    decoration_budget = density_contract.get("decoration_budget")
    if decoration_budget not in VALID_DECORATION_BUDGETS:
        result.error(f"{label}: density_contract.decoration_budget must be one of {sorted(VALID_DECORATION_BUDGETS)}")

    overflow_strategy = density_contract.get("overflow_strategy")
    if overflow_strategy not in VALID_OVERFLOW_STRATEGIES:
        result.error(f"{label}: density_contract.overflow_strategy must be one of {sorted(VALID_OVERFLOW_STRATEGIES)}")

    if density_label in DENSITY_DEFAULTS and isinstance(density_contract, dict):
        defaults = DENSITY_DEFAULTS[density_label]
        for key, expected in defaults.items():
            actual = density_contract.get(key)
            if actual != expected:
                result.warn(f"{label}: density_contract.{key}={actual!r} != recommended {expected!r} for density_label={density_label}")

    page_type = page.get("page_type")
    if page_type in {"cover", "section", "end"} and density_label == "dashboard":
        result.error(f"{label}: page_type '{page_type}' cannot use density_label 'dashboard'")
    if density_label == "dashboard" and page_type != "content":
        result.error(f"{label}: dashboard density_label is only allowed on content pages")
    if density_label == "dashboard":
        layout = page.get("layout_hint")
        if layout not in {"mixed-grid", "t-shape"}:
            result.error(f"{label}: dashboard pages must use layout_hint 'mixed-grid' or 't-shape'")
        if image_policy != "decorate_only":
            result.error(f"{label}: dashboard pages must use image_policy=decorate_only")

    if page_type == "content" and deck_bias == "relaxed" and density_label == "dashboard":
        result.error(f"{label}: relaxed deck_bias forbids dashboard content pages")
    if page_type == "content" and deck_bias == "balanced" and label_rank is not None and label_rank < DENSITY_ORDER["mid_low"]:
        result.error(f"{label}: balanced deck_bias content pages cannot be below mid_low")
    if page_type == "content" and deck_bias == "ultra_dense" and label_rank is not None and label_rank < DENSITY_ORDER["medium"]:
        result.error(f"{label}: ultra_dense deck_bias content pages cannot be below medium")

    return density_label, density_contract


def validate_page(page: dict[str, Any], refs_dir: Path | None) -> ValidationResult:
    result = ValidationResult()
    slide_number = page.get("slide_number")
    label = f"slide {slide_number if slide_number is not None else '?'}"

    required_fields = (
        "slide_number", "page_type", "title", "page_goal", "cards", "visual_weight",
        "density_label", "density_reason", "density_contract",
    )
    for field_name in required_fields:
        if field_name not in page:
            result.error(f"{label}: missing required field '{field_name}'")

    if not isinstance(slide_number, int):
        result.error(f"{label}: slide_number must be an integer")

    page_type = page.get("page_type")
    if page_type not in VALID_PAGE_TYPES:
        result.error(f"{label}: invalid page_type '{page_type}'")

    narrative_role = page.get("narrative_role")
    if narrative_role and narrative_role not in VALID_NARRATIVE_ROLES:
        result.warn(f"{label}: unknown narrative_role '{narrative_role}'")

    visual_weight = page.get("visual_weight")
    if not isinstance(visual_weight, int) or not (1 <= visual_weight <= 9):
        result.error(f"{label}: visual_weight must be an integer in [1, 9]")

    if page_type == "content":
        layout_hint = page.get("layout_hint")
        if not isinstance(layout_hint, str) or not layout_hint:
            result.error(f"{label}: content page requires layout_hint")
        elif layout_hint not in VALID_LAYOUT_HINTS:
            result.warn(f"{label}: non-standard layout_hint '{layout_hint}'")

    density_label, density_contract = validate_density_contract(page, label, result)
    validate_workflow_metadata(page, label, result)

    cards = [card for card in as_list(page.get("cards")) if isinstance(card, dict)]
    if page_type == "content" and len(cards) < 2:
        result.warn(f"{label}: content page has only {len(cards)} cards")
    if not cards:
        result.error(f"{label}: cards[] is empty")

    if isinstance(density_contract.get("max_cards"), int) and len(cards) > density_contract["max_cards"]:
        result.error(f"{label}: cards count {len(cards)} exceeds density_contract.max_cards={density_contract['max_cards']}")

    chart_count = sum(
        1 for card in cards
        if isinstance(card.get("chart"), dict) and isinstance(card.get("chart", {}).get("chart_type"), str)
    )
    if isinstance(density_contract.get("max_charts"), int) and chart_count > density_contract["max_charts"]:
        result.error(f"{label}: chart count {chart_count} exceeds density_contract.max_charts={density_contract['max_charts']}")

    anchor_count = sum(1 for card in cards if card.get("role") == "anchor")
    if anchor_count == 0:
        result.error(f"{label}: missing anchor card")
    if anchor_count > 1:
        result.error(f"{label}: multiple anchor cards ({anchor_count})")

    card_styles = {card.get("card_style") for card in cards if isinstance(card.get("card_style"), str)}
    if page_type == "content" and len(cards) >= 2 and len(card_styles) < 2:
        result.error(f"{label}: content page with multiple cards needs at least 2 card styles")

    accent_count = sum(1 for card in cards if card.get("card_style") == "accent")
    elevated_count = sum(1 for card in cards if card.get("card_style") == "elevated")
    if accent_count > 1:
        result.warn(f"{label}: accent card_style appears {accent_count} times")
    if elevated_count > 1:
        result.warn(f"{label}: elevated card_style appears {elevated_count} times")

    if not isinstance(page.get("director_command"), dict):
        result.error(f"{label}: missing director_command")
    if not isinstance(page.get("decoration_hints"), dict):
        result.error(f"{label}: missing decoration_hints")
    if page_type == "content" and not isinstance(page.get("source_guidance"), dict):
        result.error(f"{label}: content page missing source_guidance")

    resources = page.get("resources")
    if not isinstance(resources, dict):
        result.error(f"{label}: missing resources")
    else:
        if refs_dir:
            page_template = resources.get("page_template")
            if isinstance(page_template, str) and page_template and not resource_exists(refs_dir, "page_template", page_template):
                result.error(f"{label}: resources.page_template not found: {page_template}")
            for group in ("layout_refs", "block_refs", "chart_refs", "principle_refs"):
                for item in as_list(resources.get(group)):
                    if isinstance(item, str) and item.strip() and not resource_exists(refs_dir, group, item):
                        result.error(f"{label}: resources.{group} not found: {item}")

    for index, card in enumerate(cards, start=1):
        validate_card(card, page, label, index, refs_dir, result)

    return result


def validate_cross_page(pages: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    if not pages:
        return result

    seen_numbers: set[int] = set()
    last_content_layout: str | None = None
    high_pressure_streak = 0

    for index, page in enumerate(pages):
        slide_number = page.get("slide_number")
        label = f"slide {slide_number}"
        if isinstance(slide_number, int):
            if slide_number in seen_numbers:
                result.error(f"{label}: duplicate slide_number")
            seen_numbers.add(slide_number)

        if page.get("page_type") == "content":
            layout = page.get("layout_hint")
            if isinstance(layout, str) and layout == last_content_layout:
                result.warn(f"{label}: repeats previous content layout_hint '{layout}'")
            last_content_layout = layout if isinstance(layout, str) else last_content_layout

        density_label = normalize_density_label(page.get("density_label"))
        if density_label in {"high", "dashboard"}:
            high_pressure_streak += 1
        else:
            high_pressure_streak = 0
        if high_pressure_streak >= 3:
            result.error(f"{label}: 3 consecutive slides with density_label in {{high, dashboard}}")

        if density_label == "dashboard":
            prev_label = normalize_density_label(pages[index - 1].get("density_label")) if index > 0 else None
            next_label = normalize_density_label(pages[index + 1].get("density_label")) if index + 1 < len(pages) else None
            if prev_label is None or next_label is None or prev_label == "dashboard" or next_label == "dashboard":
                result.error(f"{label}: dashboard 前后必须至少有 1 页非 dashboard 过渡")

    sorted_numbers = sorted(number for number in seen_numbers)
    if sorted_numbers and sorted_numbers != list(range(min(sorted_numbers), max(sorted_numbers) + 1)):
        result.warn("slide numbers are not consecutive")

    return result


def format_result(result: ValidationResult) -> str:
    lines: list[str] = []
    lines.extend(f"ERROR: {item}" for item in result.errors)
    lines.extend(f"WARN:  {item}" for item in result.warnings)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PPT planning JSON files")
    parser.add_argument("path", help="Single planning JSON file or directory containing planning*.json")
    parser.add_argument("--refs", help="Path to references directory")
    parser.add_argument("--page", type=int, help="Validate only one slide_number from the target payload")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--report", help="Optional path to write a JSON report")
    args = parser.parse_args()

    target = Path(args.path)
    refs_dir = Path(args.refs).resolve() if args.refs else None
    if refs_dir and not refs_dir.is_dir():
        print(f"ERROR: references directory not found: {refs_dir}", file=sys.stderr)
        return 1

    try:
        pages = load_planning_pages(target)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.page is not None:
        pages = [page for page in pages if int(page.get("slide_number") or 0) == args.page]
        if not pages:
            print(f"ERROR: slide_number {args.page} not found in {target}", file=sys.stderr)
            return 1

    page_reports = []
    aggregate = ValidationResult()
    for page in pages:
        page_result = validate_page(page, refs_dir)
        aggregate.errors.extend(page_result.errors)
        aggregate.warnings.extend(page_result.warnings)
        page_reports.append(
            {
                "slide_number": page.get("slide_number"),
                "errors": page_result.errors,
                "warnings": page_result.warnings,
            }
        )

    cross_page = validate_cross_page(pages)
    aggregate.errors.extend(cross_page.errors)
    aggregate.warnings.extend(cross_page.warnings)

    report_payload = {
        "ok": aggregate.ok and (not args.strict or not aggregate.warnings),
        "pages": page_reports,
        "cross_page": {
            "errors": cross_page.errors,
            "warnings": cross_page.warnings,
        },
        "summary": {
            "total_pages": len(pages),
            "error_count": len(aggregate.errors),
            "warning_count": len(aggregate.warnings),
        },
    }
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output = format_result(aggregate)
    if output:
        print(output)
    if not aggregate.errors and not aggregate.warnings:
        print(f"OK: {len(pages)} page(s) validated")

    if aggregate.errors:
        return 1
    if args.strict and aggregate.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
