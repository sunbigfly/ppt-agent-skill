#!/usr/bin/env python3
"""visual_qa.py — 自动化视觉质量断言脚本

在 subagent review 完成后，由主 agent 运行此脚本对 slide PNG 做客观检测。
检测项全部基于像素分析，不依赖 LLM 判断。

用法：
    # 检查单页
    python3 scripts/visual_qa.py OUTPUT_DIR/png/slide-1.png --planning OUTPUT_DIR/planning/planning1.json

    # 批量检查所有页
    python3 scripts/visual_qa.py OUTPUT_DIR/png --planning-dir OUTPUT_DIR/planning

    # 同时把文本报告写入 runtime
    python3 scripts/visual_qa.py OUTPUT_DIR/png/slide-1.png --planning OUTPUT_DIR/planning/planning1.json --output OUTPUT_DIR/runtime/page-review-qa-1.txt

退出码：
    0 = 全部通过
    1 = 存在 FAIL（致命缺陷，建议重跑该页）
    2 = 只有 WARN（品质警告，可交付但建议人工复查）
"""

import json
import os
import sys
from pathlib import Path

# PIL 是唯一外部依赖；如缺失则给出友好提示
try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ─────────────────────── 检测函数 ───────────────────────

def check_dimensions(img: Image.Image) -> dict:
    """检测截图分辨率是否为 16:9 比例，支持下层缩小图片"""
    w, h = img.size
    if abs(w / h - 16 / 9) < 0.05:
        if w >= 960:
            return {"id": "DIM-01", "status": "PASS", "msg": f"分辨率 {w}x{h} (比例正常)"}
        else:
            return {"id": "DIM-01", "status": "WARN", "msg": f"分辨率 {w}x{h} (较小但可接受)"}
    return {"id": "DIM-01", "status": "FAIL", "msg": f"分辨率 {w}x{h} 不符合 16:9 规格"}


