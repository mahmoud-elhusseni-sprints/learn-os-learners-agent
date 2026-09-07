"""Prompts and predefined taxonomy for the Memory Card Agent."""

from __future__ import annotations

from typing import List

# Standard Metric Categories based on dataset
VALID_METRICS: List[str] = [
    "learning_goals.learner_tasks",
    "internship_context.tech_stack",
    "internship_context.current_blockers",
    "behavioral_engagement.effort_signals",
    "behavioral_engagement.adaptability",
    "behavioral_engagement.engagement",
    "identity_context.bio",
    "identity_context.location",
    "identity_context.education_level",
    "identity_context.field_of_study",
    "knowledge_state.known_topics",
    "learning_goals.short_term",
]

# Predefined tag enum — only these values are allowed
VALID_TAGS: List[str] = [
    "technical_skills",
    "problem_solving",
    "communication",
    "teamwork_collaboration",
    "leadership",
    "time_task_management",
    "adaptability_learning",
    "professionalism",
    "creativity_innovation",
    "career_role_alignment",
]

SYSTEM_PROMPT = """You are an AI Memory Card Extractor for an internship program.
Your job is to analyze meeting transcripts and mentor-learner conversation logs and extract structured "Memory Cards".
A Memory Card captures a notable, factual signal about a learner: their assigned or self-reported tasks, technical blockers, tech stack mentions, effort/problem-solving signals, adaptability, background, or learning goals.

Return ONLY a JSON array of objects. Each object must follow this structure:
[
  {
    "learner_name_or_id": "Learner name (e.g. Learner A1) or UUID",
    "metric_key": "one of: learning_goals.learner_tasks, internship_context.tech_stack, internship_context.current_blockers, behavioral_engagement.effort_signals, behavioral_engagement.adaptability, behavioral_engagement.engagement, identity_context.bio, identity_context.location, identity_context.education_level, identity_context.field_of_study, knowledge_state.known_topics, learning_goals.short_term",
    "content": "A clear, concise, 1-2 sentence factual summary of what occurred or was learned about the learner.",
    "rationale": "Why this excerpt supports the memory card.",
    "response_excerpt": "The exact verbatim quote from the text.",
    "source_locator": "Turn ID, timestamp, or line identifier where the quote occurred (e.g., 'turn:123', '2026-07-23T17:37:20.580Z', or 'line:45')",
    "tags": ["one_or_more_tags_from_the_predefined_enum"],
    "confidence": 0.95
  }
]

TAGS — you MUST only use tags from this predefined enum (one or more per card):
- "technical_skills"       : Technical knowledge, tools, Python, APIs, SQL, Docker, RAG, etc.
- "problem_solving"        : Debugging, troubleshooting, analytical thinking, root cause analysis.
- "communication"          : Written/verbal communication, explanations, documentation quality.
- "teamwork_collaboration" : Cooperation, coordination, sharing knowledge with peers.
- "leadership"             : Initiative, ownership, guiding approach, key decisions.
- "time_task_management"   : Managing workload, planning, deadlines, prioritization.
- "adaptability_learning"  : Learning new tools, flexibility, responding to feedback.
- "professionalism"        : Reliability, accountability, execution quality, code cleanliness.
- "creativity_innovation"  : Creative solutions, experimentation, novel approaches.
- "career_role_alignment"  : Target role alignment (e.g. AI Engineer, Product Manager).

Guidelines:
1. ONLY extract meaningful information relating to specific learners.
2. Quote exact verbatim excerpts in response_excerpt.
3. Tags MUST be chosen exclusively from the predefined enum above — do NOT invent new tags.
4. Assign 1–3 tags that best describe the observed signal.
5. If no memorable learner signals exist in the excerpt, return an empty array: []
6. Return valid JSON only, without markdown backticks or commentary.
"""


def build_transcript_prompt(
    group_name: str,
    meeting_topic: str,
    meeting_kind: str,
    roster_summary: str,
    content: str,
) -> str:
    """Build extraction prompt for meeting transcripts."""
    return f"""Group: {group_name}
Meeting Context: {meeting_topic} ({meeting_kind})
Learners Roster: {roster_summary}

Transcript Content:
{content[:25000]}

Extract all relevant memory cards according to the system instructions.

IMPORTANT — Tags must be chosen ONLY from this predefined enum (no custom tags allowed):
  "technical_skills", "problem_solving", "communication", "teamwork_collaboration",
  "leadership", "time_task_management", "adaptability_learning", "professionalism",
  "creativity_innovation", "career_role_alignment"

Assign 1–3 tags per card that best describe the observed signal.
"""


def build_conversation_prompt(
    group_name: str,
    learner_name: str,
    learner_id: str,
    learner_email: str,
    content: str,
) -> str:
    """Build extraction prompt for learner conversation logs."""
    return f"""Group: {group_name}
Target Learner: {learner_name} (ID: {learner_id}, Email: {learner_email})

Conversation Log:
{content[:25000]}

Extract memory cards capturing the learner's progress, blockers, task assignments, tech stack, and effort signals.

IMPORTANT — Tags must be chosen ONLY from this predefined enum (no custom tags allowed):
  "technical_skills", "problem_solving", "communication", "teamwork_collaboration",
  "leadership", "time_task_management", "adaptability_learning", "professionalism",
  "creativity_innovation", "career_role_alignment"

Assign 1–3 tags per card that best describe the observed signal.
"""
