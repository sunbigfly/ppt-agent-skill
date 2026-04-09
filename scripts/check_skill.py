#!/usr/bin/env python3
"""Consistency checks for the PPT workflow skill.

This checker keeps the current markdown-first architecture, but adds a thin
automated guardrail layer so docs and validators drift less often.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
REFERENCES_DIR = ROOT_DIR / "references"

sys.path.insert(0, str(SCRIPTS_DIR))

from planning_validator import validate_page, load_planning_pages  # noqa: E402
from prompt_harness import VAR_PATTERN  # noqa: E402


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class HarnessInvocation:
    source_path: Path
    line_no: int
    command: str
    template_path: Path
    provided_keys: set[str]


PHASE1_STAGE_COMPLETE_RULES = {
    Path("references/prompts/tpl-research-synth-phase1.md"): "--- STAGE 1 COMPLETE: {{SEARCH_OUTPUT}} ---",
    Path("references/prompts/tpl-source-synth-phase1.md"): "--- STAGE 1 COMPLETE: {{BRIEF_OUTPUT}} ---",
    Path("references/prompts/tpl-outline-phase1.md"): "--- STAGE 1 COMPLETE: {{OUTLINE_OUTPUT}} ---",
    Path("references/prompts/tpl-style-phase1.md"): "--- STAGE 1 COMPLETE: {{STYLE_OUTPUT}} ---",
}

STEP4_LEGACY_ALIASES = {
    "hero",
    "split-left",
    "split-right",
    "bento-grid",
    "columns",
    "timeline-flow",
    "steps-horizontal",
    "steps-vertical",
    "list-ranked",
    "chart-focus",
    "centered-statement",
    "feature-card",
    "info-card",
}

STEP4_DOCS = [
    ROOT_DIR / "references/prompts/step4/tpl-page-planning.md",
    ROOT_DIR / "references/prompts/step4/tpl-page-html.md",
    ROOT_DIR / "references/playbooks/step4/page-planning-playbook.md",
    ROOT_DIR / "references/playbooks/step4/page-html-playbook.md",
]

RESOURCE_ROUTE_DOC_RULES = {
    ROOT_DIR / "SKILL.md": [
        r"layout_hint→layouts/",
        r"page_type→page-templates/",
        r"card_type→blocks/",
        r"chart_type→charts/",
    ],
    ROOT_DIR / "references/README.md": [
        r"\|\s*`layout_hint`\s*\|\s*`layouts/`\s*\|",
        r"\|\s*`page_type`\s*\|\s*`page-templates/`\s*\|",
        r"\|\s*`card_type`\s*\|\s*`blocks/`\s*\|",
        r"\|\s*`chart_type`\s*\|\s*`charts/`\s*\|",
    ],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_skill_path(raw: str) -> Path:
    text = raw.strip().strip('"').strip("'")
    prefixes = ("SKILL_DIR/", "./")
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return ROOT_DIR / text


def find_prompt_harness_invocations(path: Path) -> list[HarnessInvocation]:
    lines = path.read_text(encoding="utf-8").splitlines()
    invocations: list[HarnessInvocation] = []
    i = 0
    while i < len(lines):
        if "prompt_harness.py" not in lines[i]:
            i += 1
            continue

        start = i
        parts = [lines[i].strip()]
        while parts[-1].endswith("\\") and i + 1 < len(lines):
            i += 1
            parts.append(lines[i].strip())

        command = " ".join(part.rstrip("\\").strip() for part in parts if part.strip())
        tokens = shlex.split(command)
        template_ref: str | None = None
        provided_keys: set[str] = set()
        j = 0
        while j < len(tokens):
            token = tokens[j]
            if token == "--template" and j + 1 < len(tokens):
                template_ref = tokens[j + 1]
                j += 2
                continue
            if token == "--var" and j + 1 < len(tokens):
                key, _, _ = tokens[j + 1].partition("=")
                if key:
                    provided_keys.add(key)
                j += 2
                continue
            if token == "--inject-file" and j + 1 < len(tokens):
                key, _, _ = tokens[j + 1].partition("=")
                if key:
                    provided_keys.add(key)
                j += 2
                continue
            j += 1

        if template_ref:
            invocations.append(
                HarnessInvocation(
                    source_path=path,
                    line_no=start + 1,
                    command=command,
                    template_path=normalize_skill_path(template_ref),
                    provided_keys=provided_keys,
                )
            )
        i += 1
    return invocations


def format_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def check_prompt_harness_coverage(result: CheckResult) -> None:
    cheatsheet = ROOT_DIR / "references/cli-cheatsheet.md"
    for invocation in find_prompt_harness_invocations(cheatsheet):
        if not invocation.template_path.exists():
            result.error(
                f"{format_rel(invocation.source_path)}:{invocation.line_no}: template not found: "
                f"{format_rel(invocation.template_path)}"
            )
            continue

        placeholders = set(VAR_PATTERN.findall(read_text(invocation.template_path)))
        missing = sorted(placeholders - invocation.provided_keys)
        unused = sorted(invocation.provided_keys - placeholders)

        if missing:
            result.error(
                f"{format_rel(invocation.source_path)}:{invocation.line_no}: "
                f"{format_rel(invocation.template_path)} missing vars {missing}"
            )
        if unused:
            result.warn(
                f"{format_rel(invocation.source_path)}:{invocation.line_no}: "
                f"{format_rel(invocation.template_path)} has unused vars {unused}"
            )


def check_phase1_completion_contract(result: CheckResult) -> None:
    for rel_path, expected_marker in PHASE1_STAGE_COMPLETE_RULES.items():
        path = ROOT_DIR / rel_path
        text = read_text(path)
        if expected_marker not in text:
            result.error(f"{format_rel(path)}: missing stage-complete marker `{expected_marker}`")
        if re.search(r"`FINALIZE:\s", text):
            result.error(f"{format_rel(path)}: phase1 template still contains a final `FINALIZE:` payload")


def check_step4_legacy_aliases(result: CheckResult) -> None:
    for path in STEP4_DOCS:
        text = read_text(path)
        for alias in sorted(STEP4_LEGACY_ALIASES):
            if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(alias)}(?![A-Za-z0-9_-])", text):
                result.error(f"{format_rel(path)}: legacy Step4 alias detected: `{alias}`")


def check_planning_example(result: CheckResult) -> None:
    """Verify the planning playbook schema skeleton contains all required field names."""
    path = ROOT_DIR / "references/playbooks/step4/page-planning-playbook.md"
    text = read_text(path)

    # The schema skeleton uses <> placeholders instead of real values,
    # so we verify structural completeness by checking for required field names.
    required_field_names = [
        "slide_number",
        "page_type",
        "narrative_role",
        "page_goal",
        "visual_weight",
        "density_label",
        "density_reason",
        "density_contract",
        "max_cards",
        "max_charts",
        "min_body_font_px",
        "max_lines_per_card",
        "image_policy",
        "decoration_budget",
        "overflow_strategy",
        "layout_hint",
        "director_command",
        "decoration_hints",
        "source_guidance",
        "resources",
        "cards",
        "workflow_metadata",
        "card_id",
        "role",
        "card_type",
        "card_style",
        "content_budget",
        "resource_ref",
    ]

    # Must have a JSON code block
    if "```json" not in text:
        result.error(f"{format_rel(path)}: no JSON schema skeleton found (missing ```json block)")
        return

    for field_name in required_field_names:
        # Check for "field_name" (quoted key) in the file
        if f'"{field_name}"' not in text:
            result.error(f"{format_rel(path)}: schema skeleton missing required field `{field_name}`")


def check_truth_source_docs(result: CheckResult) -> None:
    checks = {
        ROOT_DIR / "SKILL.md": ["planning_validator.py", "check_skill.py"],
        ROOT_DIR / "references/README.md": ["check_skill.py", "planning_validator.py", "prompt_harness.py"],
        ROOT_DIR / "scripts/README.md": ["check_skill.py"],
    }
    for path, required_tokens in checks.items():
        text = read_text(path)
        for token in required_tokens:
            if token not in text:
                result.warn(f"{format_rel(path)}: missing maintenance hint `{token}`")


def check_resource_route_docs(result: CheckResult) -> None:
    for path, patterns in RESOURCE_ROUTE_DOC_RULES.items():
        text = read_text(path)
        for pattern in patterns:
            if not re.search(pattern, text):
                result.error(f"{format_rel(path)}: missing documented resource route pattern `{pattern}`")


def check_step0_interview_contract(result: CheckResult) -> None:
    required_patterns = {
        ROOT_DIR / "SKILL.md": [
            r"tpl-interview-structured-ui\.md",
            r"tpl-interview-text-fallback\.md",
            r"prompt-interview\.md",
            r"BLOCKED_SCRIPT_INTERFACE",
            r"Step 0 默认强制模板化",
            r"结构化采访 UI",
        ],
        ROOT_DIR / "references/cli-cheatsheet.md": [
            r"tpl-interview-structured-ui\.md",
            r"tpl-interview-text-fallback\.md",
            r"prompt-interview\.md",
            r"BLOCKED_SCRIPT_INTERFACE",
            r"Prompt 生成（按能力二选一）",
            r"INTERVIEW_MODE_MODULE",
            r"INTERVIEW_CORE",
            r"module-text-interview-fallback\.md",
        ],
    }
    banned_snippets = {
        ROOT_DIR / "references/cli-cheatsheet.md": [
            "Prompt 生成（可选，主 agent 也可直接发问）",
        ],
    }

    for path, patterns in required_patterns.items():
        text = read_text(path)
        for pattern in patterns:
            if not re.search(pattern, text):
                result.error(f"{format_rel(path)}: missing Step 0 interview contract pattern `{pattern}`")

    for path, snippets in banned_snippets.items():
        text = read_text(path)
        for snippet in snippets:
            if snippet in text:
                result.error(f"{format_rel(path)}: deprecated Step 0 interview wording still present: `{snippet}`")

    expected_files = {
        ROOT_DIR / "references/prompts/tpl-interview.md": [
            "采访问卷共享核心",
            "必须覆盖的 4 组维度",
            "presentation_scenario",
            "`interview-qa.txt` 写盘锚点（强制）",
            "target_action",
            "must_avoid",
            "material_strategy",
        ],
        ROOT_DIR / "references/prompts/tpl-interview-structured-ui.md": [
            "{{TOPIC}}",
            "{{USER_CONTEXT}}",
            "{{INTERVIEW_MODE_MODULE}}",
            "{{INTERVIEW_CORE}}",
        ],
        ROOT_DIR / "references/prompts/tpl-interview-text-fallback.md": [
            "{{TOPIC}}",
            "{{USER_CONTEXT}}",
            "{{INTERVIEW_MODE_MODULE}}",
            "{{INTERVIEW_CORE}}",
        ],
        ROOT_DIR / "references/prompts/module-structured-interview-ui.md": [
            "AskUserQuestion",
            "request_user_input",
            "question/header/id/options",
        ],
        ROOT_DIR / "references/prompts/module-text-interview-fallback.md": [
            "结构化文本采访单",
            "**A. 场景与目标**",
            "全部按默认，用 research",
            "## 归纳后的问答落点",
            "material_strategy: research",
        ],
    }

    for path, tokens in expected_files.items():
        if not path.exists():
            result.error(f"{format_rel(path)}: missing Step 0 interview artifact")
            continue
        text = read_text(path)
        for token in tokens:
            if token not in text:
                result.error(f"{format_rel(path)}: missing Step 0 token `{token}`")


def check_visual_qa_contract(result: CheckResult) -> None:
    cli_text = read_text(ROOT_DIR / "references/cli-cheatsheet.md")
    required_snippets = [
        "visual_qa.py OUTPUT_DIR/png/slide-N.png --planning OUTPUT_DIR/planning/planningN.json --html OUTPUT_DIR/slides/slide-N.html",
        "visual_qa.py OUTPUT_DIR/png --planning-dir OUTPUT_DIR/planning --html-dir OUTPUT_DIR/slides",
    ]
    for snippet in required_snippets:
        if snippet not in cli_text:
            result.error(f"references/cli-cheatsheet.md: missing visual_qa command `{snippet}`")

    html_playbook = read_text(ROOT_DIR / "references/playbooks/step4/page-html-playbook.md")
    html_prompt = read_text(ROOT_DIR / "references/prompts/step4/tpl-page-html.md")
    for path_label, text in (
        ("references/playbooks/step4/page-html-playbook.md", html_playbook),
        ("references/prompts/step4/tpl-page-html.md", html_prompt),
    ):
        for token in ("data-decoration-layer", 'aria-hidden="true"'):
            if token not in text:
                result.error(f"{path_label}: missing decoration contract token `{token}`")


def run_all_checks() -> CheckResult:
    result = CheckResult()
    check_prompt_harness_coverage(result)
    check_phase1_completion_contract(result)
    check_step4_legacy_aliases(result)
    check_planning_example(result)
    check_truth_source_docs(result)
    check_resource_route_docs(result)
    check_step0_interview_contract(result)
    check_visual_qa_contract(result)
    return result


def print_messages(title: str, messages: Iterable[str]) -> None:
    items = list(messages)
    if not items:
        return
    print(title)
    for message in items:
        print(f"- {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check markdown/code contract drift in the PPT skill")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="treat warnings as failures",
    )
    args = parser.parse_args()

    result = run_all_checks()
    print("PPT skill consistency check")
    print(f"errors: {len(result.errors)}")
    print(f"warnings: {len(result.warnings)}")
    print_messages("Errors", result.errors)
    print_messages("Warnings", result.warnings)

    if result.errors:
        return 1
    if args.strict_warnings and result.warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
