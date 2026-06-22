# KHK ER Proteostasis Paper Video

The final video is a generated binary artifact and is **not committed to Git** because the Codex/GitHub PR flow cannot apply binary MP4 diffs reliably.

## Local video path

After rendering, the video exists locally at:

```text
projects/khk-er-proteostasis-paper/renders/final.mp4
```

A convenience copy may also exist locally at:

```text
assets/khk-er-proteostasis-paper/final.mp4
```

That convenience copy is gitignored on purpose so it does not block PR creation.

## Video details

- Format: MP4
- Codec: H.264
- Resolution: 1280×720
- Frame rate: 30 fps
- Duration: 60 seconds
- Audio: none — caption-led version

## Why there is no committed `final.mp4`

GitHub/Codex may show an error such as **"Binary files are not supported"** when a PR includes an MP4. To keep the PR mergeable, this repository stores the pipeline state and render metadata as text files, while the MP4 remains a generated local artifact.
