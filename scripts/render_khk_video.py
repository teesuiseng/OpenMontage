#!/usr/bin/env python3
"""Render the KHK ER proteostasis explainer video as a GitHub Actions artifact.

This intentionally keeps the MP4 out of git while making it reproducible on
GitHub. It reads the committed script checkpoint and renders a caption-led MP4.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 30
DURATION_SECONDS = 60
TOTAL_FRAMES = FPS * DURATION_SECONDS

BLUE = (37, 99, 235)
DARK = (31, 41, 55)
MUTED = (107, 114, 128)
AMBER = (245, 158, 11)
GREEN = (16, 185, 129)
BG = (255, 255, 255)
SURFACE = (249, 250, 251)
PALE_BLUE = (239, 246, 255)
PALE_GREEN = (236, 253, 245)
PALE_ORANGE = (255, 247, 237)
GRID = (245, 247, 250)
BORDER = (229, 231, 235)


def find_font(name: str) -> str:
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/usr/share/fonts/truetype/liberation2/{name}",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"Could not find font {name}; tried {candidates}")


def load_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    regular = find_font("DejaVuSans.ttf")
    bold = find_font("DejaVuSans-Bold.ttf")
    return {
        "regular": ImageFont.truetype(regular, 34),
        "bold": ImageFont.truetype(bold, 58),
        "bold2": ImageFont.truetype(bold, 42),
        "small": ImageFont.truetype(regular, 25),
        "caption": ImageFont.truetype(bold, 29),
    }


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if not words:
            lines.append("")
    return lines


def centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: float,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = DARK,
    max_width: int = 1080,
    spacing: int = 12,
) -> None:
    lines = wrap_text(draw, text, font, max_width)
    heights = [draw.textbbox((0, 0), line or " ", font=font)[3] for line in lines]
    total_height = sum(heights) + spacing * (len(lines) - 1)
    yy = y - total_height / 2
    for line, height in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, yy), line, font=font, fill=fill)
        yy += height + spacing


def pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    color: tuple[int, int, int],
    font: ImageFont.FreeTypeFont,
) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 34
    height = bbox[3] - bbox[1] + 18
    draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=BG, outline=color, width=3)
    draw.text((x + 17, y + 8), text, font=font, fill=color)


def draw_background(draw: ImageDraw.ImageDraw, frame: int) -> None:
    draw.rectangle((0, 0, W, H), fill=BG)
    for x in range(0, W, 48):
        draw.line((x, 0, x, H), fill=GRID, width=1)
    for y in range(0, H, 48):
        draw.line((0, y, W, y), fill=GRID, width=1)

    orbs = [
        (190, 160, 130, BLUE),
        (1040, 180, 160, AMBER),
        (960, 600, 120, GREEN),
        (260, 620, 90, BLUE),
    ]
    for i, (cx, cy, radius, color) in enumerate(orbs):
        ox = math.sin(frame / 180 + i) * 18
        oy = math.cos(frame / 210 + i) * 14
        pale = tuple(int(v * 0.08 + 255 * 0.92) for v in color)
        draw.ellipse((cx - radius + ox, cy - radius + oy, cx + radius + ox, cy + radius + oy), fill=pale)


def draw_caption(draw: ImageDraw.ImageDraw, t: float, sections: list[dict], fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    section = next((s for s in sections if s["start_seconds"] <= t < s["end_seconds"]), sections[-1])
    words = section["text"].split()
    if not words:
        return
    progress = (t - section["start_seconds"]) / (section["end_seconds"] - section["start_seconds"])
    idx = min(len(words) - 1, max(0, int(progress * len(words))))
    start = max(0, idx - 5)
    chunk = " ".join(words[start : min(len(words), start + 10)])
    lines = wrap_text(draw, chunk, fonts["caption"], 980)
    box_h = 48 + len(lines) * 36
    y = H - box_h - 24
    draw.rounded_rectangle((120, y, W - 120, H - 28), radius=18, fill=BG, outline=BORDER, width=2)
    yy = y + 22
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fonts["caption"])
        draw.text(((W - (bbox[2] - bbox[0])) / 2, yy), line, font=fonts["caption"], fill=DARK)
        yy += 36


def scene1(draw: ImageDraw.ImageDraw, _t: float, _frame: int, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    centered(draw, "KHK", 250, fonts["bold"], BLUE)
    centered(draw, "one enzyme, two jobs", 325, fonts["bold2"], DARK)
    pill(draw, (280, 420), "fructose metabolism", BLUE, fonts["small"])
    pill(draw, (725, 420), "ER stress adaptation", GREEN, fonts["small"])
    draw.line((535, 445, 720, 445), fill=AMBER, width=5)


def scene2(draw: ImageDraw.ImageDraw, t: float, _frame: int, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    centered(draw, "Nutrient overload creates an ER decision point", 105, fonts["bold2"], DARK, 1120)
    nodes = [
        ("fructose +\nsaturated fat", 220, 310, BLUE),
        ("ER folding\nbacklog", 640, 310, AMBER),
        ("adapt\nor die?", 1060, 310, GREEN),
    ]
    progress = ease((t - 8) / 10)
    for i, (text, cx, cy, color) in enumerate(nodes):
        if progress < i / 3:
            continue
        draw.rounded_rectangle((cx - 130, cy - 70, cx + 130, cy + 70), radius=28, fill=SURFACE, outline=color, width=5)
        centered(draw, text, cy, fonts["small"], DARK, 220, 4)
        if i > 0:
            draw.line((nodes[i - 1][1] + 135, cy, cx - 140, cy), fill=BLUE, width=5)
            draw.polygon([(cx - 140, cy), (cx - 160, cy - 10), (cx - 160, cy + 10)], fill=BLUE)
    centered(draw, "ER proteostasis = keeping protein folding under control", 555, fonts["small"], MUTED, 1000)


def scene3(draw: ImageDraw.ImageDraw, t: float, _frame: int, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    centered(draw, "The surprise in the stress response", 90, fonts["bold2"], DARK)
    progress = ease((t - 18) / 15)
    draw.rounded_rectangle((100, 155, 610, 510), radius=30, fill=PALE_BLUE, outline=BLUE, width=5)
    draw.rounded_rectangle((670, 155, 1180, 510), radius=30, fill=PALE_ORANGE, outline=AMBER, width=5)
    centered(draw, "KHK present", 220, fonts["bold2"], BLUE, 430)
    centered(draw, "adaptive\nIRE1α / XBP1", 340, fonts["bold2"], DARK, 430)
    if progress > 0.45:
        centered(draw, "KHK knockdown", 220, fonts["bold2"], AMBER, 430)
        centered(draw, "aggregates +\napoptosis signals", 340, fonts["bold2"], DARK, 430)
    draw.rectangle((100, 565, 100 + int(1080 * progress), 585), fill=BLUE)
    centered(draw, "adaptive UPR  →  proteotoxic stress", 625, fonts["small"], MUTED)


def scene4(draw: ImageDraw.ImageDraw, _t: float, _frame: int, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    centered(draw, "Aha moment", 85, fonts["bold2"], BLUE)
    draw.ellipse((250, 180, 650, 520), outline=BLUE, width=6, fill=PALE_BLUE)
    draw.ellipse((630, 180, 1030, 520), outline=GREEN, width=6, fill=PALE_GREEN)
    centered(draw, "metabolism", 305, fonts["bold2"], BLUE, 310)
    centered(draw, "ER\nproteostasis", 305, fonts["bold2"], GREEN, 310)
    draw.rounded_rectangle((540, 270, 740, 380), radius=24, fill=BG, outline=AMBER, width=6)
    centered(draw, "KHK", 325, fonts["bold"], AMBER, 180)
    centered(draw, "KHK connects metabolic flux with stress adaptation", 585, fonts["small"], DARK, 980)


def scene5(draw: ImageDraw.ImageDraw, _t: float, _frame: int, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    centered(draw, "Therapeutic nuance", 95, fonts["bold2"], DARK)
    draw.line((275, 430, 1005, 430), fill=DARK, width=8)
    draw.polygon([(640, 250), (590, 430), (690, 430)], outline=BLUE, fill=PALE_BLUE)
    draw.rounded_rectangle((130, 230, 520, 355), radius=28, fill=PALE_BLUE, outline=BLUE, width=5)
    draw.rounded_rectangle((760, 230, 1150, 355), radius=28, fill=PALE_GREEN, outline=GREEN, width=5)
    centered(draw, "Reduce\nharmful fructose flux", 292, fonts["bold2"], BLUE, 330)
    centered(draw, "Preserve\nER protection", 292, fonts["bold2"], GREEN, 330)
    centered(draw, "blocking flux ≠ deleting KHK", 560, fonts["bold2"], AMBER, 900)


def scene6(draw: ImageDraw.ImageDraw, _t: float, _frame: int, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
    centered(draw, "Blocking flux ≠ deleting KHK", 260, fonts["bold2"], DARK, 1000)
    centered(draw, "Read the open-access article", 345, fonts["small"], MUTED)
    centered(draw, "doi.org/10.1152/ajpgi.00235.2025", 410, fonts["bold2"], BLUE, 1100)
    draw.line((345, 465, 935, 465), fill=AMBER, width=5)


SCENES = [
    (0, 8, scene1),
    (8, 18, scene2),
    (18, 33, scene3),
    (33, 46, scene4),
    (46, 56, scene5),
    (56, 60, scene6),
]


def make_frame(frame: int, sections: list[dict], fonts: dict[str, ImageFont.FreeTypeFont]) -> Image.Image:
    t = frame / FPS
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    draw_background(draw, frame)
    for start, end, scene_fn in SCENES:
        if start <= t < end or (t >= DURATION_SECONDS - 0.001 and end == DURATION_SECONDS):
            scene_fn(draw, t, frame, fonts)
            break
    draw_caption(draw, t, sections, fonts)
    return image


def render(repo_root: Path, output: Path, ffmpeg: str) -> dict:
    checkpoint_path = repo_root / "pipelines/khk-er-proteostasis-paper/checkpoint_script.json"
    script = json.loads(checkpoint_path.read_text())["artifacts"]["script"]
    sections = script["sections"]
    fonts = load_fonts()
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]

    start = time.time()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for frame in range(TOTAL_FRAMES):
        image = make_frame(frame, sections, fonts)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        proc.stdin.write(buffer.getvalue())
    proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    returncode = proc.wait()
    if returncode:
        raise RuntimeError(f"ffmpeg failed with exit code {returncode}\n{stderr[-4000:]}")

    return {
        "output": str(output),
        "size": output.stat().st_size,
        "render_time_seconds": round(time.time() - start, 2),
        "frames": TOTAL_FRAMES,
        "fps": FPS,
        "resolution": f"{W}x{H}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="projects/khk-er-proteostasis-paper/renders/final.mp4")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report = render(repo_root, repo_root / args.output, args.ffmpeg)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
