"""
Comprehensive tests for Memory Card Agent and ingestion pipeline.
Validates MemoryCardAgentConfig, tag/metric normalization, GroupContext,
build_card schema conformance, code block formatting, prompt builders,
and transcript / conversation processing.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.app.agents.memory_card import (
    MemoryCardAgent,
    MemoryCardAgentConfig,
    MemoryCardLLMAdapter,
    VALID_METRICS,
    VALID_TAGS,
)
from src.app.agents.memory_card.models import RawExtractedItem
from src.app.ingestion.generate_memory_cards import (
    GroupContext,
    build_card,
    format_as_memory_card_code,
    process_conversation_file,
    process_transcript_file,
)


@pytest.fixture
def mock_group_context(tmp_path: Path) -> GroupContext:
    """Creates a temporary GroupContext with learners, meetings, and existing memory cards."""
    # Create learners.jsonl
    learners_file = tmp_path / "learners.jsonl"
    learner_data = [
        {
            "learner_id": "127c834c-f7ce-4cc7-9a73-c8f93c8648aa",
            "name": "Learner A1",
            "email": "learner-a1@example.invalid",
            "group_id": "group-uuid-1",
            "group_name": "AI Engineer Internship",
            "round_name": "round2",
        },
        {
            "learner_id": "227c834c-f7ce-4cc7-9a73-c8f93c8648bb",
            "name": "Learner A2",
            "email": "learner-a2@example.invalid",
            "group_id": "group-uuid-1",
            "group_name": "AI Engineer Internship",
            "round_name": "round2",
        },
    ]
    learners_file.write_text(
        "\n".join(json.dumps(l) for l in learner_data) + "\n",
        encoding="utf-8",
    )

    # Create meetings.jsonl
    meetings_file = tmp_path / "meetings.jsonl"
    meeting_data = [
        {
            "meeting_id": "meeting-uuid-1",
            "zoom_meeting_id": "81057624277",
            "zoom_meeting_uuid": "zoom-uuid-1",
            "topic": "Sprint Planning",
            "kind": "sprint_planning",
            "starts_at_utc": "2026-07-26T10:00:00Z",
        }
    ]
    meetings_file.write_text(
        "\n".join(json.dumps(m) for m in meeting_data) + "\n",
        encoding="utf-8",
    )

    # Create meeting_memory_cards.jsonl
    cards_file = tmp_path / "meeting_memory_cards.jsonl"
    card_data = [
        {
            "card_id": "existing-card-1",
            "normalized_payload": {"org_id": "custom-org-id-123"},
        }
    ]
    cards_file.write_text(
        "\n".join(json.dumps(c) for c in card_data) + "\n",
        encoding="utf-8",
    )

    return GroupContext(tmp_path)


# --------------------------------------------------------------------------
# MemoryCardAgent Configuration and Core Unit Tests
# --------------------------------------------------------------------------


def test_agent_config_shared_api_key(monkeypatch):
    """Verify MemoryCardAgentConfig uses the same AI_API_KEY and settings as other agents."""
    monkeypatch.setenv("AI_API_KEY", "shared-ai-key-456")
    monkeypatch.setenv("AI_AGENT_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("AI_MODEL", "gpt-4o-mini")

    config = MemoryCardAgentConfig.from_env()
    assert config.api_key == "shared-ai-key-456"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.model_name == "gpt-4o-mini"


def test_agent_tag_normalization():
    agent = MemoryCardAgent()
    raw_tags = [
        "technical_skills",
        "technical-skills",
        "time-task-management",
        "invalid_tag",
        "problem_solving",
    ]
    normalized = agent.normalize_tags(raw_tags)
    assert normalized == ["technical_skills", "time_task_management", "problem_solving"]
    for t in normalized:
        assert t in VALID_TAGS


def test_agent_metric_normalization():
    agent = MemoryCardAgent()
    assert agent.normalize_metric("internship_context.tech_stack") == "internship_context.tech_stack"
    assert agent.normalize_metric("custom.tech_stack") == "internship_context.tech_stack"
    assert agent.normalize_metric("unknown_metric") == "learning_goals.learner_tasks"


def test_agent_prompt_builders():
    agent = MemoryCardAgent()
    t_prompt = agent.build_transcript_prompt(
        group_name="AI Track",
        meeting_topic="Sprint Planning",
        meeting_kind="planning",
        roster_summary="Learner A1 (id1)",
        content="Meeting text",
    )
    assert "Sprint Planning" in t_prompt
    assert "Learner A1 (id1)" in t_prompt

    c_prompt = agent.build_conversation_prompt(
        group_name="AI Track",
        learner_name="Learner A1",
        learner_id="id1",
        learner_email="a1@example.com",
        content="Conversation text",
    )
    assert "Learner A1 (ID: id1, Email: a1@example.com)" in c_prompt


def test_llm_adapter_json_parsing():
    adapter = MemoryCardLLMAdapter(MemoryCardAgentConfig(api_key="test"))
    raw_markdown = "```json\n[{\"content\": \"test1\"}]\n```"
    assert adapter.parse_json_response(raw_markdown) == [{"content": "test1"}]

    raw_wrapped = '{"memory_cards": [{"content": "wrapped_test"}]}'
    assert adapter.parse_json_response(raw_wrapped) == [{"content": "wrapped_test"}]
    assert adapter.parse_json_response("") == []
    assert adapter.parse_json_response("not valid json") == []


def test_raw_extracted_item_model():
    item = RawExtractedItem(
        learner_name_or_id="Learner A1",
        metric_key="learning_goals.learner_tasks",
        content="Sample content",
        tags=["technical_skills"],
    )
    assert item.learner_name_or_id == "Learner A1"
    assert item.tags == ["technical_skills"]


# --------------------------------------------------------------------------
# GroupContext Tests
# --------------------------------------------------------------------------


def test_group_context_loads_roster_and_org_id(mock_group_context: GroupContext):
    assert len(mock_group_context.learners_by_id) == 2
    assert "127c834c-f7ce-4cc7-9a73-c8f93c8648aa" in mock_group_context.learners_by_id
    assert mock_group_context.org_id == "custom-org-id-123"
    assert len(mock_group_context.meetings) == 1


def test_group_context_find_learner(mock_group_context: GroupContext):
    l1 = mock_group_context.find_learner("127c834c-f7ce-4cc7-9a73-c8f93c8648aa")
    assert l1 is not None
    assert l1["name"] == "Learner A1"

    l2 = mock_group_context.find_learner("learner a2")
    assert l2 is not None
    assert l2["learner_id"] == "227c834c-f7ce-4cc7-9a73-c8f93c8648bb"

    l3 = mock_group_context.find_learner("learner-a1@example.invalid")
    assert l3 is not None
    assert l3["name"] == "Learner A1"

    assert mock_group_context.find_learner("Unknown Learner") is None


def test_group_context_find_meeting_by_transcript(
    mock_group_context: GroupContext, tmp_path: Path
):
    t1 = tmp_path / "2026-07-26_sprint_planning_81057624277_transcript.vtt"
    m1 = mock_group_context.find_meeting_by_transcript(t1)
    assert m1 is not None
    assert m1["meeting_id"] == "meeting-uuid-1"

    t2 = tmp_path / "2026-07-26_sprint_planning_transcript.vtt"
    m2 = mock_group_context.find_meeting_by_transcript(t2)
    assert m2 is not None
    assert m2["kind"] == "sprint_planning"

    t3 = tmp_path / "2026-08-01_standup_transcript.vtt"
    assert mock_group_context.find_meeting_by_transcript(t3) is None


# --------------------------------------------------------------------------
# build_card Schema and Tag Validation Tests
# --------------------------------------------------------------------------


def test_build_card_valid_structure(mock_group_context: GroupContext):
    learner = mock_group_context.learners_by_id["127c834c-f7ce-4cc7-9a73-c8f93c8648aa"]
    item = {
        "learner_name_or_id": "Learner A1",
        "metric_key": "learning_goals.learner_tasks",
        "content": "Learner A1 implemented the FastAPI backend authentication service.",
        "rationale": "Learner A1 reported completing the auth task during sprint planning.",
        "response_excerpt": "I finished setting up JWT authentication on FastAPI.",
        "source_locator": "turn:42",
        "tags": ["technical_skills", "problem_solving"],
        "confidence": 0.95,
    }

    card = build_card(
        item=item,
        learner=learner,
        ctx=mock_group_context,
        source_type="meeting_transcript",
        workflow="meeting_memory_cards",
        source_id="zoom-uuid-1",
        project_slug="internship_meetings",
        meeting_meta=mock_group_context.meetings[0],
    )

    expected_id = "zoom-uuid-1:127c834c-f7ce-4cc7-9a73-c8f93c8648aa:turn:42:learning_goals.learner_tasks"
    assert card["card_id"] == expected_id
    assert card["learner_id"] == "127c834c-f7ce-4cc7-9a73-c8f93c8648aa"
    assert card["meeting_id"] == "meeting-uuid-1"
    assert card["metric_key"] == "learning_goals.learner_tasks"
    assert card["delivery_status"] == "pending"
    assert card["round_name"] == "round2"

    payload = card["normalized_payload"]
    assert payload["org_id"] == "custom-org-id-123"
    assert payload["user_id"] == "127c834c-f7ce-4cc7-9a73-c8f93c8648aa"
    assert payload["content"] == item["content"]
    assert payload["rationale"] == item["rationale"]
    assert payload["response_excerpt"] == item["response_excerpt"]
    assert payload["profile_hints"] == ["learning_goals.learner_tasks"]

    metadata = payload["project_metadata"]
    assert metadata["tags"] == ["technical_skills", "problem_solving"]
    assert metadata["card_id"] == expected_id
    assert metadata["group_id"] == mock_group_context.group_id
    assert metadata["meeting_type"] == "sprint_planning"


def test_build_card_tags_enum_validation(mock_group_context: GroupContext):
    learner = mock_group_context.learners_by_id["127c834c-f7ce-4cc7-9a73-c8f93c8648aa"]
    item = {
        "metric_key": "internship_context.tech_stack",
        "content": "Learner is working with Docker and Python.",
        "tags": ["technical_skills", "technical-skills", "invalid_custom_tag", "time-task-management"],
    }

    card = build_card(
        item=item,
        learner=learner,
        ctx=mock_group_context,
        source_type="meeting_transcript",
        workflow="meeting_memory_cards",
        source_id="src-1",
        project_slug="internship_meetings",
    )

    tags = card["normalized_payload"]["project_metadata"]["tags"]
    for t in tags:
        assert t in VALID_TAGS
    assert "invalid_custom_tag" not in tags
    assert "technical_skills" in tags
    assert "time_task_management" in tags
    assert len(tags) == len(set(tags))


def test_build_card_metric_key_normalization(mock_group_context: GroupContext):
    learner = mock_group_context.learners_by_id["127c834c-f7ce-4cc7-9a73-c8f93c8648aa"]
    item = {
        "metric_key": "custom_prefix.tech_stack",
        "content": "Learner uses PyTorch.",
    }

    card = build_card(
        item=item,
        learner=learner,
        ctx=mock_group_context,
        source_type="meeting_transcript",
        workflow="meeting_memory_cards",
        source_id="src-1",
        project_slug="internship_meetings",
    )

    assert card["metric_key"] == "internship_context.tech_stack"
    assert card["metric_key"] in VALID_METRICS


# --------------------------------------------------------------------------
# format_as_memory_card_code Tests
# --------------------------------------------------------------------------


def test_format_as_memory_card_code(mock_group_context: GroupContext):
    learner = mock_group_context.learners_by_id["127c834c-f7ce-4cc7-9a73-c8f93c8648aa"]
    item = {
        "metric_key": "learning_goals.learner_tasks",
        "content": "Learner A1 completed baseline task evaluation.",
        "rationale": "Learner A1 demonstrated task completion.",
        "tags": ["technical_skills", "leadership"],
        "source_locator": "turn:10",
    }
    card = build_card(
        item=item,
        learner=learner,
        ctx=mock_group_context,
        source_type="meeting_transcript",
        workflow="meeting_memory_cards",
        source_id="zoom-1",
        project_slug="internship_meetings",
        meeting_meta=mock_group_context.meetings[0],
    )

    formatted = format_as_memory_card_code([card])

    assert "## 1. MemoryCard" in formatted
    assert f'card_id="{card["card_id"]}",' in formatted
    assert 'meeting_id="meeting-uuid-1",' in formatted
    assert 'metric_key="learning_goals.learner_tasks",' in formatted
    assert 'content=(\n    "Learner A1 completed baseline task evaluation.",\n),' in formatted
    assert 'rationale=(\n    "Learner A1 demonstrated task completion.",\n),' in formatted
    assert 'tags=[\n    "technical_skills",\n    "leadership",\n], # predefined' in formatted


# --------------------------------------------------------------------------
# File Processing and Pipeline Tests (Dry Run & Mocked LLM)
# --------------------------------------------------------------------------


def test_process_transcript_file_dry_run(
    mock_group_context: GroupContext, tmp_path: Path
):
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:05.000
Learner A1: I have built the API service using FastAPI.
"""
    vtt_file = tmp_path / "2026-07-26_sprint_planning_81057624277_transcript.vtt"
    vtt_file.write_text(vtt_content, encoding="utf-8")

    cards = process_transcript_file(
        file_path=vtt_file,
        ctx=mock_group_context,
        dry_run=True,
    )
    assert cards == []


