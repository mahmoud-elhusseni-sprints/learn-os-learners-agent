"""Run every public talent-intelligence tool and write JSON evidence."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "json" / "talent_tools_test_report.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.agents.talent_intelligence import tools  # noqa: E402
from src.app.graph.connections import close_driver, get_driver  # noqa: E402


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _evidence_ids(data: Any) -> list[Any]:
    if isinstance(data, list):
        return [
            item.get("evidence_id", item.get("event_id"))
            for item in data
            if isinstance(item, dict)
        ]
    if isinstance(data, dict):
        ids: list[Any] = []
        for value in data.values():
            ids.extend(_evidence_ids(value))
        return ids
    return []


def _summary(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        return {
            "type": "list",
            "count": len(data),
            "first_item": data[0] if data else None,
        }
    if isinstance(data, dict):
        return {"type": "object", "keys": sorted(data), "value": data}
    return {"type": type(data).__name__, "value": data}


def main() -> int:
    driver = get_driver()
    driver.verify_connectivity()
    with driver.session() as session:
        learner = session.run("""
            MATCH (l:LearnerProfile)-[:HAS_MEMORY_CARD]->(m:MemoryCard)
            RETURN l.learner_id AS learner_id, l.name AS name,
                   coalesce(m.metric_key, 'evidence') AS skill
            ORDER BY l.name
            LIMIT 1
            """).single()
    if learner is None:
        raise RuntimeError("No learner with evidence exists in Neo4j")

    learner_id = learner["learner_id"]
    learner_name = learner["name"]
    skill = learner["skill"]

    calls: list[tuple[str, Callable[..., Any], tuple[Any, ...]]] = [
        ("get_learner_profile", tools.get_learner_profile, (learner_name,)),
        ("get_skill_proofs", tools.get_skill_proofs, (learner_id, skill)),
        ("get_behavioral_context", tools.get_behavioral_context, (learner_id,)),
        ("get_strengths_and_gaps", tools.get_strengths_and_gaps, (learner_id,)),
        ("get_milestone_history", tools.get_milestone_history, (learner_id,)),
        ("investigate_employer", tools.investigate_employer, (learner_id, skill)),
        ("suggest_next_steps", tools.suggest_next_steps, (learner_id,)),
    ]

    results: list[dict[str, Any]] = []
    for name, function, arguments in calls:
        entry: dict[str, Any] = {
            "tool": name,
            "arguments": arguments,
            "working": False,
        }
        try:
            result = function(*arguments)
            entry.update(
                {
                    "working": result.status != "error",
                    "status": result.status,
                    "message": result.message,
                    "evidence_ids": _evidence_ids(result.data),
                    "result": _summary(result.data),
                }
            )
        except Exception as exc:  # pragma: no cover - report boundary
            entry.update(
                {
                    "status": "exception",
                    "message": str(exc),
                    "evidence_ids": [],
                }
            )
        results.append(entry)

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "database": "bolt://127.0.0.1:7687",
        "learner": {"learner_id": learner_id, "name": learner_name, "skill": skill},
        "summary": {
            "tools_tested": len(results),
            "tools_working": sum(1 for item in results if item["working"]),
            "tools_failed": sum(1 for item in results if not item["working"]),
        },
        "tools": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, default=_json_default), encoding="utf-8"
    )
    print(f"Wrote {OUTPUT}")
    print(json.dumps(report["summary"], indent=2))
    close_driver()
    return 0 if report["summary"]["tools_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
