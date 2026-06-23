from pathlib import Path

from scripts.render_paper_caption_video import build_story, validate_linkedin_story


def write_paper(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def assert_story_passes(path: Path) -> dict:
    story = build_story(path, 60)
    assert validate_linkedin_story(story) == []
    assert sum(scene["kind"] == "finding" for scene in story["scenes"]) >= 3
    assert all(not scene["heading"].lower().startswith("key point") for scene in story["scenes"])
    return story


def test_khk_structured_outline_passes_quality_gate() -> None:
    story = assert_story_passes(Path("paper_inputs/KHK_ER.txt"))
    assert story["title"].startswith("Ketohexokinase Protects")
    headings = [scene["heading"] for scene in story["scenes"]]
    assert "KHK Loss Shifts ER Stress from Adaptive to Apoptotic" in headings


def test_arbitrary_structured_topic_passes_quality_gate(tmp_path: Path) -> None:
    paper = write_paper(
        tmp_path,
        "quantum-batteries.txt",
        """
        Title
        Quantum Batteries Improve Energy Storage in Molecular Devices

        Background
        Molecular devices lose useful charge during storage, limiting practical deployment in small autonomous sensors.

        Main Findings

        Coherent Charging Increases Stored Work
        The authors observed faster charging when molecular units were coupled through a shared resonant cavity.
        The effect persisted across multiple simulated device sizes and noise assumptions.

        Disorder Changes the Optimal Protocol
        Random variation in molecular energy levels reduced the benefit of simultaneous charging.
        Adaptive pulse schedules recovered part of the lost performance.

        Thermal Leakage Defines the Practical Limit
        Higher temperature increased leakage during the storage interval.
        The best designs balanced rapid charging against slower post-charge dissipation.

        Significance
        The results suggest that quantum battery advantages depend on device architecture, control strategy, and thermal environment.
        """,
    )
    story = assert_story_passes(paper)
    headings = [scene["heading"] for scene in story["scenes"]]
    assert "Coherent Charging Increases Stored Work" in headings
    assert "Disorder Changes the Optimal Protocol" in headings
    assert "Thermal Leakage Defines the Practical Limit" in headings


def test_plain_abstract_without_sections_degrades_to_generic_story(tmp_path: Path) -> None:
    paper = write_paper(
        tmp_path,
        "plain-abstract.txt",
        """
        Microbial pigments improve crop resilience under drought
        We show that engineered microbial pigments increased seedling survival during water limitation in greenhouse trials.
        Results demonstrate that treated plants retained more chlorophyll after repeated dry cycles compared with untreated controls.
        The model suggests pigment-mediated light filtering reduced oxidative stress in leaf tissue.
        Field validation remains necessary because greenhouse conditions do not capture soil complexity or weather variation.
        These findings suggest a low-cost route for improving drought tolerance, but agronomic safety should be verified before broad deployment.
        """,
    )
    story = assert_story_passes(paper)
    assert story["scenes"][0]["body"].startswith("Microbial pigments")
