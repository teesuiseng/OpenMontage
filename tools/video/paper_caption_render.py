"""OpenMontage tool wrapper for caption-led paper video rendering.

This tool keeps the GitHub Actions artifact workflow, but exposes the renderer
through the standard BaseTool contract so agents and the registry can discover
and call it like other OpenMontage capabilities.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ResumeSupport,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)


class PaperCaptionRender(BaseTool):
    name = "paper_caption_render"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "video_post"
    provider = "openmontage"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    # ffmpeg may be provided by GitHub Actions, system PATH, or an explicit
    # ffmpeg_path input. Keep it out of static dependencies so discovery still
    # works in Codex containers that only have bundled renderer binaries.
    dependencies = ["python:PIL", "cmd:npx", "node:remotion-composer"]
    install_instructions = "Install Pillow, FFmpeg, Node.js/npm, and Remotion dependencies. On GitHub Actions: apt-get install ffmpeg; pip install pillow; cd remotion-composer && npm ci."

    capabilities = [
        "paper_txt_to_caption_video",
        "github_actions_artifact_render",
        "caption_led_video",
        "remotion_render",
    ]
    best_for = [
        "Committed .txt paper inputs that need a lightweight caption-led MP4 artifact",
        "GitHub/Codex environments where binary MP4 PR diffs are unsupported",
    ]
    not_good_for = [
        "Scientifically verified paper summarization",
        "Narrated videos with TTS/audio",
        "High-end motion graphics or provider-generated visuals",
    ]
    supports = {
        "input_extensions": [".txt"],
        "output_format": "mp4",
        "renderer": "remotion",
        "delivery": "GitHub Actions artifact or local project render",
        "commits_binary_video": False,
    }
    resource_profile = ResourceProfile(cpu_cores=2, ram_mb=1024, disk_mb=500, network_required=False)
    resume_support = ResumeSupport.FROM_START
    side_effects = ["writes MP4 output", "writes story JSON artifact"]
    user_visible_verification = ["ffprobe output", "ToolResult success", "artifact paths"]

    input_schema = {
        "type": "object",
        "required": ["paper_path", "output_path"],
        "properties": {
            "paper_path": {"type": "string", "description": "Path to committed .txt paper input"},
            "output_path": {"type": "string", "description": "Where to write final.mp4"},
            "project_id": {"type": "string", "description": "Project/output id"},
            "duration_seconds": {"type": "integer", "default": 60, "minimum": 2},
            "fps": {"type": "integer", "default": 30, "minimum": 1},
            "story_json_path": {"type": "string", "description": "Optional JSON output path for extracted story/render report"},
            "ffmpeg_path": {"type": "string", "description": "Optional explicit FFmpeg binary path"},
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "required": ["output_path", "story_json_path", "render_report"],
        "properties": {
            "output_path": {"type": "string"},
            "story_json_path": {"type": "string"},
            "render_report": {"type": "object"},
        },
    }

    def execute(self, input_data: dict[str, Any]) -> ToolResult:
        start = time.time()
        repo_root = Path(__file__).resolve().parents[2]
        paper_path = Path(input_data["paper_path"])
        if not paper_path.is_absolute():
            paper_path = repo_root / paper_path
        output_path = Path(input_data["output_path"])
        if not output_path.is_absolute():
            output_path = repo_root / output_path

        project_id = input_data.get("project_id") or paper_path.stem.replace("_", "-")
        story_json_path = Path(
            input_data.get("story_json_path")
            or output_path.parent.parent / "artifacts" / "story.json"
        )
        if not story_json_path.is_absolute():
            story_json_path = repo_root / story_json_path

        ffmpeg_path = input_data.get("ffmpeg_path") or shutil.which("ffmpeg")
        if not ffmpeg_path:
            return ToolResult(
                success=False,
                error="FFmpeg not found. Provide ffmpeg_path or install ffmpeg.",
                duration_seconds=time.time() - start,
            )

        script_path = repo_root / "scripts" / "render_paper_caption_video.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--paper",
            str(paper_path),
            "--project-id",
            str(project_id),
            "--duration-seconds",
            str(input_data.get("duration_seconds", 60)),
            "--fps",
            str(input_data.get("fps", 30)),
            "--output",
            str(output_path),
            "--story-json",
            str(story_json_path),
            "--ffmpeg",
            str(ffmpeg_path),
        ]

        proc = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True)
        if proc.returncode != 0:
            return ToolResult(
                success=False,
                error=(proc.stderr or proc.stdout)[-4000:],
                duration_seconds=time.time() - start,
            )

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"stdout": proc.stdout}

        render_report = payload.get("render_report", {}) if isinstance(payload, dict) else {}
        data = {
            "output_path": str(output_path),
            "story_json_path": str(story_json_path),
            "render_report": render_report,
            "stdout": proc.stdout,
        }
        artifacts = [str(output_path), str(story_json_path)]
        return ToolResult(
            success=True,
            data=data,
            artifacts=artifacts,
            duration_seconds=time.time() - start,
        )
