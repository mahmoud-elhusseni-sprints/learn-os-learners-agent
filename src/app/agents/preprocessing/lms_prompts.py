import json
from typing import Any, Dict, List

from src.app.core import build_taxonomy_prompt_block

LMS_MEMORY_CARD_PROMPT_TEMPLATE = """
You are Agent 1 (LMS Memory Card Generator Agent).
Evaluate learner '{learner_name}' (ID: {learner_id}) based on their work logs
and task submissions.

ALLOWED TAXONOMY TAGS:
{taxonomy_tags}

BENCHMARK QUESTIONS (First 15 domain benchmarks):
{questions_json}

LEARNER EVIDENCE SUMMARY:
Tasks: {task_headlines}
Submission Excerpts: {subs}
Interaction Logs: {logs}

TASK: Evaluate the learner against each benchmark question.
Generate JSON output as an array of exactly {cards_per_learner} memory cards.
For each memory card, choose 1 to 3 relevant tags for 'tags'
STRICLY from the ALLOWED TAXONOMY TAGS list above.

Return ONLY a valid JSON array with format:
[
  {{
    "metric_key": "<benchmark metric_key>",
    "content": "<Evaluation content of how learner met/missed criteria>",
    "rationale": "<Reasoning based on learner code submissions and logs>",
    "tags": ["technical_skills", "problem_solving"]
  }}
]
"""

MENTOR_METRIC_PROMPT_TEMPLATE = """
You are Agent 2 (Mentor Metric Evaluator Agent).
Evaluate learner '{learner_name}' (ID: {learner_id}) across mentor metrics:
1. behavioral_engagement.engagement
2. behavioral_engagement.effort_signals
3. behavioral_engagement.adaptability
4. technical_execution.code_quality

ALLOWED TAXONOMY TAGS:
{taxonomy_tags}

LEARNER EVIDENCE:
Tasks: {tasks}
Submission Excerpts: {subs}
Interaction Logs: {logs}

TASK: Return a JSON object with qualitative assessments (1-5 scale) per metric.
For each metric, also assign 1 to 3 relevant tags for 'tags'
STRICTLY from the ALLOWED TAXONOMY TAGS list above.

{{
  "behavioral_engagement.engagement": {{
    "score": 4.5,
    "notes": "Active participant in sprints.",
    "tags": ["adaptability_learning", "professionalism"]
  }},
  "behavioral_engagement.effort_signals": {{
    "score": 4.0,
    "notes": "Submitted tasks ahead of deadline.",
    "tags": ["time_task_management", "professionalism"]
  }},
  "behavioral_engagement.adaptability": {{
    "score": 4.2,
    "notes": "Incorporated mentor feedback quickly.",
    "tags": ["adaptability_learning"]
  }},
  "technical_execution.code_quality": {{
    "score": 4.0,
    "notes": "Clean modular code structure.",
    "tags": ["technical_skills", "professionalism"]
  }}
}}
"""


def get_lms_memory_card_prompt(
    learner_name: str,
    learner_id: str,
    questions: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    subs: List[str],
    logs: List[str],
    cards_per_learner: int = 15,
) -> str:
    first_q = questions[:cards_per_learner]
    q_str = json.dumps(
        [
            {
                "question_id": q.get("question_id"),
                "metric_key": q.get("metric_key"),
                "question_text": q.get("question_text") or q.get("question"),
                "domain": q.get("domain"),
            }
            for q in first_q
        ],
        indent=2,
    )
    headlines = ", ".join([t.get("headline", "") for t in tasks if t.get("headline")])
    subs_text = " | ".join(subs[:5]) if subs else "No explicit submissions found."
    logs_text = " | ".join(logs[:8]) if logs else "No interaction logs recorded."

    return LMS_MEMORY_CARD_PROMPT_TEMPLATE.format(
        learner_name=learner_name,
        learner_id=learner_id,
        questions_json=q_str,
        task_headlines=headlines,
        subs=subs_text,
        logs=logs_text,
        cards_per_learner=cards_per_learner,
        taxonomy_tags=build_taxonomy_prompt_block(),
    )


def get_mentor_metric_prompt(
    learner_name: str,
    learner_id: str,
    tasks: List[Dict[str, Any]],
    subs: List[str],
    logs: List[str],
) -> str:
    headlines = ", ".join([t.get("headline", "") for t in tasks if t.get("headline")])
    subs_text = " | ".join(subs[:5]) if subs else "No explicit submissions."
    logs_text = " | ".join(logs[:8]) if logs else "No interaction logs."

    return MENTOR_METRIC_PROMPT_TEMPLATE.format(
        learner_name=learner_name,
        learner_id=learner_id,
        tasks=headlines,
        subs=subs_text,
        logs=logs_text,
        taxonomy_tags=build_taxonomy_prompt_block(),
    )