def check_blank_ratio(img: Image.Image, threshold: float = 0.40) -> dict:
    """检测大面积空白/纯色区域是否超过阈值。

    策略：将图片缩放到小尺寸后统计主色占比。
    如果占比 > threshold 且主色极暗（背景色），再检查非背景区域是否太少。
    """
    # 缩放以加速
    small = img.resize((128, 72), Image.LANCZOS)
    pixels = list(small.getdata())
    total = len(pixels)

    # 统计颜色频率（降低精度到 8-bit 级别）
    color_count: dict[tuple, int] = {}
    for p in pixels:
        # 量化到 32 级
        quantized = (p[0] // 8 * 8, p[1] // 8 * 8, p[2] // 8 * 8)
        color_count[quantized] = color_count.get(quantized, 0) + 1

    # 找最高频色
    dominant_color = max(color_count, key=color_count.get)
    dominant_ratio = color_count[dominant_color] / total

    if dominant_ratio > threshold:
        # 检查这个 dominant 是不是背景色（暗色系）
        brightness = sum(dominant_color) / 3
        if brightness < 60:
            # 深色背景占比高可能正常（深色主题），但需要检查内容色占比
            content_pixels = sum(1 for p in pixels if sum(p) / 3 > 80)
            content_ratio = content_pixels / total
            if content_ratio < 0.15:
                return {"id": "BLANK-01", "status": "FAIL",
                        "msg": f"内容区域仅占 {content_ratio:.0%}，背景占 {dominant_ratio:.0%}（P0-3 大面积空白）"}
            return {"id": "BLANK-01", "status": "PASS",
                    "msg": f"深色背景 {dominant_ratio:.0%}，内容区 {content_ratio:.0%}"}
        else:
            return {"id": "BLANK-01", "status": "FAIL",
                    "msg": f"主色 RGB{dominant_color} 占比 {dominant_ratio:.0%}，疑似大面积空白（P0-3）"}

    return {"id": "BLANK-01", "status": "PASS",
            "msg": f"画面色彩分布正常，主色占比 {dominant_ratio:.0%}"}


def check_vertical_text(img: Image.Image) -> dict:
    """辅助检测：是否存在疑似竖排单字列。

    注意：此检测为辅助提示（WARN），不做最终判定。
    排版质量的真正判断应由 LLM view_file 看 PNG 截图完成。
    """
    w, h = img.size
    right_half = img.crop((w // 2, 0, w, h))
    small = right_half.resize((256, 144), Image.LANCZOS).convert("L")
    pixels = small.load()
    sw, sh = small.size

    threshold = 60
    suspect_regions = []

    x = 0
    while x < sw:
        col_content = sum(1 for y in range(sh) if pixels[x, y] > threshold)

        if col_content > sh * 0.25:  # 宽松阈值，宁可误报
            band_start = x
            band_end = x
            while band_end < sw - 1:
                next_content = sum(1 for y in range(sh) if pixels[band_end + 1, y] > threshold)
                if next_content > sh * 0.15:
                    band_end += 1
                else:
                    break

            band_width = band_end - band_start + 1
            content_rows = set()
            for bx in range(band_start, band_end + 1):
                for y in range(sh):
                    if pixels[bx, y] > threshold:
                        content_rows.add(y)

            content_height = (max(content_rows) - min(content_rows) + 1) if content_rows else 0
            width_ratio = band_width / sw
            height_ratio = content_height / sh

            if width_ratio < 0.06 and height_ratio > 0.35:
                suspect_regions.append(f"w={width_ratio:.1%} h={height_ratio:.1%}")

            x = band_end + 1
        else:
            x += 1

    if suspect_regions:
        return {"id": "VTXT-01", "status": "WARN",
                "msg": f"检测到 {len(suspect_regions)} 处疑似窄列内容带（{'; '.join(suspect_regions[:3])}），建议人工确认排版"}

    return {"id": "VTXT-01", "status": "PASS", "msg": "未检测到竖排异常"}


def check_overflow_cutoff(img: Image.Image) -> dict:
    """检测底部/右侧是否有内容被裁切痕迹。

    策略：检查底部和右侧边缘几行像素是否仍有非背景内容（提示被裁切）。
    """
    w, h = img.size
    pixels = img.load()

    # 检查底部最后 4 行
    bottom_content_pixels = 0
    bottom_total = w * 4
    for y in range(h - 4, h):
        for x in range(w):
            p = pixels[x, y]
            brightness = sum(p[:3]) / 3
            if brightness > 80:
                bottom_content_pixels += 1

    bottom_ratio = bottom_content_pixels / bottom_total if bottom_total > 0 else 0

    # 检查右侧最后 4 列
    right_content_pixels = 0
    right_total = h * 4
    for x in range(w - 4, w):
        for y in range(h):
            p = pixels[x, y]
            brightness = sum(p[:3]) / 3
            if brightness > 80:
                right_content_pixels += 1

    right_ratio = right_content_pixels / right_total if right_total > 0 else 0

    issues = []
    if bottom_ratio > 0.2:
        issues.append(f"底部边缘有 {bottom_ratio:.0%} 亮像素，疑似内容被裁切")
    if right_ratio > 0.15:
        issues.append(f"右侧边缘有 {right_ratio:.0%} 亮像素，疑似内容被裁切")

    if issues:
        return {"id": "CUT-01", "status": "WARN", "msg": " | ".join(issues)}

    return {"id": "CUT-01", "status": "PASS", "msg": "边缘无异常裁切痕迹"}


def check_contrast_zones(img: Image.Image) -> dict:
    """检测是否存在大面积低对比度区域（文字不可读）。

    策略：将图片分成 8x8 网格，对每个块计算亮度标准差。
    如果大量块的标准差极低（= 纯色块），且这些块不是背景色，则可能有对比度问题。
    """
    w, h = img.size
    grid_w, grid_h = 8, 8
    block_w = w // grid_w
    block_h = h // grid_h

    low_contrast_blocks = 0
    total_blocks = grid_w * grid_h

    for gx in range(grid_w):
        for gy in range(grid_h):
            block = img.crop((gx * block_w, gy * block_h, (gx + 1) * block_w, (gy + 1) * block_h))
            small_block = block.resize((16, 16), Image.LANCZOS)
            pixels = list(small_block.getdata())
            brightnesses = [sum(p[:3]) / 3 for p in pixels]

            avg = sum(brightnesses) / len(brightnesses)
            variance = sum((b - avg) ** 2 for b in brightnesses) / len(brightnesses)

            # 低方差 + 中等亮度 = 可能有文字被遮盖或对比度不足
            if variance < 25 and 40 < avg < 200:
                low_contrast_blocks += 1

    ratio = low_contrast_blocks / total_blocks
    if ratio > 0.6:
        return {"id": "CONT-01", "status": "WARN",
                "msg": f"{ratio:.0%} 的区块对比度极低，可能存在文字不可读区域"}

    return {"id": "CONT-01", "status": "PASS",
            "msg": f"对比度分布正常（低对比区块 {ratio:.0%}）"}


def check_file_size(png_path: Path) -> dict:
    """检测 PNG 文件大小是否合理。"""
    size = png_path.stat().st_size
    if size < 10_000:
        return {"id": "SIZE-01", "status": "FAIL",
                "msg": f"PNG 仅 {size:,} bytes，疑似空白页或截图失败"}
    if size < 50_000:
        return {"id": "SIZE-01", "status": "WARN",
                "msg": f"PNG {size:,} bytes，内容可能过少"}
    return {"id": "SIZE-01", "status": "PASS", "msg": f"PNG {size:,} bytes"}


def check_planning_cards_coverage(img: Image.Image, planning_path: Path) -> dict:
    """辅助检测：planning 卡片 vs 图片结构复杂度的粗略对比。

    注意：此检测为辅助提示。深色主题下边缘密度天然偏低，
    真正的卡片缺失判断应由 LLM 看图 + 对照 planning JSON 完成。
    """
    if not planning_path.exists():
        return {"id": "CARD-01", "status": "WARN", "msg": f"planning 文件不存在: {planning_path}"}

    try:
        with open(planning_path) as f:
            planning = json.load(f)
        page = planning.get("page", planning)
        cards = page.get("cards", [])
        card_count = len(cards)
    except (json.JSONDecodeError, KeyError):
        return {"id": "CARD-01", "status": "WARN", "msg": "planning JSON 解析失败"}

    if card_count == 0:
        return {"id": "CARD-01", "status": "PASS", "msg": "planning 无卡片定义"}

    w, h = img.size
    small = img.resize((64, 36), Image.LANCZOS).convert("L")
    pixels = small.load()
    sw, sh = small.size

    edge_count = 0
    for y in range(sh):
        for x in range(1, sw):
            diff = abs(pixels[x, y] - pixels[x - 1, y])
            if diff > 30:
                edge_count += 1

    edge_density = edge_count / (sw * sh)

    # 极低边缘密度 + 多卡片 = 疑似卡片缺失（辅助提示）
    if card_count >= 3 and edge_density < 0.015:
        return {"id": "CARD-01", "status": "WARN",
                "msg": f"planning 有 {card_count} 张卡片，但图片结构极简（边缘密度 {edge_density:.3f}），建议人工确认卡片完整性"}

    return {"id": "CARD-01", "status": "PASS",
            "msg": f"planning {card_count} 张卡片，图片边缘密度 {edge_density:.3f}"}


# ─────────────────────── 主逻辑 ───────────────────────

def run_checks(png_path: Path, planning_path: Path | None = None) -> list[dict]:
    """对单张 PNG 运行全部检测。"""
    results = []

    # 文件级检查
    results.append(check_file_size(png_path))

    # 打开图片
    try:
        img = Image.open(png_path).convert("RGB")
    except Exception as e:
        results.append({"id": "OPEN-01", "status": "FAIL", "msg": f"无法打开 PNG: {e}"})
        return results

    # 像素级检查
    results.append(check_dimensions(img))
    results.append(check_blank_ratio(img))
    results.append(check_vertical_text(img))
    results.append(check_overflow_cutoff(img))
    results.append(check_contrast_zones(img))

    # planning 对照检查
    if planning_path:
        results.append(check_planning_cards_coverage(img, planning_path))

    return results


def print_report(png_name: str, results: list[dict]) -> tuple[int, int]:
    """打印检测报告，返回 (fail_count, warn_count)。"""
    fails = sum(1 for r in results if r["status"] == "FAIL")
    warns = sum(1 for r in results if r["status"] == "WARN")

    print(f"\n{'─' * 60}")
    print(f"  {png_name}")
    print(f"{'─' * 60}")

    for r in results:
        icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX"}[r["status"]]
        print(f"  [{icon}] {r['id']}: {r['msg']}")

    verdict = "PASS" if fails == 0 and warns == 0 else ("FAIL" if fails > 0 else "WARN")
    print(f"\n  verdict: {verdict}  (FAIL={fails}, WARN={warns})")
    return fails, warns


def build_report_lines(png_name: str, results: list[dict]) -> tuple[list[str], int, int]:
    """构造文本报告，同时返回 (fail_count, warn_count)。"""
    fails = sum(1 for r in results if r["status"] == "FAIL")
    warns = sum(1 for r in results if r["status"] == "WARN")
    verdict = "PASS" if fails == 0 and warns == 0 else ("FAIL" if fails > 0 else "WARN")

    lines = [
        "",
        f"{'─' * 60}",
        f"  {png_name}",
        f"{'─' * 60}",
    ]
    for r in results:
        icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX"}[r["status"]]
        lines.append(f"  [{icon}] {r['id']}: {r['msg']}")
    lines.append(f"\n  verdict: {verdict}  (FAIL={fails}, WARN={warns})")
    return lines, fails, warns


def write_text_report(path: Path | None, text: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()

    # 解析可选参数
    planning_path = None
    planning_dir = None
    output_path = None
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--planning" and i + 1 < len(args):
            planning_path = Path(args[i + 1]).resolve()
            i += 2
        elif args[i] == "--planning-dir" and i + 1 < len(args):
            planning_dir = Path(args[i + 1]).resolve()
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = Path(args[i + 1]).resolve()
            i += 2
        else:
            i += 1

    # 收集要检查的 PNG
    if target.is_file():
        pngs = [target]
    elif target.is_dir():
        pngs = sorted(target.glob("slide-*.png"))
    else:
        print(f"ERROR: {target} 不存在", file=sys.stderr)
        sys.exit(1)

    if not pngs:
        print(f"ERROR: 未找到 slide-*.png 文件于 {target}", file=sys.stderr)
        sys.exit(1)

    total_fails = 0
    total_warns = 0
    report_lines: list[str] = []

    for png in pngs:
        # 自动推断 planning 路径
        pp = planning_path
        if pp is None and planning_dir:
            # slide-3.png -> planning3.json
            import re
            m = re.search(r"slide-(\d+)", png.stem)
            if m:
                pp = planning_dir / f"planning{m.group(1)}.json"

        results = run_checks(png, pp)
        lines, f, w = build_report_lines(png.name, results)
        report_lines.extend(lines)
        print("\n".join(lines))
        total_fails += f
        total_warns += w

    summary_lines = [
        f"\n{'=' * 60}",
        f"  TOTAL: {len(pngs)} pages, FAIL={total_fails}, WARN={total_warns}",
    ]
    if total_fails > 0:
        summary_lines.append("  EXIT 1 — 存在致命缺陷，建议重跑对应页面")
    elif total_warns > 0:
        summary_lines.append("  EXIT 2 — 存在品质警告，建议人工复查")
    else:
        summary_lines.append("  EXIT 0 — 全部通过")
    summary_lines.append(f"{'=' * 60}")
    print("\n".join(summary_lines))

    write_text_report(output_path, "\n".join(report_lines + summary_lines) + "\n")

    sys.exit(1 if total_fails > 0 else (2 if total_warns > 0 else 0))


if __name__ == "__main__":
    main()
