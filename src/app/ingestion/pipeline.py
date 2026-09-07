import json
import os
from typing import Any, Dict

from src.app.agents.preprocessing import LMSMemoryCardAgent, MentorMetricAgent
from src.app.core.config import (
    COHORT_GROUPS,
    DATASOURCE_OUTPUT_FILE,
    GROUP_A,
    GROUP_B,
    JSON_DIR,
    LMS_ASSESSMENTS_OUTPUT_FILE,
    MEMORY_CARDS_OUTPUT_FILE,
    PROFILES_OUTPUT_FILE,
    RUBRICS_OUTPUT_FILE,
)
from src.app.ingestion.evidence_payload_generation import generate_datasource_nodes
from src.app.ingestion.learner_profile_extraction import extract_learner_profiles
from src.app.ingestion.lms_assessment_extraction import extract_lms_assessments
from src.app.ingestion.memory_card_extraction import generate_memory_card_nodes
from src.app.ingestion.mentor_rubric_extraction import (
    build_attempt_map,
    build_deadline_map,
    extract_mentor_evaluations,
    extract_rubric_taxonomies,
)


def run_pipeline(run_llm_agents: bool = False) -> Dict[str, Any]:
    """
    Executes the end-to-end extraction and graph node generation pipeline,
    producing all 3 core node datasets:
      - Node 1: json/extracted_learner_profiles.json (LearnerProfile)
      - Node 2: json/graph_datasource_nodes.json (DataSource)
      - Node 3: json/graph_memory_cards.json (MemoryCard)
    """
    os.makedirs(JSON_DIR, exist_ok=True)

    print("\n[Step 1/3] Extracting Learner Profiles (Node 1)...")

    learner_files = [GROUP_A["learners"], GROUP_B["learners"]]
    profiles = extract_learner_profiles(learner_files)
    with open(PROFILES_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    print(f"  -> Successfully generated {len(profiles)} LearnerProfile nodes.")

    print("\n[Step 2/3] Extracting Activity Logs (Reviews & Assessments)...")

    all_evals = []
    mentor_agent = MentorMetricAgent() if run_llm_agents else None
    for grp in COHORT_GROUPS:
        att_map = build_attempt_map(grp["turns"])
        dead_map = build_deadline_map(grp["configs"])
        taxonomies = extract_rubric_taxonomies(grp["configs"])
        metrics_map = (
            mentor_agent.evaluate_mentor_metrics_map(grp["configs"], grp["logs"])
            if mentor_agent
            else {}
        )
        evals = extract_mentor_evaluations(
            grp["logs"],
            att_map,
            taxonomies,
            deadline_map=dead_map,
            metrics_map=metrics_map,
        )
        all_evals.extend(evals)

    with open(RUBRICS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_evals, f, indent=2, ensure_ascii=False)
    print(f"  -> Extracted {len(all_evals)} review evaluations.")

    all_lms = []
    for grp in COHORT_GROUPS:
        cards_map = {}
        if run_llm_agents:
            agent = LMSMemoryCardAgent(grp["catalog"])
            cards_map = agent.generate_memory_cards_map(
                grp["configs"], grp["logs"], cards_per_learner=15
            )

        answers_file = grp.get("answers")
        if answers_file and os.path.exists(answers_file):
            lms_list = extract_lms_assessments(
                grp["configs"],
                cards_map,
                answers_filepath_or_records=answers_file,
            )
        else:
            lms_list = extract_lms_assessments(grp["configs"], cards_map)
        all_lms.extend(lms_list)

    with open(LMS_ASSESSMENTS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_lms, f, indent=2, ensure_ascii=False)
    print(f"  -> Extracted {len(all_lms)} LMS assessments.")

    datasource_nodes = generate_datasource_nodes(
        rubrics_file=RUBRICS_OUTPUT_FILE,
        lms_file=LMS_ASSESSMENTS_OUTPUT_FILE,
        output_file=DATASOURCE_OUTPUT_FILE,
    )
    print(
        f"  -> Successfully generated {len(datasource_nodes)} "
        f"DataSource nodes (Node 2)."
    )

    print("\n[Step 3/3] Extracting MemoryCard Graph Nodes (Node 3)...")

    memory_cards = generate_memory_card_nodes(
        assessments_file=LMS_ASSESSMENTS_OUTPUT_FILE,
        rubrics_file=RUBRICS_OUTPUT_FILE,
        output_file=MEMORY_CARDS_OUTPUT_FILE,
    )

    print(
        f"  -> Successfully generated {len(memory_cards)} "
        f"MemoryCard nodes (Node 3)."
    )

    return {
        "profiles": profiles,
        "datasources": datasource_nodes,
        "memory_cards": memory_cards,
    }


if __name__ == "__main__":
    run_pipeline()
