import json
import os
from typing import Any, Dict, List

from src.app.core.config import (
    DATASOURCE_OUTPUT_FILE,
    LMS_ASSESSMENTS_OUTPUT_FILE,
    RUBRICS_OUTPUT_FILE,
)
from src.app.models.deliverables import (
    AssessmentAnswer,
    AssessmentPayload,
    DataSource,
    DataSourceType,
    ReviewPayload,
    RubricPointEvaluation,
)


def generate_datasource_nodes(
    rubrics_file: str = RUBRICS_OUTPUT_FILE,
    lms_file: str = LMS_ASSESSMENTS_OUTPUT_FILE,
    output_file: str = DATASOURCE_OUTPUT_FILE,) -> List[Dict[str, Any]]:

    datasource_nodes: List[Dict[str, Any]] = []

    if os.path.exists(rubrics_file):
        with open(rubrics_file, "r", encoding="utf-8") as f:
            rubrics = json.load(f)

        for r in rubrics:
            learner_id = r.get("learner_id")
            lx_id = r.get("lx_id")
            attempt_number = r.get("attempt_number", 1)
            timestamp = r.get("timestamp", "2026-08-01T00:00:00Z")

            detailed_rubrics = [
                RubricPointEvaluation(**rp)
                for rp in r.get("detailed_rubric_evaluations", [])
            ]

            review_payload = ReviewPayload(
                lx_id=lx_id,
                task_headline=r.get("task_headline"),
                attempt_number=attempt_number,
                hours_before_deadline=r.get("hours_before_deadline"),
                submission_text=r.get("submission_text", ""),
                assets=r.get("assets", []),
                verdict=r.get("verdict", "passed"),
                feedback_summary=r.get("feedback_summary", ""),
                mentor_reply=r.get("mentor_reply"),
                detailed_rubric_evaluations=detailed_rubrics,
            )

            ds_id = DataSource.generate_deterministic_id(
                learner_id=learner_id,
                lx_id=lx_id,
                timestamp=timestamp,
                source_type="review",
                attempt=attempt_number,
            )

            ds_node = DataSource(
                datasource_id=ds_id,
                datasource_name=DataSourceType.REVIEW,
                timestamp=timestamp,
                learner_id=learner_id,
                payload=review_payload,
            )
            datasource_nodes.append(ds_node.model_dump())

    if os.path.exists(lms_file):
        with open(lms_file, "r", encoding="utf-8") as f:
            lms_list = json.load(f)

        for lms in lms_list:
            learner_id = lms.get("learner_id")
            lx_id = lms.get("lx_id", "lms_assessment")
            timestamp = (
                lms.get("terminated_at")
                or lms.get("activated_at")
                or "2026-08-01T00:00:00Z"
            )

            answers = [
                AssessmentAnswer(
                    question_id=ans.get("question_id", "QA"),
                    domain=ans.get("domain"),
                    metric_key=ans.get("metric_key"),
                    learner_answer=ans.get("learner_answer", ""),
                    score=ans.get("score"),
                    evaluation_notes=ans.get("evaluation_notes"),
                )
                for ans in lms.get("answers", [])
            ]

            assessment_payload = AssessmentPayload(
                lx_id=lx_id,
                assessment_type=lms.get("assessment_type", "pre_course"),
                topic_id=lms.get("topic_id"),
                score=lms.get("score"),
                max_score=lms.get("max_score", 100.0),
                answers=answers,
            )

            ds_id = DataSource.generate_deterministic_id(
                learner_id=learner_id,
                lx_id=lx_id,
                timestamp=timestamp,
                source_type="assesments",
                attempt=1,
            )

            ds_node = DataSource(
                datasource_id=ds_id,
                datasource_name=DataSourceType.ASSESSMENTS,
                timestamp=timestamp,
                learner_id=learner_id,
                payload=assessment_payload,
            )
            datasource_nodes.append(ds_node.model_dump())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(datasource_nodes, f, indent=2, ensure_ascii=False)

    print(
        f"[OK] Generated {len(datasource_nodes)} DataSource nodes and saved to "
        f"'{output_file}'."
    )
    return datasource_nodes


if __name__ == "__main__":
    generate_datasource_nodes()
