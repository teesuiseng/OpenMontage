# KHK ER Proteostasis Paper Project

This folder contains pipeline checkpoint JSON files only. It does **not** contain the binary MP4.

## Where the video is on GitHub

The video is produced by GitHub Actions:

1. Open the repository's **Actions** tab.
2. Select the **Render KHK video** workflow.
3. Open the latest successful run.
4. Download the artifact named **`khk-er-proteostasis-paper-final-video`**.
5. Unzip it and open `final.mp4`.

This avoids committing an MP4 binary directly to the pull request, which can trigger the Codex/GitHub **"Binary files are not supported"** error.

## Manual render path

If you render the project in a checkout, the MP4 is written to:

```text
projects/khk-er-proteostasis-paper/renders/final.mp4
```

## What this folder contains

`pipelines/khk-er-proteostasis-paper/` stores production state:

- script checkpoint
- scene plan checkpoint
- asset manifest checkpoint
- edit checkpoint
- compose/render checkpoint
- decision log
