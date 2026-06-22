# Paper Caption Video — Executive Producer

Use this pipeline when the input is a committed `.txt` file containing a scientific paper, preprint, abstract, or paper-like notes and the requested output is a caption-led explainer video.

## Required routing

1. Confirm the `.txt` is committed under `paper_inputs/` or another repository path.
2. Use `pipeline_defs/paper-caption-video.yaml`.
3. Do not commit MP4 binaries. This pipeline delivers video through GitHub Actions artifacts.
4. Prefer the workflow `.github/workflows/render-paper-caption-video.yml` for GitHub users.
5. If rendering locally, run `python scripts/render_paper_caption_video.py --paper <path> --project-id <id>`.

## Known limitations from the KHK project

- Binary MP4 diffs can block Codex/GitHub PR application.
- Remotion may fail in constrained runners if Chrome/Chromium is unavailable or cannot be downloaded.
- Caption-led videos avoid TTS/provider problems but have no narration audio by default.
- Heuristic text extraction is not scientific peer review; claims should be checked by a human before public use.

## Delivery promise

A reproducible, caption-based MP4 generated from paper text, uploaded as a GitHub Actions artifact, with committed text metadata and no committed binary video.
