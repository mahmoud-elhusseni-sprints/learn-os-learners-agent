from unittest.mock import patch

from src.app.agents.talent_intelligence import tools


def test_compare_learners_returns_side_by_side_coverage():
    profiles = {
        "learner-a": {"learner_id": "learner-a", "name": "Learner A"},
        "learner-b": {"learner_id": "learner-b", "name": "Learner B"},
    }

    def find(query):
        return profiles.get(query)

    with (
        patch.object(tools, "_find_learner", side_effect=find),
        patch.object(
            tools,
            "get_learner_profile",
            side_effect=lambda learner_id: tools.ToolResult(
                "ok",
                {
                    "evidence_coverage": {
                        "evidence_count": 2 if learner_id == "learner-a" else 1
                    }
                },
                "",
            ),
        ),
        patch.object(
            tools,
            "search_evidence",
            side_effect=lambda learner_id, query="", limit=20: tools.ToolResult(
                "ok", [{"evidence_id": learner_id, "focus": query}], ""
            ),
        ),
    ):
        result = tools.compare_learners("learner-a", "learner-b", "python")

    assert result.status == "ok"
    assert result.data["focus"] == "python"
    assert [item["name"] for item in result.data["learners"]] == [
        "Learner A",
        "Learner B",
    ]
    assert result.data["learners"][0]["evidence_coverage"]["evidence_count"] == 2
    assert "not a proficiency score" in result.data["limitations"][0]


def test_compare_learners_rejects_unknown_learner():
    with patch.object(tools, "_find_learner", return_value=None):
        result = tools.compare_learners("Learner A", "Learner B")

    assert result.status == "not_found"
    assert result.data == []