def test_process_conversation_file_dry_run(
    mock_group_context: GroupContext, tmp_path: Path
):
    md_content = """# Learner A1

- Round: **round2**
- Group: **AI Engineer Internship**
- Learner: `learner-a1@example.invalid` (`127c834c-f7ce-4cc7-9a73-c8f93c8648aa`)

## LX `lx-100`
- **learner → mentor:** I deployed the Docker container successfully.
"""
    md_file = tmp_path / "learner-a1-gmail.com.md"
    md_file.write_text(md_content, encoding="utf-8")

    cards = process_conversation_file(
        file_path=md_file,
        ctx=mock_group_context,
        dry_run=True,
    )
    assert cards == []


@patch("src.app.ingestion.generate_memory_cards.call_gemini_llm")
def test_process_transcript_with_mock_llm(
    mock_llm: MagicMock, mock_group_context: GroupContext, tmp_path: Path
):
    mock_llm.return_value = [
        {
            "learner_name_or_id": "Learner A1",
            "metric_key": "internship_context.tech_stack",
            "content": "Learner A1 is using Docker and PostgreSQL.",
            "rationale": "Learner A1 discussed their tech stack during the meeting.",
            "response_excerpt": "We are running PostgreSQL inside Docker.",
            "source_locator": "turn:12",
            "tags": ["technical_skills"],
            "confidence": 0.95,
        }
    ]

    vtt_file = tmp_path / "2026-07-26_sprint_planning_81057624277_transcript.vtt"
    vtt_file.write_text("WEBVTT\n00:01:00.000 --> 00:01:05.000\nLearner A1: We are running PostgreSQL inside Docker.\n", encoding="utf-8")

    cards = process_transcript_file(
        file_path=vtt_file,
        ctx=mock_group_context,
        client_type="mock",
        client=MagicMock(),
        dry_run=False,
    )

    assert len(cards) == 1
    assert cards[0]["learner_id"] == "127c834c-f7ce-4cc7-9a73-c8f93c8648aa"
    assert cards[0]["metric_key"] == "internship_context.tech_stack"
    assert cards[0]["normalized_payload"]["project_metadata"]["tags"] == ["technical_skills"]


