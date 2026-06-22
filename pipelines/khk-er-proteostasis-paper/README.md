# KHK ER Proteostasis Paper Project

This folder contains pipeline checkpoint JSON files only. It does **not** contain the binary MP4.

## Final video location

The rendered video is a generated local artifact at:

```text
projects/khk-er-proteostasis-paper/renders/final.mp4
```

A local convenience copy may also exist at:

```text
assets/khk-er-proteostasis-paper/final.mp4
```

The `assets/.../final.mp4` convenience copy is intentionally gitignored because Codex/GitHub PR creation can fail when an MP4 binary is included in the diff.

## What this folder contains

`pipelines/khk-er-proteostasis-paper/` stores production state:

- script checkpoint
- scene plan checkpoint
- asset manifest checkpoint
- edit checkpoint
- compose/render checkpoint
- decision log

## Why GitHub may say "Binary files are not supported"

That message appears when a Pull Request tries to include or display an MP4 binary. The fix is to avoid committing the MP4 and keep the video as a generated local artifact.
