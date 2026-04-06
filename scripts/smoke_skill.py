#!/usr/bin/env python3
"""Minimal end-to-end smoke test for the PPT workflow skill.

This script intentionally stays within the current markdown/code architecture.
It exercises the most failure-prone integration points:
1. Step 0 interview prompt rendering (structured/text dual templates)
2. Step 4 planning example -> planning_validator.py
3. resource_loader.py menu / resolve / images
4. prompt_harness.py for the Step 4 prompt chain
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from workflow_versions import (  # noqa: E402
    PLANNING_CONTINUITY_VERSION,
    PLANNING_PACKET_VERSION,
    PLANNING_SCHEMA_VERSION,
    WORKFLOW_VERSION,
)


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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_content_page_fixture() -> dict[str, object]:
    """Build a minimal content page planning fixture for smoke testing."""
    return {
        "page": {
            "slide_number": 3,
            "page_type": "content",
            "narrative_role": "evidence",
            "title": "增长判断",
            "page_goal": "证明增长成立",
            "audience_takeaway": "增长数据可信",
            "visual_weight": 7,
            "layout_hint": "hero-top",
            "layout_variation_note": "与上一页重心不同",
            "focus_zone": "右上 1/3 作为视觉锚点",
            "negative_space_target": "medium",
            "page_text_strategy": "标题强、正文短、数据做锚点",
            "rhythm_action": "推进",
            "must_avoid": ["禁止平均分栏"],
            "variation_guardrails": {
                "same_gene_as_deck": "保留统一字体和 signature_move",
                "different_from_previous": ["重心从上移到右"],
            },
            "director_command": {
                "mood": "判断感强、结论先行",
                "spatial_strategy": "主锚占据第一视线",
                "anchor_treatment": "用尺度断层强化主锚",
                "techniques": ["T1", "W3"],
                "prose": "保持证据链清晰",
            },
            "decoration_hints": {
                "background": {"feel": "轻微渐变底", "restraint": "不抢文字对比", "techniques": ["T1"]},
                "floating": {"feel": "局部辅助装饰", "restraint": "只服务锚点动线", "techniques": ["W3"]},
                "page_accent": {"feel": "强调色集中在锚点附近", "restraint": "accent 只用 1-2 种", "techniques": ["T9"]},
            },
            "source_guidance": {
                "brief_sections": ["核心发现"],
                "citation_expectation": "有数字就保留来源",
                "strictness": "不得超出 brief 结论边界",
            },
            "resources": {
                "page_template": None,
                "layout_refs": ["hero-top"],
                "block_refs": [],
                "chart_refs": ["kpi", "metric-row"],
                "principle_refs": ["visual-hierarchy", "composition"],
                "resource_rationale": "用 hero-top 放大单一结论",
            },
            "cards": [
                {
                    "card_id": "s03-anchor",
                    "role": "anchor",
                    "card_type": "data_highlight",
                    "card_style": "accent",
                    "argument_role": "claim",
                    "headline": "核心指标",
                    "body": ["一句解释它为什么重要"],
                    "data_points": [
                        {"label": "同比增长", "value": "47.3", "unit": "%", "source": "search-brief metrics[2]"}
                    ],
                    "chart": {"chart_type": "kpi"},
                    "content_budget": {"headline_max_chars": 12, "body_max_bullets": 2, "body_max_lines": 4},
                    "image": {
                        "mode": "decorate",
                        "needed": False,
                        "usage": None,
                        "placement": None,
                        "content_description": None,
                        "source_hint": None,
                        "decorate_brief": "用内联 SVG 装饰填满留白",
                    },
                    "resource_ref": {"chart": "kpi", "principle": "visual-hierarchy"},
                },
                {
                    "card_id": "s03-support-1",
                    "role": "support",
                    "card_type": "data",
                    "card_style": "outline",
                    "argument_role": "evidence",
                    "headline": "增长原因",
                    "body": ["增长主要来自高客单区域放量"],
                    "data_points": [
                        {"label": "高客单区域占比", "value": "31", "unit": "%", "source": "search-brief metrics[4]"}
                    ],
                    "chart": {"chart_type": "metric_row"},
                    "content_budget": {"headline_max_chars": 12, "body_max_bullets": 2, "body_max_lines": 4},
                    "image": {
                        "mode": "decorate",
                        "needed": False,
                        "usage": None,
                        "placement": None,
                        "content_description": None,
                        "source_hint": None,
                        "decorate_brief": "用低对比度辅助线承托信息",
                    },
                    "resource_ref": {"chart": "metric-row", "principle": "composition"},
                },
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
            "visual_weight": 7,
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
        "requirements": tmp_dir / "requirements-interview.txt",
        "outline": tmp_dir / "outline.txt",
        "brief": tmp_dir / "search-brief.txt",
        "style": tmp_dir / "style.json",
        "planning": tmp_dir / "planning/planning3.json",
        "slide": tmp_dir / "slides/slide-3.html",
        "png": tmp_dir / "png/slide-3.png",
        "images": tmp_dir / "images",
        "runtime": tmp_dir / "runtime",
        "prompt_interview_structured": tmp_dir / "runtime/prompt-interview-structured.md",
        "prompt_interview_text": tmp_dir / "runtime/prompt-interview-text.md",
        "prompt_style_phase1": tmp_dir / "runtime/prompt-style-phase1.md",
        "prompt_planning": tmp_dir / "runtime/prompt-page-planning-3.md",
        "prompt_html": tmp_dir / "runtime/prompt-page-html-3.md",
        "prompt_review": tmp_dir / "runtime/prompt-page-review-3.md",
        "prompt_orchestrator": tmp_dir / "runtime/prompt-page-orchestrator-3.md",
    }

    write_text(
        fixtures["requirements"],
        "# 需求归一化\n\n## 基本信息\n- 主题：Smoke Test\n- 项目类型：演示文稿\n- 语言：中文\n- 输入类型：示例\n- 分支：research\n",
    )
    write_text(fixtures["outline"], "# 大纲\n\n## Part 1: Demo\n\n### 第 3 页：增长判断\n- 页目标：增长成立\n")
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
                    "--bg-primary": "#0f172a",
                    "--bg-secondary": "#111827",
                    "--card-bg-from": "#1f2937",
                    "--card-bg-to": "#111827",
                    "--card-border": "#334155",
                    "--card-radius": "24px",
                    "--text-primary": "#f8fafc",
                    "--text-secondary": "#cbd5e1",
                    "--accent-1": "#38bdf8",
                    "--accent-2": "#22c55e",
                    "--accent-3": "#f59e0b",
                    "--accent-4": "#a78bfa",
                    "--font-primary": "Noto Sans SC",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    fixtures["images"].mkdir(parents=True, exist_ok=True)
    write_text(fixtures["planning"], json.dumps(build_content_page_fixture(), ensure_ascii=False, indent=2))
    return fixtures


def run_smoke() -> SmokeResult:
    result = SmokeResult()
    with tempfile.TemporaryDirectory(prefix="ppt-skill-smoke-") as tmp:
        tmp_dir = Path(tmp)
        fx = build_fixture_tree(tmp_dir)
        py = sys.executable

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
            ],
            result,
        )
        if validator.returncode == 0:
            assert_contains("planning-validator", validator.stdout, ["OK"], result)

        menu = run_cmd(
            "resource-loader-menu",
            [py, str(SCRIPTS_DIR / "resource_loader.py"), "menu", "--refs-dir", str(REFERENCES_DIR)],
            result,
        )
        if menu.returncode == 0:
            assert_contains("resource-loader-menu", menu.stdout, ["### layouts/", "#### hero-top", "### blocks/"], result)

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
            assert_contains("resource-loader-images", images.stdout, ["count: 0", "(empty)"], result)

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
                    f"PLANNING_OUTPUT={fx['planning']}",
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
                    f"STYLE_PATH={fx['style']}",
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
                    f"STYLE_PATH={fx['style']}",
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
                    "--output",
                    str(fx["prompt_orchestrator"]),
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
                    assert_max_bytes(label, rendered, 9000, result)
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
                        ["# Page Planning Playbook -- 单页策划稿", "# 设计原则速查表 -- Step 4 字段级操作手册"],
                        result,
                    )
                if label == "prompt-page-html":
                    assert_contains(label, rendered, ["# Page HTML Playbook -- 单页 HTML 设计稿"], result)
                if label == "prompt-page-review":
                    assert_contains(
                        label,
                        rendered,
                        ["# Page Visual Review & Fix Playbook -- 单页图审与 HTML 修复", "# Runtime Failure Modes"],
                        result,
                    )

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
