#!/usr/bin/env python3
"""Resource router -- dynamic resource loading for PPT workflow.

Three modes:
  menu    -- Extract # title + > blockquote from all resources (for planning)
  resolve -- Load full body of resources referenced in planning JSON (for HTML)
  images  -- Enumerate available local image assets (for planning/html correction)

Usage:
  # Planning stage: get resource menu
  python3 resource_loader.py menu --refs-dir references

  # HTML stage: load only needed resources based on planning JSON
  python3 resource_loader.py resolve --refs-dir references --planning planning3.json

  # Planning/HTML stage: list all local image assets
  python3 resource_loader.py images --images-dir OUTPUT_DIR/images
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ── Field-to-directory routing table ────────────────────────────────────────
# Planning JSON field -> resource directory -> match logic
FIELD_ROUTES = {
    # Page-level fields
    "layout_hint": "layouts",
    "page_type": "page-templates",
    # Card-level fields
    "card_type": "blocks",
    "chart_type": "charts",
}

# Always-include resources when certain conditions are met
ALWAYS_INCLUDE = {
    "blocks/card-styles.md": lambda pages: any(
        card.get("card_style")
        for page in pages
        for card in _as_list(page.get("cards"))
        if isinstance(card, dict)
    ),
    # Data type mapping tables -- always include for planning context
    "design-runtime/data-type-visual-mapping.md": lambda pages: True,
    "design-runtime/data-type-decoration-mapping.md": lambda pages: True,
    # Canvas specs (1280x720 hard constraint) -- MUST always inject
    "design-runtime/design-specs.md": lambda pages: True,
    # CSS advanced techniques (W1-W12) -- always inject so HTML subagent can use without planning preselection
    "design-runtime/css-weapons.md": lambda pages: True,
    # Director command rules -- always inject so HTML subagent understands director_command field conventions
    "design-runtime/director-command-rules.md": lambda pages: True,
}

# Explicit ref fields in planning JSON resources section
REF_FIELD_ROUTES = {
    "layout_refs": "layouts",
    "block_refs": "blocks",
    "chart_refs": "charts",
    "principle_refs": "principles",
}

# Categories to scan for menu
MENU_CATEGORIES = [
    "layouts",
    "blocks",
    "charts",
    "styles",
    "principles",
    "page-templates",
    "design-runtime",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _as_list(val: Any) -> list:
    return val if isinstance(val, list) else []


def _natural_text_key(value: str) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", value)
    key: list[Any] = []
    for part in parts:
        key.append(int(part) if part.isdigit() else part.lower())
    return tuple(key)


# ── Menu mode: extract titles + blockquotes ─────────────────────────────────

def extract_menu_entry(filepath: Path) -> dict[str, str] | None:
    """Extract # title and all consecutive > blockquote lines from a resource file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    lines = text.split("\n")
    title = ""
    quote_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
        elif title and stripped.startswith("> "):
            quote_lines.append(stripped[2:].strip())
        elif title and stripped == ">":
            # Empty blockquote continuation line
            quote_lines.append("")
        elif title and quote_lines:
            # First non-quote line after quote block = done
            break
        elif title and stripped and not stripped.startswith(">"):
            # Non-empty non-quote line after title means no blockquote
            break

    if not title:
        return None

    return {
        "file": filepath.name,
        "id": filepath.stem,
        "title": title,
        "quote": "\n".join(quote_lines).strip(),
    }


