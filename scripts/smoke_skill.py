#!/usr/bin/env python3
"""Minimal end-to-end smoke test for the PPT workflow skill.

This script intentionally stays within the current markdown/code architecture.
It exercises the most failure-prone integration points:
1. Step 0 interview prompt rendering (structured/text dual templates)
2. Step 3 outline density contract for relaxed / balanced / ultra_dense
3. Step 4 planning density labels / deck_bias windows -> planning_validator.py
4. visual_qa.py for PNG + planning + HTML double checks
5. resource_loader.py menu / resolve / images
6. prompt_harness.py for the Step 4 prompt chain
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from planning_validator import DENSITY_DEFAULTS  # noqa: E402
from workflow_versions import (  # noqa: E402
    PLANNING_CONTINUITY_VERSION,
    PLANNING_PACKET_VERSION,
    PLANNING_SCHEMA_VERSION,
    WORKFLOW_VERSION,
)

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - smoke will fail later with a clear error
    Image = None
    ImageDraw = None


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
REFERENCES_DIR = ROOT_DIR / "references"
PLAYBOOK_PATH = REFERENCES_DIR / "playbooks/step4/page-planning-playbook.md"
PAGE_TEMPLATE_EXPECTATIONS = {
    "cover": "# 封面页 -- 演讲的第一声呼吸",
    "toc": "# 目录页 -- 演讲的地图俯瞰",
    "section": "# 章节封面页 -- 演讲中的呼吸",
    "end": "# 结束页 -- 演讲的最后一个视觉印记",
}
BIAS_BOUNDS = {
    "relaxed": ("low", "medium"),
    "balanced": ("mid_low", "high"),
    "ultra_dense": ("medium", "dashboard"),
}


@dataclass
class SmokeResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.steps.append(message)


def run_cmd(label: str, args: list[str], result: SmokeResult, cwd: Path = ROOT_DIR) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        result.error(
            f"{label}: exit={proc.returncode}\n"
            f"cmd={' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    else:
        result.note(f"{label}: ok")
    return proc


def run_cmd_expect_failure(
    label: str,
    args: list[str],
    result: SmokeResult,
    expected_tokens: list[str] | None = None,
    cwd: Path = ROOT_DIR,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0:
        result.error(
            f"{label}: expected failure but exit=0\n"
            f"cmd={' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
        return proc

    haystack = f"{proc.stdout}\n{proc.stderr}"
    if expected_tokens:
        missing = [token for token in expected_tokens if token not in haystack]
        if missing:
            result.error(f"{label}: expected failure output missing tokens {missing}")
    result.note(f"{label}: expected-fail ok")
    return proc


def run_cmd_allow_codes(
    label: str,
    args: list[str],
    result: SmokeResult,
    allowed_codes: set[int],
    cwd: Path = ROOT_DIR,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    if proc.returncode not in allowed_codes:
        result.error(
            f"{label}: exit={proc.returncode}, expected one of {sorted(allowed_codes)}\n"
            f"cmd={' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    else:
        suffix = "" if proc.returncode == 0 else f" (exit={proc.returncode})"
        result.note(f"{label}: ok{suffix}")
    return proc


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_card(
    slide_number: int,
    role: str,
    index: int,
    headline: str,
    body: list[str],
    card_type: str,
    card_style: str,
    body_max_lines: int,
    chart_type: str | None = None,
) -> dict[str, object]:
    card_id = f"s{slide_number:02d}-{role}-{index}"
    payload: dict[str, object] = {
        "card_id": card_id,
        "role": role,
        "card_type": card_type,
        "card_style": card_style,
        "argument_role": "claim" if role == "anchor" else "evidence",
        "headline": headline,
        "body": body,
        "data_points": [],
        "content_budget": {
            "headline_max_chars": 12,
            "body_max_bullets": min(3, max(1, len(body))),
            "body_max_lines": body_max_lines,
        },
        "image": {
            "mode": "decorate",
            "needed": False,
            "usage": None,
            "placement": None,
            "content_description": None,
            "source_hint": None,
            "decorate_brief": "只用内部装饰，不引入外部图片。",
        },
    }
    if chart_type:
        payload["chart"] = {"chart_type": chart_type}
        payload["data_points"] = [
            {"label": headline, "value": str(20 + index * 7), "unit": "%", "source": f"smoke-source-{index}"}
        ]
        payload["resource_ref"] = {"chart": chart_type.replace("_", "-"), "principle": "visual-hierarchy"}
    else:
        payload["resource_ref"] = {"principle": "composition"}
    return payload


def build_content_page_fixture(
    *,
    slide_number: int = 3,
    deck_bias: str = "balanced",
    density_label: str = "medium",
) -> dict[str, object]:
    """Build a content page planning fixture for density smoke tests."""
    defaults = copy.deepcopy(DENSITY_DEFAULTS[density_label])
    lower_bound, upper_bound = BIAS_BOUNDS[deck_bias]
    base_cards = {
        "low": [
            make_card(slide_number, "anchor", 1, "一句判断", ["先给出核心判断"], "data_highlight", "accent", 3, "kpi"),
            make_card(slide_number, "support", 1, "一句解释", ["只补一层解释"], "text", "outline", 3),
        ],
        "mid_low": [
            make_card(slide_number, "anchor", 1, "判断先行", ["先说结论，再补解释"], "data_highlight", "accent", 4, "kpi"),
            make_card(slide_number, "support", 1, "证据一", ["第一组支撑信息"], "data", "outline", 4),
            make_card(slide_number, "context", 1, "范围说明", ["补充边界与上下文"], "text", "transparent", 4),
        ],
        "medium": [
            make_card(slide_number, "anchor", 1, "核心指标", ["一句解释它为什么重要"], "data_highlight", "accent", 4, "kpi"),
            make_card(slide_number, "support", 1, "增长原因", ["增长主要来自高客单区域放量"], "data", "outline", 4, "metric_row"),
            make_card(slide_number, "support", 2, "区域分布", ["北区与华东贡献最高"], "comparison", "filled", 4),
            make_card(slide_number, "context", 1, "边界条件", ["样本期已排除促销异常"], "text", "transparent", 4),
        ],
        "high": [
            make_card(slide_number, "anchor", 1, "高密结论", ["先看结论，再扫读其余 5 卡"], "data_highlight", "accent", 4, "kpi"),
            make_card(slide_number, "support", 1, "渠道", ["直营增长更稳"], "data", "outline", 4, "metric_row"),
            make_card(slide_number, "support", 2, "区域", ["东区拉动明显"], "data", "filled", 4),
            make_card(slide_number, "support", 3, "客群", ["老客复购抬升"], "comparison", "outline", 4),
            make_card(slide_number, "context", 1, "节奏", ["增长发生在两个阶段"], "timeline", "transparent", 4),
            make_card(slide_number, "context", 2, "风险", ["高客单区需继续验证"], "text", "glass", 4),
        ],
        "dashboard": [
            make_card(slide_number, "anchor", 1, "总览", ["整页以扫读为主，不做大图"], "data_highlight", "accent", 3, "kpi"),
            make_card(slide_number, "support", 1, "营收", ["营收抬升"], "data", "outline", 3, "metric_row"),
            make_card(slide_number, "support", 2, "转化", ["转化改善"], "data", "filled", 3, "progress_bar"),
            make_card(slide_number, "support", 3, "结构", ["结构更健康"], "comparison", "glass", 3, "comparison_bar"),
            make_card(slide_number, "support", 4, "客群", ["新客占比抬升"], "data", "outline", 3),
            make_card(slide_number, "context", 1, "地区", ["东区领先"], "text", "transparent", 3),
            make_card(slide_number, "context", 2, "阶段", ["第二阶段最强"], "timeline", "transparent", 3),
            make_card(slide_number, "context", 3, "提醒", ["仍需防止误读"], "quote", "outline", 3),
        ],
    }
    layout_hint = "mixed-grid" if density_label == "dashboard" else ("hero-top" if density_label in {"low", "medium"} else "asymmetric" if density_label == "mid_low" else "t-shape")
    chart_refs = sorted(
        {
            str(card.get("chart", {}).get("chart_type", "")).replace("_", "-")
            for card in base_cards[density_label]
            if isinstance(card.get("chart"), dict) and card["chart"].get("chart_type")
        }
    )
    return {
        "page": {
            "slide_number": slide_number,
            "page_type": "content",
            "narrative_role": "evidence",
            "title": f"{density_label} smoke",
            "page_goal": f"验证 {density_label} 密度合同",
            "audience_takeaway": f"{density_label} page passes planning gate",
            "visual_weight": {"low": 4, "mid_low": 5, "medium": 7, "high": 8, "dashboard": 9}[density_label],
            "density_label": density_label,
            "density_reason": f"作为 {deck_bias} deck 的 {density_label} 示例页，验证页级预算与窗口绑定。",
            "density_contract": {
                "deck_bias": deck_bias,
                "page_lower_bound": lower_bound,
                "page_upper_bound": upper_bound,
                **defaults,
            },
            "layout_hint": layout_hint,
            "layout_variation_note": f"用于验证 {deck_bias} -> {density_label} 的固定施工模式。",
            "focus_zone": "中心偏上" if density_label in {"low", "medium"} else "网格核心区",
            "negative_space_target": "high" if density_label == "low" else "medium" if density_label in {"mid_low", "medium"} else "low",
            "page_text_strategy": "短句化、先结论再证据",
            "rhythm_action": "推进",
            "must_avoid": ["禁止把导演指令渲染成正文"],
            "variation_guardrails": {
                "same_gene_as_deck": "统一字体与强调色",
                "different_from_previous": [f"验证 {density_label} 专属预算与骨架"],
            },
            "director_command": {
                "mood": f"{density_label} 密度冒烟页",
                "spatial_strategy": "主锚先读，其余卡片次序清晰",
                "anchor_treatment": "只保留一个主锚点",
                "techniques": ["T1", "W3"],
                "prose": "先结论后扫读，结构稳定优先。",
            },
            "decoration_hints": {
                "background": {"feel": "克制背景", "restraint": "不抢正文", "techniques": ["T1"]},
                "floating": {"feel": "轻量装饰", "restraint": "只服务动线", "techniques": ["W3"] if density_label in {"low", "mid_low", "medium"} else []},
                "page_accent": {"feel": "强调色聚焦锚点", "restraint": "不超过 2 个亮点", "techniques": ["T9"]},
            },
            "source_guidance": {
                "brief_sections": ["核心发现"],
                "citation_expectation": "有数字就保留来源",
                "strictness": "不得超出 brief 结论边界",
            },
            "resources": {
                "page_template": None,
                "layout_refs": [layout_hint],
                "block_refs": [],
                "chart_refs": chart_refs,
                "principle_refs": ["visual-hierarchy", "composition"],
                "resource_rationale": f"验证 {density_label} 密度页的布局与预算合同。",
            },
            "cards": base_cards[density_label],
            "workflow_metadata": {
                "stage": "planning",
                "workflow_version": WORKFLOW_VERSION,
                "planning_schema_version": PLANNING_SCHEMA_VERSION,
                "planning_packet_version": PLANNING_PACKET_VERSION,
                "planning_continuity_version": PLANNING_CONTINUITY_VERSION,
            },
        }
    }


def build_outline_fixture(density_bias: str) -> str:
    if density_bias == "relaxed":
        curve = "low -> medium -> high -> mid_low"
        pages = [
            ("1", "封面", "cover", "low", "low", "mid_low", "铺垫", "呼吸页", "标题"),
            ("2", "背景判断", "content", "low", "medium", "medium", "推进", "证据页", "KPI"),
            ("3", "高潮论证", "content", "medium", "high", "high", "爆发", "证据页", "KPI"),
            ("4", "收束", "end", "mid_low", "mid_low", "medium", "收束", "结论页", "标题"),
        ]
    elif density_bias == "ultra_dense":
        curve = "medium -> medium -> dashboard -> medium -> high"
        pages = [
            ("1", "封面", "cover", "medium", "medium", "high", "铺垫", "呼吸页", "标题"),
            ("2", "总览", "content", "medium", "medium", "high", "推进", "证据页", "KPI"),
            ("3", "仪表盘", "content", "high", "dashboard", "dashboard", "爆发", "仪表盘页", "表格"),
            ("4", "缓冲", "content", "medium", "medium", "high", "缓冲", "证据页", "表格"),
            ("5", "收束", "end", "medium", "high", "high", "收束", "结论页", "标题"),
        ]
    else:
        curve = "mid_low -> medium -> high -> mid_low"
        pages = [
            ("1", "封面", "cover", "mid_low", "mid_low", "medium", "铺垫", "呼吸页", "标题"),
            ("2", "背景判断", "content", "mid_low", "medium", "high", "推进", "证据页", "KPI"),
            ("3", "增长判断", "content", "mid_low", "high", "high", "爆发", "证据页", "KPI"),
            ("4", "收束", "end", "mid_low", "mid_low", "medium", "收束", "结论页", "标题"),
        ]
    lines = [
        "# 大纲",
        "核心论点：社区价值成立",
        "叙事结构：是什么->为什么->怎么做",
        f"密度倾向：{density_bias}",
        f"密度曲线：{curve}",
        f"总页数：{len(pages)}",
        "",
        "---",
        "",
        "## Part 1: Demo",
        "Part 目标：验证密度曲线",
        "论证策略：data_driven",
        "与上一 Part 的关系：无（首Part）",
        "",
    ]
    for page_no, title, page_type, lower, target, upper, rhythm, posture, anchor in pages:
        lines.extend(
            [
                f"### 第 {page_no} 页：{title}",
                f"- 页目标：验证 {title}",
                "- 叙事角色：evidence",
                f"- 页面类型映射：{page_type}",
                f"- 密度下限：{lower}",
                f"- 密度目标：{target}",
                f"- 密度上限：{upper}",
                f"- 节奏动作：{rhythm}",
                f"- 信息姿态：{posture}",
                f"- 锚点类型：{anchor}",
                "- 论证方式：数据驱动",
                "- 内容支撑：用示例内容验证合同",
                "- 素材来源：found_in_brief: true",
                "",
            ]
        )
    lines.extend(["---", "SELF_REVIEW_PASS", "自审轮数：1", "自审时间：2026-04-09 12:00", ""])
    return "\n".join(lines)


def build_html_fixture(
    page_payload: dict[str, object],
    *,
    decoration_count: int,
    font_px: int | None = None,
    include_img: bool = False,
    include_bg_url: bool = False,
    omit_header: bool = False,
    omit_footer: bool = False,
    decoration_aria_hidden: bool = True,
) -> str:
    page = page_payload["page"] if "page" in page_payload else page_payload
    assert isinstance(page, dict)
    density_contract = page.get("density_contract", {})
    min_font = int(density_contract.get("min_body_font_px", 18)) if isinstance(density_contract, dict) else 18
    body_font = font_px or max(min_font, 18)
    title = str(page.get("title", "Smoke"))
    cards = [card for card in page.get("cards", []) if isinstance(card, dict)]
    decoration_layers = ["background", "floating", "page-accent"]

    decoration_parts = []
    for index in range(decoration_count):
        layer = decoration_layers[index % len(decoration_layers)]
        aria_attr = ' aria-hidden="true"' if decoration_aria_hidden else ""
        decoration_parts.append(
            f'<div class="decor decor-{index + 1}" data-decoration-layer="{layer}"{aria_attr}></div>'
        )

    card_parts = []
    for index, card in enumerate(cards, start=1):
        role = str(card.get("role") or "support")
        body_lines = "".join(f"<li>{item}</li>" for item in card.get("body", []) if isinstance(item, str))
        chart_markup = ""
        chart = card.get("chart")
        if isinstance(chart, dict) and chart.get("chart_type"):
            chart_markup = f'<div class="chart">{chart["chart_type"]}</div>'
        card_parts.append(
            "\n".join(
                [
                    f'<section class="card {role}" data-card-id="{card["card_id"]}">',
                    f'  <h3>{card.get("headline", f"card-{index}")}</h3>',
                    f'  <ul>{body_lines or "<li>smoke</li>"}</ul>',
                    f"  {chart_markup}",
                    "</section>",
                ]
            )
        )

    header_markup = ""
    footer_markup = ""
    page_type = str(page.get("page_type") or "").strip().lower()
    if page_type in {"content", "toc", "section"} and not omit_header:
        header_markup = '<header class="slide-header"><span class="overline">Smoke</span><h1 class="page-title">测试页</h1></header>'
    if page_type in {"content", "toc", "section"} and not omit_footer:
        footer_markup = '<footer class="slide-footer"><span>01</span><span>smoke</span></footer>'
    img_markup = '<img class="hero-shot" src="../images/smoke-image.svg" alt="smoke" />' if include_img else ""
    bg_style = "background-image:url(../images/smoke-image.svg);" if include_bg_url else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      width: 1280px;
      height: 720px;
      margin: 0;
      overflow: hidden;
      font-family: 'Noto Sans SC', sans-serif;
      color: #f8fafc;
      background: linear-gradient(135deg, #0f172a, #111827);
    }}
    .stage {{
      position: relative;
      width: 1280px;
      height: 720px;
      padding: 88px 56px 56px;
      {bg_style}
    }}
    .slide-header, .slide-footer {{
      position: absolute;
      left: 40px;
      right: 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 20;
    }}
    .slide-header {{ top: 20px; }}
    .slide-footer {{ bottom: 12px; font-size: {max(min_font, 14)}px; color: #cbd5e1; }}
    .cards {{
      position: relative;
      z-index: 10;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }}
    .card {{
      min-height: 150px;
      padding: 20px;
      border: 1px solid rgba(148, 163, 184, 0.35);
      border-radius: 24px;
      background: rgba(15, 23, 42, 0.62);
      backdrop-filter: blur(8px);
      font-size: {body_font}px;
      line-height: 1.55;
    }}
    .card.anchor {{
      border-color: #38bdf8;
      box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.4);
    }}
    .card h3 {{ margin: 0 0 10px; font-size: {max(body_font + 10, 24)}px; line-height: 1.2; }}
    .card ul {{ margin: 0; padding-left: 18px; }}
    .chart {{
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid rgba(148, 163, 184, 0.25);
      color: #38bdf8;
      font-weight: 700;
      letter-spacing: 0.04em;
    }}
    .decor {{
      position: absolute;
      z-index: 1;
      pointer-events: none;
      border-radius: 999px;
      opacity: 0.18;
      filter: blur(2px);
    }}
    .decor-1 {{ width: 280px; height: 280px; top: -30px; right: 60px; background: #38bdf8; }}
    .decor-2 {{ width: 180px; height: 180px; bottom: 80px; right: 120px; background: #22c55e; }}
    .decor-3 {{ width: 140px; height: 140px; top: 260px; left: 24px; background: #a78bfa; }}
    .decor-4 {{ width: 120px; height: 120px; bottom: 120px; left: 420px; background: #f59e0b; }}
    .decor-5 {{ width: 96px; height: 96px; top: 140px; right: 360px; background: #38bdf8; }}
    .hero-shot {{
      position: absolute;
      right: 56px;
      bottom: 72px;
      width: 180px;
      height: 120px;
      border-radius: 16px;
      object-fit: cover;
      z-index: 8;
    }}
  </style>
</head>
<body>
  <div class="stage">
    {header_markup}
    {''.join(decoration_parts)}
    <main class="cards">
      {''.join(card_parts)}
    </main>
    {img_markup}
    {footer_markup}
  </div>
</body>
</html>
"""


