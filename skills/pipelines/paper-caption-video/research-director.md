# Paper Caption Video — Research Director

Use this stage to extract a video-ready brief from a `.txt` paper input.

## Process

1. Read the `.txt` input path.
2. Extract the first plausible title line.
3. Prefer abstract/conclusion/results sentences when present.
4. Select 4-6 concise claims or beats for captions.
5. Preserve a limitation note: the extraction is heuristic and must not be treated as peer review.
6. Pass the beats to script/scene planning or to `scripts/render_paper_caption_video.py`.

## Constraints

- Do not invent statistics, methods, organisms, cohorts, or conclusions.
- If the paper text is too short or malformed, produce a transparent video explaining that the input needs more complete paper text.
- Keep captions readable: short sentences, large text, high contrast.
