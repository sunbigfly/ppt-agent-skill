#!/usr/bin/env python3
"""HTML -> PNG 高清截图转换

使用 Puppeteer 在 headless 浏览器中打开 HTML 并截图。
- 视口 1280x720，设备像素比 2x -> 输出 2560x1440 PNG
- 比 SVG 管线兼容性更好（所有 CSS 特性均保留）
- 缺点：文字不可编辑（成为像素）

用法：
    python3 scripts/html2png.py <html_dir_or_file> [-o output_dir] [--scale 1]
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCREENSHOT_SCRIPT = r"""
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
    const config = JSON.parse(process.argv[2]);
    const scale = config.scale || 1;
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu',
               '--font-render-hinting=none']
    });

    for (const item of config.files) {
        const page = await browser.newPage();
        await page.setViewport({
            width: 1280,
            height: 720,
            deviceScaleFactor: scale
        });

        await page.goto('file://' + item.html, {
            waitUntil: 'networkidle0',
            timeout: 30000
        });
        // 智能等候字体与所有贴图实体装载完成再捕获
        await page.evaluate(async () => {
            await document.fonts.ready;
            const images = Array.from(document.querySelectorAll('img'));
            await Promise.all(images.map(img => {
                if (img.complete) return Promise.resolve();
                return new Promise(r => { img.onload = r; img.onerror = r; });
            }));
        });

        await page.screenshot({
            path: item.png,
            type: 'png',
            fullPage: false,
            clip: { x: 0, y: 0, width: 1280, height: 720 }
        });
        console.log('PNG: ' + path.basename(item.html) + ' -> ' + path.basename(item.png));
        await page.close();
    }

    await browser.close();
    console.log('Done: ' + config.files.length + ' PNGs');
})();
"""


def get_dep_dir(work_dir: Path) -> Path:
    curr = work_dir.resolve()
    for _ in range(5):
        if curr.name == "ppt-output":
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent
    return work_dir


def ensure_puppeteer(work_dir: Path) -> bool:
    """确保 Puppeteer 已安装，返回是否可用。"""
    dep_dir = get_dep_dir(work_dir)
    try:
        r = subprocess.run(
            ["node", "-e", "require('puppeteer')"],
            capture_output=True, text=True, timeout=10, cwd=str(work_dir)
        )
        if r.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print(f"Installing puppeteer in {dep_dir}...")
    try:
        r = subprocess.run(
            ["npm", "install", "puppeteer"],
            capture_output=True, text=True, timeout=180, cwd=str(dep_dir)
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def convert(html_dir: Path, output_dir: Path, scale: float = 1.0) -> bool:
    """主转换入口。"""
    if html_dir.is_file():
        html_files = [html_dir]
        work_dir = html_dir.parent.parent
    else:
        html_files = sorted(html_dir.glob("*.html"), key=lambda p: [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', p.stem)])
        work_dir = html_dir.parent

    if not html_files:
        print(f"No HTML files in {html_dir}", file=sys.stderr)
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    if not ensure_puppeteer(work_dir):
        print("Puppeteer unavailable. Install Node.js and retry.", file=sys.stderr)
        return False

    config = {
        "scale": scale,
        "files": [
            {"html": str(f), "png": str(output_dir / (f.stem + ".png"))}
            for f in html_files
        ]
    }

    script_path = work_dir / ".html2png_tmp.js"
    script_path.write_text(SCREENSHOT_SCRIPT)

    try:
        print(f"Converting {len(html_files)} HTML files -> PNG ({scale}x scale)...")
        r = subprocess.run(
            ["node", str(script_path), json.dumps(config)],
            cwd=str(work_dir), timeout=300
        )
        if r.returncode != 0:
            return False
        print(f"\nDone! {len(html_files)} PNGs -> {output_dir}")
        return True
    except subprocess.TimeoutExpired:
        print("Timeout: screenshot took too long", file=sys.stderr)
        return False
    finally:
        if script_path.exists():
            script_path.unlink()


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: python3 scripts/html2png.py <html_dir_or_file> [-o output_dir] [--scale 1]")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    html_path = Path(sys.argv[1]).resolve()

    output_dir = None
    scale = 1.0

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            output_dir = Path(args[i + 1]).resolve()
            i += 2
        elif args[i] == "--scale" and i + 1 < len(args):
            scale = float(args[i + 1])
            i += 2
        else:
            i += 1

    if output_dir is None:
        output_dir = (html_path.parent if html_path.is_file() else html_path.parent) / "png"

    success = convert(html_path, output_dir, scale)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