def write_smoke_png(path: Path) -> None:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required for smoke PNG generation")
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1280, 720), "#0f172a")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((34, 20, 1246, 84), radius=18, outline="#38bdf8", width=2)
    draw.text((60, 38), "Smoke Header", fill="#f8fafc")
    draw.rounded_rectangle((56, 116, 650, 356), radius=28, fill="#111827", outline="#38bdf8", width=3)
    draw.rounded_rectangle((678, 116, 1224, 270), radius=24, fill="#1e293b", outline="#22c55e", width=2)
    draw.rounded_rectangle((678, 292, 1224, 518), radius=24, fill="#172033", outline="#a78bfa", width=2)
    draw.rounded_rectangle((56, 388, 650, 620), radius=24, fill="#172033", outline="#f59e0b", width=2)
    draw.rounded_rectangle((678, 546, 1224, 650), radius=18, fill="#0b1220", outline="#38bdf8", width=2)
    for x in range(0, 1280, 16):
        for y in range(0, 720, 16):
            color = (
                10 + (x // 16 * 5) % 36,
                18 + (y // 16 * 7) % 44,
                28 + ((x + y) // 16 * 9) % 56,
            )
            draw.rectangle((x, y, x + 7, y + 7), fill=color)
    draw.ellipse((910, -20, 1180, 250), fill="#12324b")
    draw.ellipse((930, 0, 1150, 220), fill="#1d4f73")
    for y in range(140, 600, 26):
        draw.line((94, y, 610, y), fill="#cbd5e1", width=2)
    for y in range(146, 250, 22):
        draw.line((716, y, 1180, y), fill="#cbd5e1", width=2)
    for x in (736, 862, 988, 1114):
        draw.rectangle((x, 360, x + 72, 480), fill="#38bdf8")
    draw.text((92, 140), "Anchor KPI", fill="#f8fafc")
    draw.rounded_rectangle((718, 138, 1172, 168), radius=12, fill="#cbd5e1")
    draw.rounded_rectangle((718, 314, 1120, 344), radius=12, fill="#cbd5e1")
    draw.text((92, 412), "Evidence Notes", fill="#f8fafc")
    draw.text((1110, 672), "01", fill="#cbd5e1")
    img.save(path)


def assert_contains(label: str, haystack: str, needles: list[str], result: SmokeResult) -> None:
    missing = [needle for needle in needles if needle not in haystack]
    if missing:
        result.error(f"{label}: missing expected content {missing}")


def assert_no_unfilled_vars(label: str, text: str, result: SmokeResult) -> None:
    leftovers = sorted(set(re.findall(r"\{\{[A-Z_][A-Z0-9_]*\}\}", text)))
    if leftovers:
        result.error(f"{label}: unfilled template vars remain: {leftovers}")


def assert_max_bytes(label: str, text: str, max_bytes: int, result: SmokeResult) -> None:
    size = len(text.encode("utf-8"))
    if size > max_bytes:
        result.error(f"{label}: rendered prompt too large ({size} bytes > {max_bytes} bytes)")


def build_non_content_page(page_type: str) -> dict[str, object]:
    return {
        "page": {
            "slide_number": 1,
            "page_type": page_type,
            "narrative_role": "opening" if page_type == "cover" else "transition",
            "title": f"Smoke {page_type}",
            "page_goal": f"验证 {page_type} 页面模板路由",
            "audience_takeaway": f"{page_type} page template resolve",
            "visual_weight": 5,
            "density_label": "mid_low",
            "density_reason": "非 content 页只验证模板路由，保持克制密度。",
            "density_contract": {
                "deck_bias": "balanced",
                "page_lower_bound": "low",
                "page_upper_bound": "medium",
                "max_cards": 3,
                "max_charts": 1,
                "min_body_font_px": 20,
                "max_lines_per_card": 4,
                "image_policy": "flexible",
                "decoration_budget": "medium",
                "overflow_strategy": "rebalance_layout",
            },
            "focus_zone": "center",
            "negative_space_target": "medium",
            "page_text_strategy": "短句为主",
            "rhythm_action": "推进",
            "must_avoid": [],
            "variation_guardrails": {
                "same_gene_as_deck": "保留统一风格变量",
                "different_from_previous": ["验证 page template 路由"],
            },
            "director_command": {
                "mood": "测试态",
                "spatial_strategy": "居中聚焦",
                "anchor_treatment": "标题优先",
                "techniques": ["T1"],
                "prose": "用于验证非 content 页的模板消费链。",
            },
            "decoration_hints": {
                "background": {"feel": "轻量背景", "restraint": "不抢主标题", "techniques": ["T1"]},
                "floating": {"feel": "弱装饰", "restraint": "仅做陪衬", "techniques": []},
                "page_accent": {"feel": "少量强调色", "restraint": "仅一处强调", "techniques": []},
            },
            "resources": {
                "page_template": None,
                "layout_refs": [],
                "block_refs": [],
                "chart_refs": [],
                "principle_refs": [],
                "resource_rationale": "验证 page_type 自动路由到 page-templates/",
            },
            "cards": [
                {
                    "card_id": "s01-anchor",
                    "role": "anchor",
                    "card_type": "text",
                    "card_style": "accent",
                    "headline": f"{page_type} smoke",
                    "body": ["最小非 content 页冒烟样例"],
                    "content_budget": {"headline_max_chars": 12, "body_max_bullets": 1, "body_max_lines": 2},
                    "image": {
                        "mode": "decorate",
                        "needed": False,
                        "usage": None,
                        "placement": None,
                        "content_description": None,
                        "source_hint": None,
                        "decorate_brief": "只做轻量占位，不引入外部图片。",
                    },
                }
            ],
            "workflow_metadata": {
                "stage": "planning",
                "workflow_version": WORKFLOW_VERSION,
                "planning_schema_version": PLANNING_SCHEMA_VERSION,
                "planning_packet_version": PLANNING_PACKET_VERSION,
                "planning_continuity_version": PLANNING_CONTINUITY_VERSION,
            },
        }
    }


def build_fixture_tree(tmp_dir: Path) -> dict[str, Path]:
    fixtures = {
        "interview": tmp_dir / "interview-qa.txt",
        "requirements": tmp_dir / "requirements-interview.txt",
        "outline": tmp_dir / "outline.txt",
        "brief": tmp_dir / "search-brief.txt",
        "style": tmp_dir / "style.json",
        "planning": tmp_dir / "planning/planning3.json",
        "slide": tmp_dir / "slides/slide-3.html",
        "png": tmp_dir / "png/slide-3.png",
        "images": tmp_dir / "images",
        "runtime": tmp_dir / "runtime",
        "image_inventory": tmp_dir / "runtime/page-images-3.md",
        "audit_request": tmp_dir / "runtime/page-audit-request-3.txt",
        "prompt_interview_structured": tmp_dir / "runtime/prompt-interview-structured.md",
        "prompt_interview_text": tmp_dir / "runtime/prompt-interview-text.md",
        "prompt_style_phase1": tmp_dir / "runtime/prompt-style-phase1.md",
        "page_agent_log": tmp_dir / "runtime/page-agent-3.log",
        "page_patch_log": tmp_dir / "runtime/page-patch-agent-3.log",
        "planning_copy": tmp_dir / "runtime/page-planning-output-3.json",
        "planning_validator_report": tmp_dir / "runtime/page-planning-validator-3.json",
        "resource_menu": tmp_dir / "runtime/page-planning-menu-3.md",
        "prompt_planning": tmp_dir / "runtime/prompt-page-planning-3.md",
        "html_resolve": tmp_dir / "runtime/page-html-resolve-3.md",
        "html_copy": tmp_dir / "runtime/page-html-output-3.html",
        "prompt_html": tmp_dir / "runtime/prompt-page-html-3.md",
        "review_png_copy": tmp_dir / "runtime/page-review-output-3.png",
        "visual_qa_report": tmp_dir / "runtime/page-review-qa-3.txt",
        "prompt_review": tmp_dir / "runtime/prompt-page-review-3.md",
        "prompt_orchestrator": tmp_dir / "runtime/prompt-page-orchestrator-3.md",
        "prompt_audit_request": tmp_dir / "runtime/prompt-page-audit-request-3.md",
        "prompt_breakpoint": tmp_dir / "runtime/prompt-page-breakpoint-3.md",
    }

    write_text(
        fixtures["interview"],
        "# 采访纪要\n\n用户要做一份 4 页的 Linux.do 社区介绍，目标是让新用户快速理解定位并愿意加入。\n\nscenario: 社区介绍\n"
        "audience: 新用户与潜在参与者\ntarget_action: 建立认知并愿意加入\nexpected_pages: 4\npage_density: 适中\n"
        "style: 极简商务\nbrand: 保持社区感与克制气质\nmust_include: 社区定位、氛围、价值、加入理由\n"
        "must_avoid: 不要写成广告页\nlanguage: 中文\nimagery: decorate\nmaterial_strategy: research\n"
        "subagent_model_strategy: 继承主代理\nsubagent_thinking_effort: 中等\nmanual_audit_mode: fine_grained\n"
        "manual_audit_scope: page_html, page_review\nmanual_audit_assets: runtime_and_selected_assets\n",
    )
    write_text(
        fixtures["requirements"],
        "# 需求归一化\n\nscenario: 社区介绍\naudience: 新用户与潜在参与者\ntarget_action: 建立认知并愿意加入\n"
        "expected_pages: 4\npage_density: 适中\nstyle: 极简商务\nbrand: 保持社区感与克制气质\n"
        "must_include: 社区定位、氛围、价值、加入理由\nmust_avoid: 不要写成广告页\nlanguage: 中文\n"
        "imagery: decorate\nmaterial_strategy: research\nsubagent_model_strategy: 继承主代理\n"
        "subagent_thinking_effort: 中等\nmanual_audit_mode: fine_grained\nmanual_audit_scope: page_html, page_review\n"
        "manual_audit_assets: runtime_and_selected_assets\ndensity_bias: balanced\nbranch: research\n",
    )
    write_text(fixtures["outline"], build_outline_fixture("balanced"))
    write_text(fixtures["brief"], "# Research Brief\n\n## 核心发现\n1. 示例发现 [来源: smoke]\n")
    write_text(
        fixtures["style"],
        json.dumps(
            {
                "style_id": "smoke",
                "style_name": "Smoke",
                "mood_keywords": ["clear", "structured", "modern"],
                "design_soul": "清晰、克制、强调论点主次。",
                "variation_strategy": "统一色彩与边角，允许每页在布局重心和装饰位置上变化。",
                "decoration_dna": {
                    "signature_move": "轻微几何线条",
                    "forbidden": ["过强噪点"],
                    "recommended_combos": ["outline + accent"],
                },
                "font_family": "Noto Sans SC",
                "css_variables": {
                    "bg_primary": "#0f172a",
                    "bg_secondary": "#111827",
                    "card_bg_from": "#1f2937",
                    "card_bg_to": "#111827",
                    "card_border": "#334155",
                    "card_radius": "24px",
                    "text_primary": "#f8fafc",
                    "text_secondary": "#cbd5e1",
                    "accent_1": "#38bdf8",
                    "accent_2": "#22c55e",
                    "accent_3": "#f59e0b",
                    "accent_4": "#a78bfa",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    fixtures["images"].mkdir(parents=True, exist_ok=True)
    write_text(
        fixtures["images"] / "smoke-image.svg",
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"400\" height=\"240\"><rect width=\"400\" height=\"240\" fill=\"#0f172a\"/><circle cx=\"140\" cy=\"120\" r=\"52\" fill=\"#38bdf8\" opacity=\"0.7\"/><text x=\"210\" y=\"130\" fill=\"#f8fafc\" font-size=\"36\">smoke</text></svg>",
    )
    content_fixture = build_content_page_fixture()
    write_text(fixtures["planning"], json.dumps(content_fixture, ensure_ascii=False, indent=2))
    write_text(fixtures["slide"], build_html_fixture(content_fixture, decoration_count=2))
    write_smoke_png(fixtures["png"])
    write_text(fixtures["review_png_copy"], "placeholder png mirror")
    write_text(fixtures["visual_qa_report"], "placeholder qa report")
    return fixtures


def run_smoke() -> SmokeResult:
    result = SmokeResult()
    with tempfile.TemporaryDirectory(prefix="ppt-skill-smoke-") as tmp:
        tmp_dir = Path(tmp)
        fx = build_fixture_tree(tmp_dir)
        py = sys.executable

        interview_contract = run_cmd(
            "contract-validator-interview",
            [
                py,
                str(SCRIPTS_DIR / "contract_validator.py"),
                "interview",
                str(fx["interview"]),
            ],
            result,
        )
        if interview_contract.returncode == 0:
            assert_contains("contract-validator-interview", interview_contract.stdout, ["OK"], result)

        requirements_contract = run_cmd(
            "contract-validator-requirements",
            [
                py,
                str(SCRIPTS_DIR / "contract_validator.py"),
                "requirements-interview",
                str(fx["requirements"]),
            ],
            result,
        )
        if requirements_contract.returncode == 0:
            assert_contains("contract-validator-requirements", requirements_contract.stdout, ["OK"], result)

        outline_contract = run_cmd(
            "contract-validator-outline",
            [
                py,
                str(SCRIPTS_DIR / "contract_validator.py"),
                "outline",
                str(fx["outline"]),
            ],
            result,
        )
        if outline_contract.returncode == 0:
            assert_contains("contract-validator-outline", outline_contract.stdout, ["OK"], result)

        for bias in ("relaxed", "ultra_dense"):
            outline_path = tmp_dir / f"outline-{bias}.txt"
            write_text(outline_path, build_outline_fixture(bias))
            outline_variant = run_cmd(
                f"contract-validator-outline-{bias}",
                [
                    py,
                    str(SCRIPTS_DIR / "contract_validator.py"),
                    "outline",
                    str(outline_path),
                ],
                result,
            )
            if outline_variant.returncode == 0:
                assert_contains(f"contract-validator-outline-{bias}", outline_variant.stdout, ["OK"], result)

        validator = run_cmd(
            "planning-validator",
            [
                py,
                str(SCRIPTS_DIR / "planning_validator.py"),
                str(fx["planning"].parent),
                "--refs",
                str(REFERENCES_DIR),
                "--page",
                "3",
                "--report",
                str(fx["planning_validator_report"]),
            ],
            result,
        )
        if validator.returncode == 0:
            assert_contains("planning-validator", validator.stdout, ["OK"], result)
            assert_contains(
                "planning-validator-report",
                fx["planning_validator_report"].read_text(encoding="utf-8"),
                ['"ok": true', '"total_pages": 1'],
                result,
            )

        density_cases = [
            ("planning-validator-low", 1, "relaxed", "low"),
            ("planning-validator-mid-low", 2, "balanced", "mid_low"),
            ("planning-validator-high", 4, "ultra_dense", "high"),
        ]
        for label, slide_no, deck_bias, density_label in density_cases:
            planning_dir = tmp_dir / f"{label}-dir"
            planning_path = planning_dir / f"planning{slide_no}.json"
            write_text(
                planning_path,
                json.dumps(
                    build_content_page_fixture(slide_number=slide_no, deck_bias=deck_bias, density_label=density_label),
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            density_validate = run_cmd(
                label,
                [
                    py,
                    str(SCRIPTS_DIR / "planning_validator.py"),
                    str(planning_dir),
                    "--refs",
                    str(REFERENCES_DIR),
                    "--page",
                    str(slide_no),
                ],
                result,
            )
            if density_validate.returncode == 0:
                assert_contains(label, density_validate.stdout, ["OK"], result)

        dashboard_dir = tmp_dir / "planning-validator-dashboard-dir"
        dashboard_sequence = {
            4: build_content_page_fixture(slide_number=4, deck_bias="ultra_dense", density_label="medium"),
            5: build_content_page_fixture(slide_number=5, deck_bias="ultra_dense", density_label="dashboard"),
            6: build_content_page_fixture(slide_number=6, deck_bias="ultra_dense", density_label="medium"),
        }
        for slide_no, payload in dashboard_sequence.items():
            write_text(
                dashboard_dir / f"planning{slide_no}.json",
                json.dumps(payload, ensure_ascii=False, indent=2),
            )
        dashboard_validate = run_cmd(
            "planning-validator-dashboard",
            [
                py,
                str(SCRIPTS_DIR / "planning_validator.py"),
                str(dashboard_dir),
                "--refs",
                str(REFERENCES_DIR),
            ],
            result,
        )
        if dashboard_validate.returncode == 0:
            assert_contains("planning-validator-dashboard", dashboard_validate.stdout, ["OK"], result)

        visual_qa = run_cmd_allow_codes(
            "visual-qa-pass",
            [
                py,
                str(SCRIPTS_DIR / "visual_qa.py"),
                str(fx["png"]),
                "--planning",
                str(fx["planning"]),
                "--html",
                str(fx["slide"]),
                "--output",
                str(fx["visual_qa_report"]),
            ],
            result,
            allowed_codes={0, 2},
        )
        if visual_qa.returncode in {0, 2}:
            report_text = fx["visual_qa_report"].read_text(encoding="utf-8")
            assert_contains("visual-qa-pass", report_text, ["HTML-07", "HTML-08", "DENS-01", "HTML-03", "FAIL=0"], result)

        multi_anchor_dir = tmp_dir / "planning-multi-anchor"
        multi_anchor_path = multi_anchor_dir / "planning6.json"
        multi_anchor_fixture = build_content_page_fixture(slide_number=6, deck_bias="balanced", density_label="medium")
        multi_anchor_fixture["page"]["cards"][1]["role"] = "anchor"
        write_text(multi_anchor_path, json.dumps(multi_anchor_fixture, ensure_ascii=False, indent=2))
        run_cmd_expect_failure(
            "planning-validator-multi-anchor-fail",
            [
                py,
                str(SCRIPTS_DIR / "planning_validator.py"),
                str(multi_anchor_dir),
                "--refs",
                str(REFERENCES_DIR),
                "--page",
                "6",
            ],
            result,
            expected_tokens=["multiple anchor cards"],
        )

        high_dir = tmp_dir / "planning-high-decor"
        high_path = high_dir / "planning7.json"
        high_fixture = build_content_page_fixture(slide_number=7, deck_bias="ultra_dense", density_label="high")
        high_html = tmp_dir / "slides/slide-7.html"
        write_text(high_path, json.dumps(high_fixture, ensure_ascii=False, indent=2))
        write_text(high_html, build_html_fixture(high_fixture, decoration_count=3))
        run_cmd_expect_failure(
            "visual-qa-decoration-budget-fail",
            [
                py,
                str(SCRIPTS_DIR / "visual_qa.py"),
                str(fx["png"]),
                "--planning",
                str(high_path),
                "--html",
                str(high_html),
            ],
            result,
            expected_tokens=["HTML-07"],
        )

        dashboard_html_dir = tmp_dir / "planning-dashboard-bad-html"
        dashboard_path = dashboard_html_dir / "planning8.json"
        dashboard_fixture = build_content_page_fixture(slide_number=8, deck_bias="ultra_dense", density_label="dashboard")
        dashboard_html = tmp_dir / "slides/slide-8.html"
        write_text(dashboard_path, json.dumps(dashboard_fixture, ensure_ascii=False, indent=2))
        write_text(dashboard_html, build_html_fixture(dashboard_fixture, decoration_count=1, include_img=True))
        run_cmd_expect_failure(
            "visual-qa-dashboard-image-fail",
            [
                py,
                str(SCRIPTS_DIR / "visual_qa.py"),
                str(fx["png"]),
                "--planning",
                str(dashboard_path),
                "--html",
                str(dashboard_html),
            ],
            result,
            expected_tokens=["HTML-04"],
        )

        small_font_html = tmp_dir / "slides/slide-9.html"
        write_text(small_font_html, build_html_fixture(build_content_page_fixture(), decoration_count=2, font_px=10))
        run_cmd_expect_failure(
            "visual-qa-small-font-fail",
            [
                py,
                str(SCRIPTS_DIR / "visual_qa.py"),
                str(fx["png"]),
                "--planning",
                str(fx["planning"]),
                "--html",
                str(small_font_html),
            ],
            result,
            expected_tokens=["HTML-06"],
        )

        menu = run_cmd(
            "resource-loader-menu",
            [py, str(SCRIPTS_DIR / "resource_loader.py"), "menu", "--refs-dir", str(REFERENCES_DIR)],
            result,
        )
        if menu.returncode == 0:
            assert_contains("resource-loader-menu", menu.stdout, ["### layouts/", "#### hero-top", "### blocks/"], result)

        images_snapshot = run_cmd(
            "resource-loader-images-snapshot",
            [
                py,
                str(SCRIPTS_DIR / "resource_loader.py"),
                "images",
                "--images-dir",
                str(fx["images"]),
                "--output",
                str(fx["image_inventory"]),
            ],
            result,
        )
        if images_snapshot.returncode == 0:
            assert_contains(
                "resource-loader-images-snapshot",
                fx["image_inventory"].read_text(encoding="utf-8"),
                ["smoke-image.svg"],
                result,
            )

        menu_snapshot = run_cmd(
            "resource-loader-menu-snapshot",
            [
                py,
                str(SCRIPTS_DIR / "resource_loader.py"),
                "menu",
                "--refs-dir",
                str(REFERENCES_DIR),
                "--output",
                str(fx["resource_menu"]),
            ],
            result,
        )
        if menu_snapshot.returncode == 0:
            snapshot_text = fx["resource_menu"].read_text(encoding="utf-8")
            assert_contains(
                "resource-loader-menu-snapshot",
                snapshot_text,
                ["### layouts/", "#### hero-top", "### blocks/"],
                result,
            )

        resolve = run_cmd(
            "resource-loader-resolve",
            [
                py,
                str(SCRIPTS_DIR / "resource_loader.py"),
                "resolve",
                "--refs-dir",
                str(REFERENCES_DIR),
                "--planning",
                str(fx["planning"]),
            ],
            result,
        )
        if resolve.returncode == 0:
            assert_contains(
                "resource-loader-resolve",
                resolve.stdout,
                [
                    "# 顶部英雄式版式",
                    "# KPI 指标卡（数字+趋势箭头+标签）",
                    "# 指标行（数字+标签+进度条 组合）",
                    "# 视觉层级与 CRAP 原则",
                    "# 构图与留白",
                    "# Director Command Runtime Rules",
                ],
                result,
            )
            assert_no_unfilled_vars("resource-loader-resolve", resolve.stdout, result)

        resolve_snapshot = run_cmd(
            "resource-loader-resolve-snapshot",
            [
                py,
                str(SCRIPTS_DIR / "resource_loader.py"),
                "resolve",
                "--refs-dir",
                str(REFERENCES_DIR),
                "--planning",
                str(fx["planning"]),
                "--output",
                str(fx["html_resolve"]),
            ],
            result,
        )
        if resolve_snapshot.returncode == 0:
            assert_contains(
                "resource-loader-resolve-snapshot",
                fx["html_resolve"].read_text(encoding="utf-8"),
                ["# 顶部英雄式版式", "# KPI 指标卡（数字+趋势箭头+标签）"],
                result,
            )

        images = run_cmd(
            "resource-loader-images",
            [
                py,
                str(SCRIPTS_DIR / "resource_loader.py"),
                "images",
                "--images-dir",
                str(fx["images"]),
            ],
            result,
        )
        if images.returncode == 0:
            assert_contains("resource-loader-images", images.stdout, ["count: 1", "smoke-image.svg"], result)

        subagent_logger = run_cmd(
            "subagent-logger-run",
            [
                py,
                str(SCRIPTS_DIR / "subagent_logger.py"),
                "run",
                "--log",
                str(fx["page_agent_log"]),
                "--label",
                "resource-loader-images",
                "--",
                py,
                str(SCRIPTS_DIR / "resource_loader.py"),
                "images",
                "--images-dir",
                str(fx["images"]),
            ],
            result,
        )
        if subagent_logger.returncode == 0:
            logger_text = fx["page_agent_log"].read_text(encoding="utf-8")
            assert_contains(
                "subagent-logger-run",
                logger_text,
                [
                    "label: resource-loader-images",
                    "cmd:",
                    "stdout:",
                    "count: 1",
                    "smoke-image.svg",
                ],
                result,
            )

        for page_type, expected_title in PAGE_TEMPLATE_EXPECTATIONS.items():
            planning_dir = tmp_dir / f"planning-{page_type}"
            planning_path = planning_dir / "planning1.json"
            write_text(planning_path, json.dumps(build_non_content_page(page_type), ensure_ascii=False, indent=2))
            non_content_validate = run_cmd(
                f"planning-validator-{page_type}",
                [
                    py,
                    str(SCRIPTS_DIR / "planning_validator.py"),
                    str(planning_dir),
                    "--refs",
                    str(REFERENCES_DIR),
                    "--page",
                    "1",
                ],
                result,
            )
            if non_content_validate.returncode == 0:
                assert_contains(f"planning-validator-{page_type}", non_content_validate.stdout, ["OK"], result)

            non_content_resolve = run_cmd(
                f"resource-loader-resolve-{page_type}",
                [
                    py,
                    str(SCRIPTS_DIR / "resource_loader.py"),
                    "resolve",
                    "--refs-dir",
                    str(REFERENCES_DIR),
                    "--planning",
                    str(planning_path),
                ],
                result,
            )
            if non_content_resolve.returncode == 0:
                assert_contains(f"resource-loader-resolve-{page_type}", non_content_resolve.stdout, [expected_title], result)
                assert_no_unfilled_vars(f"resource-loader-resolve-{page_type}", non_content_resolve.stdout, result)

        prompt_specs = [
            (
                "prompt-interview-structured",
                fx["prompt_interview_structured"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/tpl-interview-structured-ui.md"),
                    "--var",
                    "TOPIC=Linux.do 社区介绍",
                    "--var",
                    "USER_CONTEXT=4 页介绍型 PPT，目标是快速讲清社区定位、氛围、价值与加入理由。",
                    "--inject-file",
                    f"INTERVIEW_MODE_MODULE={REFERENCES_DIR / 'prompts/module-structured-interview-ui.md'}",
                    "--inject-file",
                    f"INTERVIEW_CORE={REFERENCES_DIR / 'prompts/tpl-interview.md'}",
                    "--output",
                    str(fx["prompt_interview_structured"]),
                ],
            ),
            (
                "prompt-interview-text",
                fx["prompt_interview_text"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/tpl-interview-text-fallback.md"),
                    "--var",
                    "TOPIC=Linux.do 社区介绍",
                    "--var",
                    "USER_CONTEXT=4 页介绍型 PPT，目标是快速讲清社区定位、氛围、价值与加入理由。",
                    "--inject-file",
                    f"INTERVIEW_MODE_MODULE={REFERENCES_DIR / 'prompts/module-text-interview-fallback.md'}",
                    "--inject-file",
                    f"INTERVIEW_CORE={REFERENCES_DIR / 'prompts/tpl-interview.md'}",
                    "--output",
                    str(fx["prompt_interview_text"]),
                ],
            ),
            (
                "prompt-style-phase1",
                fx["prompt_style_phase1"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/tpl-style-phase1.md"),
                    "--var",
                    f"REQUIREMENTS_PATH={fx['requirements']}",
                    "--var",
                    f"OUTLINE_PATH={fx['outline']}",
                    "--var",
                    f"SKILL_DIR={ROOT_DIR}",
                    "--var",
                    f"STYLE_OUTPUT={fx['style']}",
                    "--inject-file",
                    f"STYLE_RUNTIME_RULES={REFERENCES_DIR / 'styles/runtime-style-rules.md'}",
                    "--inject-file",
                    f"STYLE_PRESET_INDEX={REFERENCES_DIR / 'styles/runtime-style-palette-index.md'}",
                    "--inject-file",
                    f"PLAYBOOK={REFERENCES_DIR / 'playbooks/style-phase1-playbook.md'}",
                    "--output",
                    str(fx["prompt_style_phase1"]),
                ],
            ),
            (
                "prompt-page-planning",
                fx["prompt_planning"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/step4/tpl-page-planning.md"),
                    "--var",
                    "PAGE_NUM=3",
                    "--var",
                    "TOTAL_PAGES=8",
                    "--var",
                    f"REQUIREMENTS_PATH={fx['requirements']}",
                    "--var",
                    f"OUTLINE_PATH={fx['outline']}",
                    "--var",
                    f"BRIEF_PATH={fx['brief']}",
                    "--var",
                    f"STYLE_PATH={fx['style']}",
                    "--var",
                    f"IMAGES_DIR={fx['images']}",
                    "--var",
                    f"IMAGE_INVENTORY_PATH={fx['image_inventory']}",
                    "--var",
                    f"RESOURCE_MENU_PATH={fx['resource_menu']}",
                    "--var",
                    f"PLANNING_RUNTIME_COPY_PATH={fx['planning_copy']}",
                    "--var",
                    f"PLANNING_VALIDATOR_REPORT_PATH={fx['planning_validator_report']}",
                    "--var",
                    f"PLANNING_OUTPUT={fx['planning']}",
                    "--var",
                    f"SUBAGENT_LOG_PATH={fx['page_agent_log']}",
                    "--var",
                    "SUBAGENT_NAME=PageAgent-3",
                    "--var",
                    f"SKILL_DIR={ROOT_DIR}",
                    "--var",
                    f"REFS_DIR={REFERENCES_DIR}",
                    "--inject-file",
                    f"PRINCIPLES_CHEATSHEET={REFERENCES_DIR / 'principles/design-principles-cheatsheet.md'}",
                    "--inject-file",
                    f"PLAYBOOK={REFERENCES_DIR / 'playbooks/step4/page-planning-playbook.md'}",
                    "--output",
                    str(fx["prompt_planning"]),
                ],
            ),
            (
                "prompt-page-html",
                fx["prompt_html"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/step4/tpl-page-html.md"),
                    "--var",
                    "PAGE_NUM=3",
                    "--var",
                    "TOTAL_PAGES=8",
                    "--var",
                    f"PLANNING_OUTPUT={fx['planning']}",
                    "--var",
                    f"SLIDE_OUTPUT={fx['slide']}",
                    "--var",
                    f"IMAGES_DIR={fx['images']}",
                    "--var",
                    f"IMAGE_INVENTORY_PATH={fx['image_inventory']}",
                    "--var",
                    f"HTML_RESOLVE_PATH={fx['html_resolve']}",
                    "--var",
                    f"HTML_RUNTIME_COPY_PATH={fx['html_copy']}",
                    "--var",
                    f"STYLE_PATH={fx['style']}",
                    "--var",
                    f"SUBAGENT_LOG_PATH={fx['page_agent_log']}",
                    "--var",
                    "SUBAGENT_NAME=PageAgent-3",
                    "--var",
                    f"SKILL_DIR={ROOT_DIR}",
                    "--var",
                    f"REFS_DIR={REFERENCES_DIR}",
                    "--inject-file",
                    f"PLAYBOOK={REFERENCES_DIR / 'playbooks/step4/page-html-playbook.md'}",
                    "--output",
                    str(fx["prompt_html"]),
                ],
            ),
            (
                "prompt-page-review",
                fx["prompt_review"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/step4/tpl-page-review.md"),
                    "--var",
                    "PAGE_NUM=3",
                    "--var",
                    "TOTAL_PAGES=8",
                    "--var",
                    f"PLANNING_OUTPUT={fx['planning']}",
                    "--var",
                    f"SLIDE_OUTPUT={fx['slide']}",
                    "--var",
                    f"PNG_OUTPUT={fx['png']}",
                    "--var",
                    f"REVIEW_RUNTIME_PNG_PATH={fx['review_png_copy']}",
                    "--var",
                    f"VISUAL_QA_REPORT_PATH={fx['visual_qa_report']}",
                    "--var",
                    f"STYLE_PATH={fx['style']}",
                    "--var",
                    f"SUBAGENT_LOG_PATH={fx['page_agent_log']}",
                    "--var",
                    "SUBAGENT_NAME=PageAgent-3",
                    "--var",
                    f"SKILL_DIR={ROOT_DIR}",
                    "--var",
                    f"REVIEW_DIR={tmp_dir / 'review'}",
                    "--inject-file",
                    f"PLAYBOOK={REFERENCES_DIR / 'playbooks/step4/page-review-playbook.md'}",
                    "--inject-file",
                    f"FAILURE_MODES={REFERENCES_DIR / 'principles/runtime-failure-modes.md'}",
                    "--inject-file",
                    f"PRINCIPLES_CHEATSHEET={REFERENCES_DIR / 'principles/design-principles-cheatsheet.md'}",
                    "--output",
                    str(fx["prompt_review"]),
                ],
            ),
            (
                "prompt-page-audit-request",
                fx["prompt_audit_request"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/step4/tpl-page-audit-request.md"),
                    "--var",
                    "PAGE_NUM=3",
                    "--var",
                    "START_STAGE=html",
                    "--var",
                    "END_STAGE=review",
                    "--var",
                    "USER_AUDIT_REQUEST=把主标题收敛一点，并重点检查右侧图卡和指标层级",
                    "--var",
                    "TARGET_ASSET_PATH=none",
                    "--var",
                    f"RUNTIME_CONTEXT_PATHS={fx['prompt_html']}; {fx['prompt_review']}; {fx['html_resolve']}; {fx['image_inventory']}",
                    "--var",
                    f"PLANNING_OUTPUT={fx['planning']}",
                    "--var",
                    f"SLIDE_OUTPUT={fx['slide']}",
                    "--var",
                    f"PNG_OUTPUT={fx['png']}",
                    "--output",
                    str(fx["prompt_audit_request"]),
                ],
            ),
            (
                "prompt-page-orchestrator",
                fx["prompt_orchestrator"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/step4/tpl-page-orchestrator.md"),
                    "--var",
                    "PAGE_NUM=3",
                    "--var",
                    "TOTAL_PAGES=8",
                    "--var",
                    f"PLANNING_PROMPT_PATH={fx['prompt_planning']}",
                    "--var",
                    f"HTML_PROMPT_PATH={fx['prompt_html']}",
                    "--var",
                    f"REVIEW_PROMPT_PATH={fx['prompt_review']}",
                    "--var",
                    f"PLANNING_OUTPUT={fx['planning']}",
                    "--var",
                    f"SLIDE_OUTPUT={fx['slide']}",
                    "--var",
                    f"PNG_OUTPUT={fx['png']}",
                    "--var",
                    f"SUBAGENT_LOG_PATH={fx['page_agent_log']}",
                    "--var",
                    "SUBAGENT_NAME=PageAgent-3",
                    "--var",
                    f"SKILL_DIR={ROOT_DIR}",
                    "--output",
                    str(fx["prompt_orchestrator"]),
                ],
            ),
            (
                "prompt-page-breakpoint",
                fx["prompt_breakpoint"],
                [
                    py,
                    str(SCRIPTS_DIR / "prompt_harness.py"),
                    "--template",
                    str(REFERENCES_DIR / "prompts/step4/tpl-page-breakpoint-orchestrator.md"),
                    "--var",
                    "PAGE_NUM=3",
                    "--var",
                    "TOTAL_PAGES=8",
                    "--var",
                    f"AUDIT_REQUEST_PATH={fx['audit_request']}",
                    "--var",
                    "START_STAGE=html",
                    "--var",
                    "END_STAGE=review",
                    "--var",
                    f"PLANNING_PROMPT_PATH={fx['prompt_planning']}",
                    "--var",
                    f"HTML_PROMPT_PATH={fx['prompt_html']}",
                    "--var",
                    f"REVIEW_PROMPT_PATH={fx['prompt_review']}",
                    "--var",
                    f"PLANNING_OUTPUT={fx['planning']}",
                    "--var",
                    f"SLIDE_OUTPUT={fx['slide']}",
                    "--var",
                    f"PNG_OUTPUT={fx['png']}",
                    "--var",
                    f"SUBAGENT_LOG_PATH={fx['page_patch_log']}",
                    "--var",
                    "SUBAGENT_NAME=PagePatchAgent-3",
                    "--var",
                    f"SKILL_DIR={ROOT_DIR}",
                    "--var",
                    "TARGET_ASSET_PATH=none",
                    "--var",
                    "RUNTIME_CONTEXT_PATHS=none",
                    "--var",
                    "USER_AUDIT_REQUEST=把主标题收敛一点，并重点检查右侧图卡和指标层级",
                    "--output",
                    str(fx["prompt_breakpoint"]),
                ],
            ),
        ]

        for label, output_path, args in prompt_specs:
            proc = run_cmd(label, args, result)
            if proc.returncode == 0:
                rendered = output_path.read_text(encoding="utf-8")
                assert_no_unfilled_vars(label, rendered, result)
                if label == "prompt-interview-structured":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# 采访问卷（Structured UI）",
                            "主题：Linux.do 社区介绍",
                            "用户背景：4 页介绍型 PPT",
                            "当前环境已确认支持原生结构化采访 UI",
                            "# 采访问卷共享核心",
                            "## 最终要求",
                        ],
                        result,
                    )
                    assert_max_bytes(label, rendered, 9000, result)
                if label == "prompt-interview-text":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# 采访问卷（Text Fallback）",
                            "结构化文本采访单",
                            "## 当前执行模式",
                            "# 采访问卷共享核心",
                            "## 最终要求",
                        ],
                        result,
                    )
                    assert_max_bytes(label, rendered, 11500, result)
                if label == "prompt-style-phase1":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# Runtime Style Rules",
                            "# Runtime Style Palette Index",
                            "# Style Phase 1 Playbook -- 风格合同的定义与输出",
                        ],
                        result,
                    )
                if label == "prompt-page-planning":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# Page Planning Playbook -- 单页策划稿",
                            "# 设计原则速查表 -- Step 4 字段级操作手册",
                            str(fx["image_inventory"]),
                            str(fx["resource_menu"]),
                            "主链已生成的**组件/图表菜单快照**",
                            str(fx["planning_copy"]),
                            str(fx["planning_validator_report"]),
                            str(fx["page_agent_log"]),
                            "scripts/subagent_logger.py run --log",
                        ],
                        result,
                    )
                if label == "prompt-page-html":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# Page HTML Playbook -- 单页 HTML 设计稿",
                            str(fx["html_resolve"]),
                            str(fx["html_copy"]),
                            "data-decoration-layer",
                            'aria-hidden="true"',
                            str(fx["page_agent_log"]),
                            "scripts/subagent_logger.py run --log",
                        ],
                        result,
                    )
                if label == "prompt-page-review":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# Page Visual Review & Fix Playbook -- 单页图审与 HTML 修复",
                            "# Runtime Failure Modes",
                            str(fx["review_png_copy"]),
                            str(fx["visual_qa_report"]),
                            "--html",
                            str(fx["page_agent_log"]),
                            "scripts/subagent_logger.py run --log",
                        ],
                        result,
                    )
                if label == "prompt-page-orchestrator":
                    assert_contains(
                        label,
                        rendered,
                        [
                            str(fx["page_agent_log"]),
                            "scripts/subagent_logger.py note --log",
                            "阶段 1：Planning",
                            "阶段 2：HTML",
                            "阶段 3：Review",
                        ],
                        result,
                    )
                if label == "prompt-page-audit-request":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# Step 4 人工审计返工请求",
                            "start_stage: html",
                            "end_stage: review",
                            "user_request: 把主标题收敛一点，并重点检查右侧图卡和指标层级",
                            str(fx["html_resolve"]),
                        ],
                        result,
                    )
                    write_text(fx["audit_request"], rendered)
                if label == "prompt-page-breakpoint":
                    assert_contains(
                        label,
                        rendered,
                        [
                            "# PagePatchAgent-3 断点返工调度指令",
                            f"先读取：`{fx['audit_request']}`",
                            str(fx["page_patch_log"]),
                            "scripts/subagent_logger.py note --log",
                        ],
                        result,
                    )

        audit_request_contract = run_cmd(
            "contract-validator-page-audit-request",
            [
                py,
                str(SCRIPTS_DIR / "contract_validator.py"),
                "page-audit-request",
                str(fx["audit_request"]),
                "--base-dir",
                str(tmp_dir),
            ],
            result,
        )
        if audit_request_contract.returncode == 0:
            assert_contains("contract-validator-page-audit-request", audit_request_contract.stdout, ["OK"], result)

    return result


def print_messages(title: str, messages: list[str]) -> None:
    if not messages:
        return
    print(title)
    for item in messages:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal end-to-end smoke test for the PPT skill")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="treat warnings as failures",
    )
    args = parser.parse_args()

    result = run_smoke()
    print("PPT skill smoke test")
    print(f"errors: {len(result.errors)}")
    print(f"warnings: {len(result.warnings)}")
    print_messages("Steps", result.steps)
    print_messages("Errors", result.errors)
    print_messages("Warnings", result.warnings)

    if result.errors:
        return 1
    if args.strict_warnings and result.warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
