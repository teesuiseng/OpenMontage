#!/usr/bin/env python3
"""Render a caption-led paper explainer from a .txt file.

The script stays API-free for GitHub Actions:
- reads a committed text file
- extracts heuristic paper beats
- maps the extracted story into Remotion Explainer props
- renders the MP4 with the existing Remotion composer
- writes an MP4 that the workflow uploads as an artifact
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BLUE = (37, 99, 235)
DARK = (31, 41, 55)
MUTED = (107, 114, 128)
AMBER = (245, 158, 11)
GREEN = (16, 185, 129)
BG = (255, 255, 255)
SURFACE = (249, 250, 251)
PALE_BLUE = (239, 246, 255)
GRID = (245, 247, 250)
BORDER = (229, 231, 235)

KEYWORDS = (
    "we show", "we found", "results", "conclusion", "suggest", "demonstrate",
    "reveals", "associated", "significant", "mechanism", "model", "clinical",
)


def font_path(name: str) -> str:
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/usr/share/fonts/truetype/liberation2/{name}",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"Missing font {name}")


def fonts() -> dict[str, ImageFont.FreeTypeFont]:
    regular = font_path("DejaVuSans.ttf")
    bold = font_path("DejaVuSans-Bold.ttf")
    return {
        "title": ImageFont.truetype(bold, 46),
        "heading": ImageFont.truetype(bold, 38),
        "body": ImageFont.truetype(regular, 31),
        "small": ImageFont.truetype(regular, 23),
        "caption": ImageFont.truetype(bold, 30),
    }


def split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned)
    return [p.strip() for p in parts if 45 <= len(p.strip()) <= 240]


def extract_title(lines: list[str], fallback: str) -> str:
    for line in lines[:25]:
        stripped = line.strip()
        stripped = re.sub(r"^summary\s+of\s+key\s+findings:\s*", "", stripped, flags=re.I)
        lower = stripped.lower().rstrip(":")
        if lower in {"title", "paper title"}:
            continue
        if 12 <= len(stripped) <= 140 and not lower.startswith(("abstract", "introduction", "doi")):
            return stripped
    return fallback


def extract_doi(text: str) -> str | None:
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
    return match.group(0).rstrip(".,;) ") if match else None


def score_sentence(sentence: str, index: int) -> tuple[int, int]:
    lower = sentence.lower()
    keyword_score = sum(1 for keyword in KEYWORDS if keyword in lower)
    section_score = 1 if any(label in lower for label in ("abstract", "result", "conclusion")) else 0
    early_bonus = max(0, 4 - index // 5)
    return (keyword_score * 4 + section_score * 2 + early_bonus, -index)


def extract_beats(text: str, title: str, max_beats: int = 5) -> list[str]:
    sentences = split_sentences(text)
    ranked = sorted(enumerate(sentences), key=lambda item: score_sentence(item[1], item[0]), reverse=True)
    beats: list[str] = []
    seen: set[str] = set()
    for _, sentence in ranked:
        normalized = re.sub(r"\W+", "", sentence.lower())[:80]
        if normalized in seen or title[:30].lower() in sentence.lower():
            continue
        seen.add(normalized)
        beats.append(sentence)
        if len(beats) >= max_beats:
            break
    if len(beats) < 3:
        beats.extend(sentences[: max_beats - len(beats)])
    return beats[:max_beats]


def clean_line(line: str) -> str:
    """Normalize source lines for on-screen captions without losing symbols."""
    cleaned = re.sub(r"^\s*[-*•]\s+", "", line.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def is_section_heading(line: str) -> bool:
    stripped = clean_line(line)
    if not stripped:
        return False
    if re.match(r"^\d+\.\s+\S", stripped):
        return True
    lower = stripped.lower()
    if lower in {
        "title",
        "background",
        "main findings",
        "proposed mechanism",
        "conclusions",
        "significance",
        "limitations",
    }:
        return True
    if (
        8 <= len(stripped) <= 96
        and not re.search(r"[.!?;:]$", stripped)
        and sum(1 for word in stripped.split() if word[:1].isupper() or word.isupper()) >= 2
    ):
        return True
    return False


def extract_structured_sections(lines: list[str]) -> list[dict[str, list[str] | str]]:
    """Extract heading/bullet sections from paper-summary .txt inputs.

    The GitHub Action often receives distilled notes rather than abstract prose.
    Sentence ranking performs poorly on those files because bullets do not always
    end with periods. This section parser preserves the author's outline and
    gives the renderer coherent LinkedIn-style beats.
    """
    sections: list[dict[str, list[str] | str]] = []
    current: dict[str, list[str] | str] | None = None

    for raw_line in lines:
        line = clean_line(raw_line)
        if not line:
            continue
        if is_section_heading(line):
            current = {"heading": re.sub(r"^\d+\.\s+", "", line), "body": []}
            sections.append(current)
            continue
        if current is None:
            current = {"heading": "Overview", "body": []}
            sections.append(current)
        body = current["body"]
        assert isinstance(body, list)
        body.append(line.rstrip(":"))

    return [
        section for section in sections
        if section.get("heading") and (section.get("body") or str(section.get("heading", "")).lower() != "main findings")
    ]


def section_body(section: dict[str, list[str] | str], max_items: int = 3) -> str:
    body = section.get("body", [])
    items = body if isinstance(body, list) else []
    useful = [
        item for item in items
        if item and item.lower() not in {"fructose:", "thr overexpression in fructose:"}
    ]
    return " • ".join(useful[:max_items]).strip()


def fit_caption(text: str, limit: int = 190) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}…"


def title_case_heading(heading: str) -> str:
    heading = re.sub(r"^\d+\.\s+", "", heading).strip()
    heading = heading.replace("THR", "THR").replace("UCP-1", "UCP-1")
    return heading[:1].upper() + heading[1:]


def pick_section(
    sections: list[dict[str, list[str] | str]],
    keywords: tuple[str, ...],
    used: set[int],
) -> tuple[int, dict[str, list[str] | str]] | None:
    best: tuple[int, int, dict[str, list[str] | str]] | None = None
    for index, section in enumerate(sections):
        if index in used:
            continue
        haystack = f"{section.get('heading', '')} {section_body(section, 5)}".lower()
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score and (best is None or score > best[0]):
            best = (score, index, section)
    if best is None:
        return None
    used.add(best[1])
    return best[1], best[2]


def is_heading_like(value: str, keywords: tuple[str, ...]) -> bool:
    haystack = value.lower()
    return any(keyword in haystack for keyword in keywords)


def first_sentence_fragment(text: str, limit: int = 56) -> str:
    fragment = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    fragment = re.sub(r"^\W+", "", fragment)
    return fit_caption(fragment or "Evidence from source text", limit)


def build_linkedin_scenes(lines: list[str], title: str, paper_path: Path) -> list[dict[str, str]]:
    sections = extract_structured_sections(lines)
    used: set[int] = set()

    scenes: list[dict[str, str]] = [
        {
            "kind": "title",
            "heading": "LinkedIn paper brief",
            "body": fit_caption(title, 170),
        }
    ]

    setup_keywords = ("background", "abstract", "introduction", "question", "objective", "purpose")
    takeaway_keywords = (
        "significance",
        "conclusion",
        "implication",
        "takeaway",
        "discussion",
        "relevance",
    )
    container_headings = {"title", "main findings", "findings", "results", "overview"}
    non_finding_headings = {
        "title",
        "background",
        "abstract",
        "introduction",
        "question",
        "objective",
        "purpose",
        "significance",
        "conclusions",
        "conclusion",
        "limitations",
        "discussion",
    }

    setup = pick_section(sections, setup_keywords, used)
    if setup is not None:
        _, section = setup
        body = section_body(section)
        if body:
            scenes.append({"kind": "setup", "heading": "The question", "body": fit_caption(body)})

    takeaway: tuple[int, dict[str, list[str] | str]] | None = pick_section(sections, takeaway_keywords, used)

    finding_candidates: list[tuple[int, dict[str, list[str] | str]]] = []
    for index, section in enumerate(sections):
        if index in used:
            continue
        heading = str(section.get("heading", "")).strip()
        body = section_body(section)
        if not body:
            continue
        lower = heading.lower()
        if lower in container_headings:
            continue
        if lower in non_finding_headings or is_heading_like(lower, setup_keywords + takeaway_keywords):
            continue
        finding_candidates.append((index, section))

    if len(finding_candidates) < 3:
        for index, section in enumerate(sections):
            if index in used or any(candidate_index == index for candidate_index, _ in finding_candidates):
                continue
            heading = str(section.get("heading", "")).strip()
            body = section_body(section)
            if body and heading.lower() not in container_headings:
                finding_candidates.append((index, section))
            if len(finding_candidates) >= 3:
                break

    for index, section in finding_candidates[:3]:
        used.add(index)
        heading = title_case_heading(str(section["heading"]))
        body = section_body(section)
        scenes.append({"kind": "finding", "heading": fit_caption(heading, 56), "body": fit_caption(body)})

    if takeaway is not None:
        _, section = takeaway
        body = section_body(section)
        if body:
            scenes.append({
                "kind": "takeaway",
                "heading": "Why LinkedIn readers should care",
                "body": fit_caption(body),
            })

    beats = extract_beats("\n".join(lines), title, max_beats=6)
    if "setup" not in [scene["kind"] for scene in scenes] and beats:
        scenes.insert(1, {"kind": "setup", "heading": "The question", "body": fit_caption(beats[0])})

    beat_index = 0
    while len([scene for scene in scenes if scene["kind"] == "finding"]) < 3 and beat_index < len(beats):
        beat = beats[beat_index]
        beat_index += 1
        if any(beat[:80] in scene["body"] for scene in scenes):
            continue
        scenes.append({
            "kind": "finding",
            "heading": first_sentence_fragment(beat),
            "body": fit_caption(beat),
        })

    if "takeaway" not in [scene["kind"] for scene in scenes]:
        takeaway_body = beats[-1] if beats else "Use this as a fast paper triage, then verify the full source before posting."
        scenes.append({
            "kind": "takeaway",
            "heading": "Why LinkedIn readers should care",
            "body": fit_caption(takeaway_body),
        })

    scenes.append({
        "kind": "limitations",
        "heading": "Use with caution",
        "body": "Auto-extracted captions are not peer review. Verify the full paper before posting claims.",
    })
    scenes.append({
        "kind": "cta",
        "heading": "Source text",
        "body": paper_path.name,
    })
    return scenes


def build_story(paper_path: Path, duration: int) -> dict:
    text = paper_path.read_text(encoding="utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    title = extract_title(lines, paper_path.stem.replace("-", " ").replace("_", " ").title())
    doi = extract_doi(text)
    scenes = build_linkedin_scenes(lines, title, paper_path)
    if doi:
        scenes[-1]["body"] = f"DOI: {doi}"

    scene_duration = duration / len(scenes)
    for i, scene in enumerate(scenes):
        scene["start"] = round(i * scene_duration, 3)
        scene["end"] = round((i + 1) * scene_duration, 3)

    return {
        "title": title,
        "doi": doi,
        "input_path": paper_path.as_posix(),
        "input_sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
        "duration_seconds": duration,
        "scenes": scenes,
        "limitations": [
            "Heuristic extraction only; not peer review.",
            "Caption-led video has no audio by default.",
            "Generated MP4 is delivered as a GitHub Actions artifact, not committed to git.",
        ],
    }


def validate_linkedin_story(story: dict) -> list[str]:
    """Return editorial gate failures for LinkedIn-facing paper captions."""
    scenes = story.get("scenes", [])
    failures: list[str] = []
    kinds = [scene.get("kind") for scene in scenes]
    headings = [str(scene.get("heading", "")).strip() for scene in scenes]
    bodies = [str(scene.get("body", "")).strip() for scene in scenes]

    if not story.get("title"):
        failures.append("story title is missing")
    if "setup" not in kinds:
        failures.append("missing setup/question scene")
    if kinds.count("finding") < 3:
        failures.append("fewer than three finding scenes")
    if "takeaway" not in kinds:
        failures.append("missing audience relevance/takeaway scene")
    if any(re.fullmatch(r"key point\s+\d+", heading, flags=re.I) for heading in headings):
        failures.append("generic placeholder heading found")
    if any("/home/runner/" in body or body.startswith("Source: /") for body in bodies):
        failures.append("CTA/body exposes an absolute runner path")
    if any(len(heading) > 64 for heading in headings):
        failures.append("at least one heading is too long for a social-video card")
    if any(len(body) > 220 for body in bodies):
        failures.append("at least one body caption is too dense for LinkedIn")

    return failures


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    wrapped: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for word in words:
            trial = f"{line} {word}".strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= width:
                line = trial
            else:
                if line:
                    wrapped.append(line)
                line = word
        if line:
            wrapped.append(line)
    return wrapped


def centered(draw: ImageDraw.ImageDraw, text: str, y: int, font: ImageFont.FreeTypeFont, color: tuple[int, int, int], width: int = 1020) -> None:
    lines = wrap(draw, text, font, width)
    line_height = font.size + 9
    top = y - (len(lines) * line_height) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, top + i * line_height), line, font=font, fill=color)


def background(draw: ImageDraw.ImageDraw, frame: int) -> None:
    draw.rectangle((0, 0, W, H), fill=BG)
    for x in range(0, W, 56):
        draw.line((x, 0, x, H), fill=GRID, width=1)
    for y in range(0, H, 56):
        draw.line((0, y, W, y), fill=GRID, width=1)
    offset = int(18 * (1 + (frame % 120) / 120))
    draw.ellipse((80 + offset, 90, 310 + offset, 320), fill=(236, 244, 255))
    draw.ellipse((950 - offset, 430, 1180 - offset, 660), fill=(235, 252, 246))


def progress_bar(draw: ImageDraw.ImageDraw, progress: float) -> None:
    x0, y0, x1, y1 = 160, 650, 1120, 664
    draw.rounded_rectangle((x0, y0, x1, y1), radius=7, fill=BORDER)
    draw.rounded_rectangle((x0, y0, x0 + int((x1 - x0) * progress), y1), radius=7, fill=BLUE)


def render_scene(draw: ImageDraw.ImageDraw, scene: dict, t: float, frame: int, story: dict, f: dict[str, ImageFont.FreeTypeFont]) -> None:
    background(draw, frame)
    progress_bar(draw, t / story["duration_seconds"])

    color = BLUE if scene["kind"] in {"title", "setup"} else GREEN if scene["kind"] == "finding" else AMBER
    draw.rounded_rectangle((130, 95, 1150, 560), radius=34, fill=SURFACE if scene["kind"] != "limitations" else PALE_BLUE, outline=color, width=5)
    centered(draw, scene["heading"], 175, f["heading"], color, 900)
    centered(draw, scene["body"], 330, f["body"], DARK, 900)
    centered(draw, "paper brief • auto-extracted captions • verify before sharing", 607, f["small"], MUTED, 1000)


def make_frame(frame: int, story: dict, f: dict[str, ImageFont.FreeTypeFont], fps: int) -> Image.Image:
    t = frame / fps
    scene = next((s for s in story["scenes"] if s["start"] <= t < s["end"]), story["scenes"][-1])
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    render_scene(draw, scene, t, frame, story, f)
    return image


def split_comparison_body(body: str) -> tuple[str, str] | None:
    parts = [part.strip() for part in body.split("•") if part.strip()]
    glucose = next((part for part in parts if "glucose" in part.lower()), None)
    fructose = next((part for part in parts if "fructose" in part.lower()), None)
    if glucose and fructose and glucose != fructose:
        return glucose, fructose
    return None


def remotion_cut_for_scene(scene: dict) -> dict:
    base = {
        "id": f"{scene['kind']}-{scene['start']}",
        "source": "",
        "in_seconds": scene["start"],
        "out_seconds": scene["end"],
    }
    kind = scene["kind"]
    heading = scene["heading"]
    body = scene["body"]

    if kind == "title":
        return {
            **base,
            "type": "hero_title",
            "text": body,
            "heroSubtitle": "caption-led research brief",
        }
    if kind == "setup":
        return {
            **base,
            "type": "callout",
            "callout_type": "info",
            "title": heading,
            "text": body,
        }
    if kind == "finding":
        comparison = split_comparison_body(body)
        if comparison:
            return {
                **base,
                "type": "comparison",
                "title": heading,
                "leftLabel": "Glucose condition",
                "leftValue": comparison[0],
                "rightLabel": "Fructose condition",
                "rightValue": comparison[1],
            }
        return {
            **base,
            "type": "callout",
            "callout_type": "tip",
            "title": heading,
            "text": body,
        }
    if kind == "limitations":
        return {
            **base,
            "type": "callout",
            "callout_type": "warning",
            "title": heading,
            "text": body,
        }
    return {
        **base,
        "type": "text_card",
        "text": f"{heading}\n\n{body}",
        "fontSize": 58 if kind == "takeaway" else 52,
    }


def build_remotion_props(story: dict) -> dict:
    return {
        "theme": "clean-professional",
        "cuts": [remotion_cut_for_scene(scene) for scene in story["scenes"]],
        "overlays": [
            {
                "type": "section_title",
                "text": "OpenMontage paper brief",
                "subtitle": "Auto-extracted from committed .txt",
                "in_seconds": 0,
                "out_seconds": story["duration_seconds"],
                "position": "top-left",
                "accentColor": "#2563EB",
            }
        ],
        "captions": [],
        "audio": {},
    }


def render_video(story: dict, output: Path, ffmpeg: str, fps: int) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    repo = Path.cwd()
    composer_dir = repo / "remotion-composer"
    if not composer_dir.exists():
        raise FileNotFoundError(f"Missing Remotion composer directory: {composer_dir}")
    if not (composer_dir / "node_modules").exists():
        raise RuntimeError(
            "Remotion dependencies are not installed. Run `cd remotion-composer && npm ci` before rendering."
        )

    props_path = output.parent.parent / "artifacts" / "remotion-props.json"
    props_path.parent.mkdir(parents=True, exist_ok=True)
    props_path.write_text(json.dumps(build_remotion_props(story), indent=2), encoding="utf-8")

    remotion_bin = composer_dir / "node_modules" / ".bin" / "remotion"
    if not remotion_bin.exists():
        raise FileNotFoundError(f"Missing Remotion CLI: {remotion_bin}")

    cmd = [
        str(remotion_bin),
        "render",
        "src/index.tsx",
        "Explainer",
        str(output),
        f"--props={props_path}",
        "--codec",
        "h264",
        "--overwrite",
    ]
    browser_executable = (
        shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if browser_executable:
        cmd.extend(["--browser-executable", browser_executable])
    start = time.time()
    proc = subprocess.run(cmd, cwd=composer_dir, text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"Remotion render failed with exit code {proc.returncode}\n{(proc.stderr or proc.stdout)[-4000:]}")
    return {
        "path": output.as_posix(),
        "format": "mp4",
        "codec": "h264",
        "renderer": "remotion",
        "composition": "Explainer",
        "props_path": props_path.as_posix(),
        "resolution": "1920x1080",
        "fps": fps,
        "duration_seconds": story["duration_seconds"],
        "file_size_bytes": output.stat().st_size,
        "render_time_seconds": round(time.time() - start, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a caption-led paper video from a .txt input")
    parser.add_argument("--paper", required=True, help="Path to committed .txt paper input")
    parser.add_argument("--project-id", default=None, help="Output project id; defaults to paper filename stem")
    parser.add_argument("--output", default=None, help="Output MP4 path")
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    parser.add_argument("--story-json", default=None, help="Optional path to write extracted story JSON")
    args = parser.parse_args()

    repo = Path.cwd()
    paper = (repo / args.paper).resolve() if not Path(args.paper).is_absolute() else Path(args.paper)
    if paper.suffix.lower() != ".txt":
        raise ValueError(f"Expected a .txt paper input, got {paper}")
    if not paper.exists():
        raise FileNotFoundError(paper)

    project_id = args.project_id or paper.stem.replace("_", "-")
    output = Path(args.output or f"projects/{project_id}/renders/final.mp4")
    if not output.is_absolute():
        output = repo / output
    story = build_story(paper, args.duration_seconds)
    quality_failures = validate_linkedin_story(story)
    if quality_failures:
        raise ValueError(
            "LinkedIn story quality gate failed:\n"
            + "\n".join(f"- {failure}" for failure in quality_failures)
        )
    report = render_video(story, output, args.ffmpeg, args.fps)

    story_path = Path(args.story_json) if args.story_json else output.parent.parent / "artifacts/story.json"
    if not story_path.is_absolute():
        story_path = repo / story_path
    story_path.parent.mkdir(parents=True, exist_ok=True)
    story_path.write_text(json.dumps({"story": story, "render_report": report}, indent=2), encoding="utf-8")
    print(json.dumps({"story_path": story_path.as_posix(), "render_report": report}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