@patch("src.app.ingestion.generate_memory_cards.call_gemini_llm")
def test_process_conversation_with_mock_llm(
    mock_llm: MagicMock, mock_group_context: GroupContext, tmp_path: Path
):
    mock_llm.return_value = [
        {
            "learner_name_or_id": "Learner A2",
            "metric_key": "behavioral_engagement.effort_signals",
            "content": "Learner A2 spent the weekend debugging the latency issue.",
            "rationale": "Shows dedication and problem solving effort.",
            "response_excerpt": "I worked through the weekend to resolve the bottleneck.",
            "source_locator": "line:20",
            "tags": ["problem_solving", "professionalism"],
            "confidence": 0.98,
        }
    ]

    md_content = """# Learner A2

- Learner: `learner-a2@example.invalid` (`227c834c-f7ce-4cc7-9a73-c8f93c8648bb`)
## LX `lx-200`
- **learner → mentor:** I worked through the weekend to resolve the bottleneck.
"""
    md_file = tmp_path / "learner-a2-gmail.com.md"
    md_file.write_text(md_content, encoding="utf-8")

    cards = process_conversation_file(
        file_path=md_file,
        ctx=mock_group_context,
        client_type="mock",
        client=MagicMock(),
        dry_run=False,
    )

    assert len(cards) == 1
    assert cards[0]["learner_id"] == "227c834c-f7ce-4cc7-9a73-c8f93c8648bb"
    assert cards[0]["metric_key"] == "behavioral_engagement.effort_signals"
    assert cards[0]["normalized_payload"]["project_metadata"]["tags"] == [
        "problem_solving",
        "professionalism",
    ]


