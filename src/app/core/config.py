import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
JSON_DIR = os.getenv("JSON_DIR", str(BASE_DIR / "json"))

GROUP_A = {
    "name": "Group A (AI Engineer)",
    "learners": os.path.join(DATA_DIR, "group-a-ai-engineer", "learners.jsonl"),
    "configs": os.path.join(DATA_DIR, "group-a-ai-engineer", "lx_configs.jsonl"),
    "turns": os.path.join(DATA_DIR, "group-a-ai-engineer", "lx_turns.jsonl"),
    "logs": os.path.join(DATA_DIR, "group-a-ai-engineer", "interaction_logs.jsonl"),
    "catalog": os.path.join(DATA_DIR, "benchmark_questions_group_a.json"),
    "answers": os.path.join(DATA_DIR, "benchmark_answers_group_a.json"),
}

GROUP_B = {
    "name": "Group B (Product Management)",
    "learners": os.path.join(DATA_DIR, "group-b-product-management", "learners.jsonl"),
    "configs": os.path.join(DATA_DIR, "group-b-product-management", "lx_configs.jsonl"),
    "turns": os.path.join(DATA_DIR, "group-b-product-management", "lx_turns.jsonl"),
    "logs": os.path.join(DATA_DIR, "group-b-product-management", "interaction_logs.jsonl"),
    "catalog": os.path.join(DATA_DIR, "benchmark_questions_group_b.json"),
    "answers": os.path.join(DATA_DIR, "benchmark_answers_group_b.json"),
}

COHORT_GROUPS = [GROUP_A, GROUP_B]

PROFILES_OUTPUT_FILE = os.path.join(JSON_DIR, "extracted_learner_profiles.json")

DATASOURCE_OUTPUT_FILE = os.path.join(JSON_DIR, "graph_datasource_nodes.json")

MEMORY_CARDS_OUTPUT_FILE = os.path.join(JSON_DIR, "graph_memory_cards.json")

RUBRICS_OUTPUT_FILE = os.path.join(JSON_DIR, "extracted_mentor_rubrics.json")
LMS_ASSESSMENTS_OUTPUT_FILE = os.path.join(JSON_DIR, "extracted_lms_assessments.json")

LITE_LLM_KEY = os.getenv("LITE_LLM")
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "https://management.sprints.ai/litellm/v1")

PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gemini/gemini-3.6-flash")
SECONDARY_MODEL = os.getenv("SECONDARY_MODEL", "gemini/gemini-2.5-flash")
TERTIARY_MODEL = os.getenv("TERTIARY_MODEL", "gemini/gemini-3.1-flash-lite")

FALLBACK_CHAIN = [PRIMARY_MODEL, SECONDARY_MODEL, TERTIARY_MODEL]
