"""Evidence-only delegation to Task 15, with a bounded non-waiting fallback."""

import base64
import logging
import math
import os
import re
from collections import Counter
from contextvars import copy_context
from queue import Empty, Queue
from threading import BoundedSemaphore, Thread
from typing import Any, Literal

from langsmith import traceable

from src.app.agents.visualizer.agent import VisualizerAgent
from src.app.schemas.agent_response import (
    EmployerResponse,
    VerifiedEvidence,
    VisualArtifact,
    VisualFallback,
    VisualOptions,
)
from src.app.schemas.models import VisualizationRequest, VisualizationResponse

# Timed-out Python rendering cannot be killed safely. Bound abandoned work globally.
_SLOTS = BoundedSemaphore(2)
logger = logging.getLogger(__name__)


def visual_intent(query: str) -> str:
    """Conservative routing: direct facts remain text; unsupported plots fall back."""
    if re.search(r"\b(text only|no chart|without visual\w*)\b", query, re.I):
        return "none"
    if re.search(
        r"\b(timeline|trajectory|trajectories|over time|pie chart)\b", query, re.I
    ):
        return "unsupported"
    if re.search(r"\b(chart|graph|visual\w*|plot|compare|comparison)\b", query, re.I):
        return "coverage"
    return "none"


@traceable(
    name="visualizer_delegation",
    process_inputs=lambda inputs: {
        "query": inputs.get("query"),
        "evidence_count": len(inputs.get("records", [])),
    },
)
def delegate(
    query: str,
    markdown: str,
    records: list[dict[str, Any]],
    options: VisualOptions | None = None,
    renderer: Any = None,
    timeout: float | None = None,
) -> EmployerResponse:
    """Keep factual text unchanged on every visual failure; never invent ratings.

    Only successful retrieval tool records enter this function from the agent.
    Render distinct evidence counts by source, not ability or suitability scores.
    """
    response = EmployerResponse(markdown=markdown)

    def fallback(code: Any, notice: str) -> EmployerResponse:
        logger.info("visualizer_fallback", extra={"fallback_code": code})
        response.fallback = VisualFallback(code=code, notice=notice)
        return response

    intent = visual_intent(query)
    if intent == "none":
        return response
    if intent == "unsupported":
        return fallback(
            "unsupported",
            "This visual type is not supported; the factual answer is provided above.",
        )
    try:
        options = VisualOptions.model_validate(options or VisualOptions())
        evidence: dict[str, VerifiedEvidence] = {}
        for row in records:
            try:
                item = VerifiedEvidence.model_validate(
                    {
                        "evidence_id": row.get("evidence_id"),
                        "source_type": row.get("source_type"),
                        "observation": row.get("observation"),
                        "date": str(row["date"]) if row.get("date") else None,
                    }
                )
            except ValueError:
                continue
            if item.evidence_id in evidence and evidence[item.evidence_id] != item:
                return fallback(
                    "insufficient_evidence",
                    "Conflicting evidence identifiers prevent reliable visualization.",
                )
            evidence[item.evidence_id] = item
        if not evidence:
            return fallback(
                "insufficient_evidence",
                "No verified chartable evidence was returned; no visual was generated.",
            )
        counts = Counter(item.source_type for item in evidence.values())
        request = VisualizationRequest(
            data=[
                {"label": key, "count": count} for key, count in sorted(counts.items())
            ],
            title="Retrieved evidence coverage by source",
            description=(
                "Counts of distinct retrieved records, not skill ratings "
                "or a complete learner history."
            ),
            format=options.format,
            theme=options.theme,
            width=800,
            height=480,
        )
        seconds = (
            float(os.getenv("VISUALIZER_TIMEOUT_SECONDS", "2"))
            if timeout is None
            else timeout
        )
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("Invalid visualization timeout")
        if not _SLOTS.acquire(blocking=False):
            return fallback(
                "busy", "Visualization is busy; the factual answer is available."
            )
        results: Queue[Any] = Queue(maxsize=1)

        def render() -> None:
            try:
                # Explicit JSON boundary ensures request transport compatibility.
                payload = VisualizationRequest.model_validate_json(
                    request.model_dump_json()
                )
                results.put((renderer or VisualizerAgent()).visualize(payload))
            except Exception:
                results.put(None)
            finally:
                _SLOTS.release()

        context = copy_context()
        thread = Thread(target=lambda: context.run(render), daemon=True)
        try:
            thread.start()
        except Exception:
            _SLOTS.release()
            raise
        try:
            result = results.get(timeout=seconds)
        except Empty:
            return fallback(
                "timeout", "Visualization timed out; the factual answer is available."
            )
        if not isinstance(result, VisualizationResponse):
            raise ValueError("Invalid renderer response")
        result = VisualizationResponse.model_validate_json(result.model_dump_json())
        if not result.success or result.format != options.format:
            raise ValueError("Rendering failed")
        encoding: Literal["text", "base64"]
        if result.format.value == "png":
            if not result.asset:
                raise ValueError("Empty image")
            data, encoding = base64.b64encode(result.asset).decode("ascii"), "base64"
        else:
            if not result.content:
                raise ValueError("Empty visual")
            data, encoding = result.content, "text"
        response.artifacts.append(
            VisualArtifact(
                format=result.format,
                data=data,
                encoding=encoding,
                commentary=(
                    "This chart shows retrieved evidence counts by source, "
                    "not proficiency scores. "
                )
                + result.commentary,
                evidence=list(evidence.values()),
            )
        )
        return response
    except Exception:
        return fallback(
            "error", "Visualization is unavailable; the factual answer is available."
        )
