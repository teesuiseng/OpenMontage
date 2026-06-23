# Paper text inputs

Commit `.txt` paper inputs in this folder, then run the **Render paper caption video** GitHub Actions workflow.

Example path:

```text
paper_inputs/example-paper.txt
```

The workflow input `paper_txt_path` should point to the committed text file.

## First step: create a pipeline-ready `.txt`

If you are starting from a paper, abstract, or notes, use [`PAPER_TXT_PROMPT.md`](PAPER_TXT_PROMPT.md) to convert the source into the short structured `.txt` format that the renderer expects.


## GitHub workflow

1. Commit or upload a `.txt` paper into `paper_inputs/`.
2. Open the repository **Actions** tab.
3. Select **Render paper caption video**.
4. Run the workflow with `paper_txt_path` set to your `.txt` file.
5. Download the artifact named `paper-caption-video-<project_id>`.

## Why commit `.txt`, not `.mp4`?

Text files are reviewable in PRs. Generated MP4 files are binary artifacts and can trigger Codex/GitHub errors such as **"Binary files are not supported"**. The workflow renders the MP4 on GitHub and uploads it as a downloadable artifact instead.
