from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.paper_scout import (  # noqa: E402
    PaperCandidate,
    build_search_queries,
    dedupe_candidates,
    infer_tags,
    normalize_doi,
    normalize_title,
    restore_openalex_abstract,
    screen_candidate,
)


def test_normalizers_handle_punctuation_and_doi_prefixes():
    assert normalize_title("AI-Assisted ASD Screening: A Study!") == "ai assisted asd screening a study"
    assert normalize_doi("https://doi.org/10.1038/Example") == "10.1038/example"


def test_video_candidate_is_tagged_and_included():
    candidate = PaperCandidate(
        title="Machine learning autism screening from home video behavior",
        year=2025,
        abstract=(
            "A machine learning model supports autism spectrum disorder screening "
            "using home video and behavioral observation."
        ),
    )

    assert {"video", "behavior"}.issubset(set(infer_tags(candidate)))
    decision, reason = screen_candidate(candidate)
    assert decision == "include"
    assert "ASD" in reason


def test_candidate_without_ai_or_asd_is_excluded():
    candidate = PaperCandidate(
        title="Speech therapy service preferences",
        year=2024,
        abstract="A survey about service access and caregiver experience.",
    )

    decision, _ = screen_candidate(candidate)
    assert decision == "exclude"


def test_dedupe_candidates_removes_seed_title_and_doi():
    new_candidate = PaperCandidate(title="New ASD speech AI paper", doi="10.1000/new")
    duplicate_title = PaperCandidate(title="Known Paper!", doi="10.1000/other")
    duplicate_doi = PaperCandidate(title="Different title", doi="https://doi.org/10.1000/known")

    result = dedupe_candidates(
        [new_candidate, duplicate_title, duplicate_doi],
        seed_titles={normalize_title("Known Paper")},
        seed_dois={normalize_doi("10.1000/known")},
    )

    assert result == [new_candidate]


def test_tag_specific_query_prioritizes_requested_tag():
    queries = build_search_queries(tags=["video"])

    assert len(queries) == 1
    assert "video" in queries[0]
    assert "autism spectrum disorder" in queries[0]


def test_restore_openalex_abstract_orders_words_by_position():
    abstract = restore_openalex_abstract({"Autism": [0], "screening": [2], "AI": [1]})

    assert abstract == "Autism AI screening"
