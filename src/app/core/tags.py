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

def build_taxonomy_prompt_block() -> str:

    lines = [f'- "{tag}": {desc}' for tag, desc in TAXONOMY_TAG_DESCRIPTIONS.items()]
    return "\n".join(lines)
