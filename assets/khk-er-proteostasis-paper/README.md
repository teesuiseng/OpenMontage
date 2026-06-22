# KHK ER Proteostasis Paper Video

The MP4 is **not committed as a binary file** because the Codex/GitHub PR flow cannot apply binary MP4 diffs reliably.

Instead, GitHub can render and store the video as a downloadable **Actions artifact**.

## Download the video from GitHub

1. Open the repository's **Actions** tab.
2. Select the **Render KHK video** workflow.
3. Open the latest successful run.
4. Download the artifact named **`khk-er-proteostasis-paper-final-video`**.
5. Unzip the artifact and open `final.mp4`.

## Render it manually from the repository

```bash
python -m pip install pillow
python scripts/render_khk_video.py --output projects/khk-er-proteostasis-paper/renders/final.mp4
```

The manual render writes the MP4 to:

```text
projects/khk-er-proteostasis-paper/renders/final.mp4
```

## Video details

- Format: MP4
- Codec: H.264
- Resolution: 1280×720
- Frame rate: 30 fps
- Duration: 60 seconds
- Audio: none — caption-led version

## Why there is no committed `final.mp4`

GitHub/Codex may show an error such as **"Binary files are not supported"** when a PR includes an MP4. To keep the PR mergeable while still making the video available on GitHub, the video is produced by the **Render KHK video** GitHub Actions workflow and uploaded as an artifact.
