# Prompt for creating paper `.txt` inputs

Use this prompt as the first step before running the **Render paper caption video** GitHub Actions workflow. Paste a paper, abstract, preprint summary, or paper notes after the prompt, then save the model's plain-text output as a committed `.txt` file under `paper_inputs/`.

```text
Convert the paper below into a plain .txt file optimized for a 60-second scientific caption video.

Output ONLY the .txt content. No markdown fences, no explanations.

Use this exact structure:

Title
[Short, strong title]

Background
[Scientific context in 1 short sentence.]
[Why it matters in 1 short sentence.]

Main Findings

[Finding heading]
[Evidence line 1]
[Evidence line 2]
[Evidence line 3]

[Finding heading, preferably framed as a comparison if the paper clearly supports one]
[Condition A or evidence line 1]
[Condition B or evidence line 2]
[Interpretation: cautious takeaway]

[Mechanism or explanatory finding heading]
[Mechanistic evidence line 1, if available]
[Mechanistic evidence line 2, if available]
[Mechanistic interpretation, or state that the mechanism remains uncertain]

Proposed Mechanism
[Proposed mechanism in 1 sentence.]
[Uncertainty/caveat in 1 sentence.]

Conclusions
[Main conclusion.]
[Safest interpretation.]

Significance
[Why a scientific/professional audience should care.]
[Broader disease, translational, or field implication.]

Limitations
[Key limitation.]
[Do-not-overclaim warning.]

Rules:

Plain text only.
Keep every line short and video-card friendly.
Prefer 3 strong findings, not a full paper summary.
Use cautious scientific language.
Do not invent details.
If there is a clear comparison, make finding 2 use two condition-labeled lines.
If there is no clear comparison, do not force one.
If the mechanism is unclear, say so rather than inventing one.
Do not mention the video pipeline in the .txt output.

Paper:
[paste the paper, abstract, or notes here]
```