# --------------------------------------------------------------------------
# Idempotency and Deterministic Card ID Generation Tests
# --------------------------------------------------------------------------


def test_deterministic_card_id_and_idempotency(mock_group_context: GroupContext):
    learner = mock_group_context.learners_by_id["127c834c-f7ce-4cc7-9a73-c8f93c8648aa"]
    item = {
        "metric_key": "learning_goals.learner_tasks",
        "content": "Fixed unit test suite.",
        "rationale": "Learner resolved CI issues.",
        "source_locator": "turn:99",
        "tags": ["problem_solving"],
    }

    card_1 = build_card(
        item=item,
        learner=learner,
        ctx=mock_group_context,
        source_type="meeting_transcript",
        workflow="meeting_memory_cards",
        source_id="session-xyz",
        project_slug="internship_meetings",
        created_at_utc="2026-07-26T12:00:00Z",
    )

    card_2 = build_card(
        item=item,
        learner=learner,
        ctx=mock_group_context,
        source_type="meeting_transcript",
        workflow="meeting_memory_cards",
        source_id="session-xyz",
        project_slug="internship_meetings",
        created_at_utc="2026-07-26T12:00:00Z",
    )

    assert card_1["card_id"] == card_2["card_id"]
    assert card_1["card_id"] == "session-xyz:127c834c-f7ce-4cc7-9a73-c8f93c8648aa:turn:99:learning_goals.learner_tasks"
    assert card_1["normalized_payload"]["created_at"] == card_2["normalized_payload"]["created_at"]
