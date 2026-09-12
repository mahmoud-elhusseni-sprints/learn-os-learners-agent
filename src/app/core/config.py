from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

NEO4J_MAX_CONNECTION_POOL_SIZE = int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "100"))
NEO4J_CONNECTION_ACQUISITION_TIMEOUT = float(
    os.getenv("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", "60.0")
)

GRAPH_LOADER_BATCH_SIZE = int(os.getenv("GRAPH_LOADER_BATCH_SIZE", "1000"))

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
    "logs": os.path.join(
        DATA_DIR, "group-b-product-management", "interaction_logs.jsonl"
    ),
    "catalog": os.path.join(DATA_DIR, "benchmark_questions_group_b.json"),
    "answers": os.path.join(DATA_DIR, "benchmark_answers_group_b.json"),
}

COHORT_GROUPS = [GROUP_A, GROUP_B]

PROFILES_OUTPUT_FILE = os.path.join(JSON_DIR, "extracted_learner_profiles.json")
DATASOURCE_OUTPUT_FILE = os.path.join(JSON_DIR, "graph_datasource_nodes.json")
MEMORY_CARDS_OUTPUT_FILE = os.path.join(JSON_DIR, "graph_memory_cards.json")
RUBRICS_OUTPUT_FILE = os.path.join(JSON_DIR, "extracted_mentor_rubrics.json")
LMS_ASSESSMENTS_OUTPUT_FILE = os.path.join(JSON_DIR, "extracted_lms_assessments.json")

LITE_LLM_KEY = os.getenv("AI_API_KEY")
LITELLM_BASE_URL = os.getenv("AI_AGENT_URL")

PRIMARY_MODEL = os.getenv("PRIMARY_MODEL")
SECONDARY_MODEL = os.getenv("SECONDARY_MODEL")
TERTIARY_MODEL = os.getenv("TERTIARY_MODEL")
AI_MODEL = os.getenv("AI_MODEL")

FALLBACK_CHAIN = [PRIMARY_MODEL, SECONDARY_MODEL, TERTIARY_MODEL]

settings = SimpleNamespace(
    neo4j_uri=NEO4J_URI,
    neo4j_username=NEO4J_USERNAME,
    neo4j_password=NEO4J_PASSWORD,
    neo4j_max_connection_pool_size=NEO4J_MAX_CONNECTION_POOL_SIZE,
    neo4j_connection_acquisition_timeout=NEO4J_CONNECTION_ACQUISITION_TIMEOUT,
)
