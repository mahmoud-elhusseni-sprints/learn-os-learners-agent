TAXONOMY_TAG_DESCRIPTIONS: dict[str, str] = {
    "technical_skills": "Technical knowledge, tools",
    "problem_solving": "Debugging, troubleshooting, analytical thinking.",
    "communication": "Written/verbal communication, explanations, documentation.",
    "teamwork_collaboration": "Cooperation, coordination, sharing knowledge.",
    "leadership": "Initiative, ownership, guiding approach, key decisions.",
    "time_task_management": "Managing workload, planning, deadlines, prioritization.",
    "adaptability_learning": "Learning new tools, flexibility, feedback response.",
    "professionalism": "Reliability, accountability, execution, code cleanliness.",
    "creativity_innovation": "Creative solutions, experimentation, novel ideas.",
    "career_role_alignment": "Target role alignment (AI Engineer, Product Manager).",
}

ALLOWED_TAXONOMY_TAGS: list[str] = list(TAXONOMY_TAG_DESCRIPTIONS.keys())
ALLOWED_TAXONOMY_SET: set[str] = set(TAXONOMY_TAG_DESCRIPTIONS.keys())

METRIC_KEYS: tuple[str, ...] = (
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
)

BEHAVIOR_METRIC_TAG_MAP: dict[str, list[str]] = {
    "behavioral_engagement.engagement": ["adaptability_learning", "professionalism"],
    "behavioral_engagement.effort_signals": ["time_task_management", "professionalism"],
    "behavioral_engagement.adaptability": ["adaptability_learning"],
    "technical_execution.code_quality": ["technical_skills", "professionalism"],
}

BEHAVIOR_METRICS: set[str] = {
    "behavioral_engagement.engagement",
    "behavioral_engagement.effort_signals",
    "behavioral_engagement.adaptability",
}

OUTCOME_TAGS: set[str] = {
    "learner_submission",
    "feedback_delivered",
    "grader_call",
    "attempt_passed",
    "task_closed",
    "lx_ended_success",
}


def build_taxonomy_prompt_block() -> str:

    lines = [f'- "{tag}": {desc}' for tag, desc in TAXONOMY_TAG_DESCRIPTIONS.items()]
    return "\n".join(lines)