def generate_menu(refs_dir: Path, categories: list[str] | None = None) -> str:
    """Generate resource menu with titles + full blockquotes organized by category."""
    cats = categories or MENU_CATEGORIES
    sections: list[str] = []

    for cat in cats:
        cat_dir = refs_dir / cat
        if not cat_dir.is_dir():
            continue

        entries: list[dict[str, str]] = []
        for md_file in sorted(cat_dir.glob("*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            # Skip runtime-only files
            if md_file.name.startswith("runtime-"):
                continue
            entry = extract_menu_entry(md_file)
            if entry:
                entries.append(entry)

        if entries:
            cat_lines = [f"### {cat}/"]
            for e in entries:
                cat_lines.append(f"\n#### {e['id']}")
                cat_lines.append(f"**{e['title']}**")
                if e["quote"]:
                    # Indent multi-line quotes for readability
                    for q_line in e["quote"].split("\n"):
                        cat_lines.append(f"> {q_line}" if q_line else ">")
            sections.append("\n".join(cat_lines))

    return "\n\n".join(sections)


# ── Resolve mode: load resource bodies based on planning JSON ───────────────

def extract_body(filepath: Path) -> str:
    """Extract body content (everything after the > blockquote line)."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return ""

    lines = text.split("\n")
    body_start = 0
    found_title = False
    found_quote = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not found_title and stripped.startswith("# "):
            found_title = True
            continue
        if found_title and stripped.startswith("> "):
            found_quote = True
            continue
        if found_title and (found_quote or (stripped and not stripped.startswith(">"))):
            body_start = i
            break

    # Skip leading blank lines
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    body = "\n".join(lines[body_start:]).strip()
    return body


def normalize_ref(value: str) -> str:
    """Normalize a resource reference to a filename stem."""
    raw = value.strip().strip("`").strip()
    # Remove path prefixes
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    # Remove .md extension
    if raw.endswith(".md"):
        raw = raw[:-3]
    # Normalize underscores to hyphens
    return raw.replace("_", "-")


def collect_resource_refs(pages: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Collect all resource references from planning pages, grouped by directory."""
    refs: dict[str, set[str]] = {d: set() for d in set(FIELD_ROUTES.values()) | set(REF_FIELD_ROUTES.values())}

    for page in pages:
        # Page-level fields
        for field, directory in FIELD_ROUTES.items():
            if field == "chart_type":
                continue  # handled at card level
            val = page.get(field)
            if isinstance(val, str) and val.strip():
                refs[directory].add(normalize_ref(val))

        # Card-level fields
        for card in _as_list(page.get("cards")):
            if not isinstance(card, dict):
                continue

            # card_type -> blocks/
            card_type = card.get("card_type")
            if isinstance(card_type, str) and card_type.strip():
                refs["blocks"].add(normalize_ref(card_type))

            # chart.chart_type -> charts/
            chart = card.get("chart")
            if isinstance(chart, dict):
                chart_type = chart.get("chart_type")
                if isinstance(chart_type, str) and chart_type.strip():
                    refs["charts"].add(normalize_ref(chart_type))

            # Card-level resource_ref
            resource_ref = card.get("resource_ref")
            if isinstance(resource_ref, dict):
                for key, directory in [("block", "blocks"), ("chart", "charts"), ("principle", "principles")]:
                    val = resource_ref.get(key)
                    if isinstance(val, str) and val.strip():
                        refs[directory].add(normalize_ref(val))

        # Explicit resources section
        resources = page.get("resources")
        if isinstance(resources, dict):
            # page_template
            pt = resources.get("page_template")
            if isinstance(pt, str) and pt.strip():
                refs["page-templates"].add(normalize_ref(pt))

            # Ref lists
            for field, directory in REF_FIELD_ROUTES.items():
                for item in _as_list(resources.get(field)):
                    if isinstance(item, str) and item.strip():
                        refs[directory].add(normalize_ref(item))

    return refs


def load_planning_pages(path: Path) -> list[dict[str, Any]]:
    """Load planning pages from a JSON file or directory."""
    text = path.read_text(encoding="utf-8").strip()

    # Try direct JSON parse
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # Try extracting from fenced block
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
        if match:
            payload = json.loads(match.group(1))
        else:
            first, last = text.find("{"), text.rfind("}")
            if first != -1 and last > first:
                payload = json.loads(text[first:last + 1])
            else:
                raise ValueError(f"Cannot parse planning JSON: {path}")

    if isinstance(payload, dict) and "ppt_planning" in payload:
        return _as_list(payload["ppt_planning"].get("pages"))
    if isinstance(payload, dict):
        page = payload.get("page", payload)
        if isinstance(page, dict) and ("slide_number" in page or "page_number" in page):
            return [page]
    return []


def resolve_resources(refs_dir: Path, planning_path: Path) -> str:
    """Load full resource bodies based on planning JSON field references."""
    pages = load_planning_pages(planning_path)
    if not pages:
        print("WARN: no planning pages found", file=sys.stderr)
        return ""

    resource_refs = collect_resource_refs(pages)
    sections: list[str] = []
    loaded_files: set[str] = set()

    for directory, ref_ids in sorted(resource_refs.items()):
        dir_path = refs_dir / directory
        if not dir_path.is_dir():
            continue

        for ref_id in sorted(ref_ids):
            # Try multiple filename patterns
            candidates = [
                dir_path / f"{ref_id}.md",
                dir_path / f"{ref_id.replace('-', '_')}.md",
            ]
            for candidate in candidates:
                if candidate.exists() and str(candidate) not in loaded_files:
                    loaded_files.add(str(candidate))
                    title_line = ""
                    for line in candidate.read_text(encoding="utf-8").split("\n"):
                        if line.strip().startswith("# "):
                            title_line = line.strip()
                            break
                    body = extract_body(candidate)
                    if body:
                        sections.append(f"{title_line}\n\n{body}")
                    break

    # Always-include resources
    for rel_path, condition in ALWAYS_INCLUDE.items():
        full_path = refs_dir / rel_path
        if full_path.exists() and str(full_path) not in loaded_files and condition(pages):
            loaded_files.add(str(full_path))
            title_line = ""
            for line in full_path.read_text(encoding="utf-8").split("\n"):
                if line.strip().startswith("# "):
                    title_line = line.strip()
                    break
            body = extract_body(full_path)
            if body:
                sections.append(f"{title_line}\n\n{body}")

    return "\n\n---\n\n".join(sections)


def generate_image_inventory(images_dir: Path) -> str:
    """Generate deterministic local image inventory for subagent correction loops."""
    image_files: list[Path] = []
    if images_dir.is_dir():
        image_files = [
            path for path in images_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ]
        image_files.sort(key=lambda p: _natural_text_key(str(p.relative_to(images_dir)).replace("\\", "/")))

    try:
        images_dir_display = images_dir.relative_to(Path.cwd()).as_posix()
    except ValueError:
        images_dir_display = images_dir.as_posix()

    lines: list[str] = [
        "# Image Asset Inventory",
        "",
        f"images_dir: {images_dir_display}",
        f"exists: {images_dir.is_dir()}",
        f"count: {len(image_files)}",
        "",
        "## Assets",
    ]
    if not image_files:
        lines.append("(empty)")
        lines.append("")
        lines.append("当前没有可直接绑定的本地图片。")
        lines.append("如果本页走 AI 文生图，可先在 planning 中规划未来落盘路径，再在图片阶段生成。")
        lines.append("如果本页走 manual_slot / decorate，可继续后续 HTML，不必等待图片文件。")
        return "\n".join(lines)

    for idx, file_path in enumerate(image_files, start=1):
        rel = file_path.relative_to(images_dir).as_posix()
        lines.append(f"{idx}. rel={rel}")

    lines.append("")
    lines.append("约束：当 planning 选择 provided 模式时，image.source_hint 必须引用上面清单中的相对路径。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynamic resource loader for PPT workflow")
    subparsers = parser.add_subparsers(dest="mode")

    # Menu mode
    menu_parser = subparsers.add_parser("menu", help="Generate resource menu (titles + blockquotes)")
    menu_parser.add_argument("--refs-dir", required=True, help="Path to references directory")
    menu_parser.add_argument("--categories", help="Comma-separated list of categories (default: all)")
    menu_parser.add_argument("--output", help="Output file path (default: stdout)")

    # Resolve mode
    resolve_parser = subparsers.add_parser("resolve", help="Load resource bodies based on planning JSON")
    resolve_parser.add_argument("--refs-dir", required=True, help="Path to references directory")
    resolve_parser.add_argument("--planning", required=True, help="Path to planning JSON file")
    resolve_parser.add_argument("--output", help="Output file path (default: stdout)")

    # Images mode
    images_parser = subparsers.add_parser("images", help="Generate local image inventory for planning/html stages")
    images_parser.add_argument("--images-dir", required=True, help="Path to local images directory")
    images_parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()
    if not args.mode:
        parser.print_help()
        return 1

    if args.mode == "menu":
        refs_dir = Path(args.refs_dir)
        if not refs_dir.is_dir():
            print(f"ERROR: refs-dir not found: {refs_dir}", file=sys.stderr)
            return 1
        cats = args.categories.split(",") if args.categories else None
        result = generate_menu(refs_dir, cats)

    elif args.mode == "resolve":
        refs_dir = Path(args.refs_dir)
        planning_path = Path(args.planning)
        if not refs_dir.is_dir():
            print(f"ERROR: refs-dir not found: {refs_dir}", file=sys.stderr)
            return 1
        if not planning_path.exists():
            print(f"ERROR: planning file not found: {planning_path}", file=sys.stderr)
            return 1
        result = resolve_resources(refs_dir, planning_path)
        
        # [增强版] 自动保存所提取组合资源的一份副本，用于审计与开发排查
        try:
            if planning_path.parent.name == "planning":
                runtime_dir = planning_path.parent.parent / "runtime"
                runtime_dir.mkdir(parents=True, exist_ok=True)
                audit_file = runtime_dir / f"resolved_assets_{planning_path.stem}.md"
            else:
                audit_file = planning_path.parent / f"resolved_assets_{planning_path.stem}.md"
            audit_file.write_text(result, encoding="utf-8")
            print(f"[Audit] 自动保存所提取组合资源副本至: {audit_file}", file=sys.stderr)
        except Exception:
            pass
    elif args.mode == "images":
        images_dir = Path(args.images_dir)
        result = generate_image_inventory(images_dir)
    else:
        parser.print_help()
        return 1

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result, encoding="utf-8")
        print(f"Written to {out} ({len(result)} chars)", file=sys.stderr)
    else:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
