import pytest

from src.app.services.learner_context import resolve_context

LEARNERS = [
    {"learner_id": "L001", "name": "Ahmed"},
    {"learner_id": "L002", "name": "Sara"},
]


@pytest.mark.parametrize(
    "query", ["Sara's skills?", "tell me about SARA", "L002 skills"]
)
def test_explicit_identity_switch(query):
    result = resolve_context(query, "L001", LEARNERS)
    assert result.active == result.saved == "L002"


@pytest.mark.parametrize(
    "query",
    ["Compare Ahmed and Sara", "Ahmed and Sara skills", "Compare him with Sara"],
)
def test_multi_learner_preserves_default(query):
    result = resolve_context(query, "L001", LEARNERS)
    assert result.saved == "L001"
    assert result.preserve_default


def test_duplicate_name_is_not_a_comparison():
    result = resolve_context(
        "Sara skills", "L001", LEARNERS + [{"learner_id": "L003", "name": "Sara"}]
    )
    assert result.clarification
    assert result.saved == "L001"


def test_whole_names_and_longest_match():
    assert resolve_context("Saratoga", "L001", LEARNERS).saved == "L001"
    result = resolve_context(
        "Sara Ali skills",
        "L001",
        LEARNERS + [{"learner_id": "L003", "name": "Sara Ali"}],
    )
    assert result.saved == "L003"


def test_no_default_ambiguous_pronoun():
    assert resolve_context("What are his skills?", None, LEARNERS).clarification
    assert (
        resolve_context("Find learners with Python", None, LEARNERS).clarification
        is None
    )
