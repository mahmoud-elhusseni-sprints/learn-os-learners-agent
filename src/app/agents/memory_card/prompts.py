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

SYSTEM_PROMPT = (
    "You are an AI Memory Card Extractor for an internship program.\n"
    "Your job is to analyze meeting transcripts and mentor-learner "
    'conversation logs and extract structured "Memory Cards".\n'
    "A Memory Card captures a notable, factual signal about a learner: "
    "their assigned or self-reported tasks, technical blockers, tech stack "
    "mentions, effort/problem-solving signals, adaptability, background, or "
    "learning goals.\n\n"
    "Return ONLY a JSON array of objects. Each object must follow this "
    "structure:\n"
    "[\n"
    "  {\n"
    '    "learner_name_or_id": "Learner name (e.g. Learner A1) or UUID",\n'
    '    "metric_key": "one of: learning_goals.learner_tasks, '
    "internship_context.tech_stack, internship_context.current_blockers, "
    "behavioral_engagement.effort_signals, behavioral_engagement."
    "adaptability, behavioral_engagement.engagement, identity_context.bio, "
    "identity_context.location, identity_context.education_level, "
    "identity_context.field_of_study, knowledge_state.known_topics, "
    'learning_goals.short_term",\n'
    '    "content": "A clear, concise, 1-2 sentence factual summary of what '
    'occurred or was learned about the learner.",\n'
    '    "rationale": "Why this excerpt supports the memory card.",\n'
    '    "response_excerpt": "The exact verbatim quote from the text.",\n'
    '    "source_locator": "Turn ID, timestamp, or line identifier '
    "where the quote occurred (e.g., 'turn:123', '2026-07-23T17:37:20.580Z', "
    'or "line:45")",\n'
    '    "tags": ["one_or_more_tags_from_the_predefined_enum"],\n'
    '    "confidence": 0.95\n'
    "  }\n"
    "]\n\n"
    "TAGS — you MUST only use tags from this predefined enum (one or more "
    "per card):\n"
    '- "technical_skills"       : Technical knowledge, tools, Python, APIs, '
    "SQL, Docker, RAG, etc.\n"
    '- "problem_solving"        : Debugging, troubleshooting, analytical '
    "thinking, root cause analysis.\n"
    '- "communication"          : Written/verbal communication, explanations, '
    "documentation quality.\n"
    '- "teamwork_collaboration" : Cooperation, coordination, sharing '
    "knowledge with peers.\n"
    '- "leadership"             : Initiative, ownership, guiding approach, '
    "key decisions.\n"
    '- "time_task_management"   : Managing workload, planning, deadlines, '
    "prioritization.\n"
    '- "adaptability_learning"  : Learning new tools, flexibility, '
    "responding to feedback.\n"
    '- "professionalism"        : Reliability, accountability, execution '
    "quality, code cleanliness.\n"
    '- "creativity_innovation"  : Creative solutions, experimentation, novel '
    "approaches.\n"
    '- "career_role_alignment"  : Target role alignment (e.g. AI Engineer, '
    "Product Manager).\n\n"
    "Guidelines:\n"
    "1. ONLY extract meaningful information relating to specific learners.\n"
    "2. Quote exact verbatim excerpts in response_excerpt.\n"
    "3. Tags MUST be chosen exclusively from the predefined enum above — do "
    "NOT invent new tags.\n"
    "4. Assign 1–3 tags that best describe the observed signal.\n"
    "5. If no memorable learner signals exist in the excerpt, return an empty "
    "array: []\n"
    "6. Return valid JSON only, without markdown backticks or commentary.\n"
)


def build_transcript_prompt(
    group_name: str,
    meeting_topic: str,
    meeting_kind: str,
    roster_summary: str,
    content: str,
) -> str:
    """Build extraction prompt for meeting transcripts."""
    return (
        f"Group: {group_name}\n"
        f"Meeting Context: {meeting_topic} ({meeting_kind})\n"
        f"Learners Roster: {roster_summary}\n\n"
        "Transcript Content:\n"
        f"{content[:25000]}\n\n"
        "Extract all relevant memory cards according to the system "
        "instructions.\n\n"
        "IMPORTANT — Tags must be chosen ONLY from this predefined enum "
        "(no custom tags allowed):\n"
        '  "technical_skills", "problem_solving", "communication", '
        '"teamwork_collaboration",\n'
        '  "leadership", "time_task_management", "adaptability_learning", '
        '"professionalism",\n'
        '  "creativity_innovation", "career_role_alignment"\n\n'
        "Assign 1–3 tags per card that best describe the observed signal.\n"
    )


def build_conversation_prompt(
    group_name: str,
    learner_name: str,
    learner_id: str,
    learner_email: str,
    content: str,
) -> str:
    """Build extraction prompt for learner conversation logs."""
    return (
        f"Group: {group_name}\n"
        f"Target Learner: {learner_name} (ID: {learner_id}, Email: "
        f"{learner_email})\n\n"
        "Conversation Log:\n"
        f"{content[:25000]}\n\n"
        "Extract memory cards capturing the learner's progress, blockers, "
        "task assignments, tech stack, and effort signals.\n\n"
        "IMPORTANT — Tags must be chosen ONLY from this predefined enum "
        "(no custom tags allowed):\n"
        '  "technical_skills", "problem_solving", "communication", '
        '"teamwork_collaboration",\n'
        '  "leadership", "time_task_management", "adaptability_learning", '
        '"professionalism",\n'
        '  "creativity_innovation", "career_role_alignment"\n\n'
        "Assign 1–3 tags per card that best describe the observed signal.\n"
    )
