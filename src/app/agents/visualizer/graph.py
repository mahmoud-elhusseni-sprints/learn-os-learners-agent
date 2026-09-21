"""LangGraph workflow for the Visualizer Agent."""

from __future__ import annotations

import re
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.app.schemas.models import (
    ChartRow,
    VisualizationFormat,
    VisualizationRequest,
    VisualizationResponse,
    VisualizerState,
    get_theme,
)

from .renderers import (
    canvas_height,
    format_value,
    is_number,
    render_html,
    render_png,
    render_svg,
)


def select_format(request: VisualizationRequest) -> VisualizationFormat:
    text = " ".join(
        part.lower()
        for part in (
            request.title or "",
            request.description or "",
            request.visualization_type or "",
        )
    )
    words = set(re.findall(r"[a-z]+", text))
    if words & {"interactive", "dashboard", "web"}:
        return VisualizationFormat.HTML
    if words & {"image", "export", "png"}:
        return VisualizationFormat.PNG
    return VisualizationFormat.SVG


def rows_from_known_payload(data: dict[Any, Any]) -> list[ChartRow]:
    strengths = data.get("strengths")
    if isinstance(strengths, list):
        rows: list[ChartRow] = []
        for index, item in enumerate(strengths, start=1):
            if not isinstance(item, dict):
                continue
            label = str(item.get("area") or item.get("skill") or f"Strength {index}")
            evidence_ids = item.get("evidence_ids")
            value = float(len(evidence_ids)) if isinstance(evidence_ids, list) else 1.0
            rows.append(ChartRow(label, value, str(item.get("observation") or "")))
        return rows
    gaps = data.get("gaps")
    if isinstance(gaps, list):
        return [
            ChartRow(str(item.get("area") or f"Gap {index}"), 1.0, "Gap")
            for index, item in enumerate(gaps, start=1)
            if isinstance(item, dict)
        ]
    return []


def rows_from_item(item: dict[str, Any]) -> list[ChartRow]:
    label = (
        item.get("label") or item.get("name") or item.get("area") or item.get("skill")
    )
    value = next(
        (
            item[key]
            for key in ("value", "score", "count", "confidence")
            if item.get(key) is not None
        ),
        None,
    )
    if label is None or value is None or not is_number(value):
        return []
    note = str(item.get("observation") or item.get("summary") or "")
    return [ChartRow(str(label), float(value), note)]


def rows_from_data(data: Any) -> list[ChartRow]:
    if isinstance(data, dict):
        known = rows_from_known_payload(data)
        if known:
            return known
        return [
            ChartRow(str(label), float(value))
            for label, value in data.items()
            if is_number(value)
        ]
    if isinstance(data, list):
        return [
            row
            for item in data
            if isinstance(item, dict)
            for row in rows_from_item(item)
        ]
    return []


def generate_commentary(
    request: VisualizationRequest,
    rows: list[ChartRow],
    selected_format: VisualizationFormat,
) -> str:
    title = request.title or "Talent Intelligence Visualization"
    names = ", ".join(row.label for row in rows[:8])
    if len(rows) > 8:
        names += f" and {len(rows) - 8} more"
    ranked = sorted(rows, key=lambda row: row.value, reverse=True)
    highest, lowest = ranked[0], ranked[-1]
    text = (
        f"{selected_format.value.upper()} bar chart '{title}' showing "
        f"{len(rows)} item(s): {names}. "
    )
    if len(rows) == 1:
        text += f"{highest.label} has a value of "
        text += f"{format_value(highest.value)}."
    else:
        average = sum(row.value for row in rows) / len(rows)
        text += (
            f"Highest is {highest.label} ({format_value(highest.value)}), "
            f"lowest is {lowest.label} ({format_value(lowest.value)}), "
            f"average is {format_value(average)}."
        )
    if selected_format == VisualizationFormat.PNG:
        text += " Bars appear top to bottom in the order listed."
    return text


def resolve_request_node(state: VisualizerState) -> dict[str, Any]:
    request = state["request"]
    selected_format = request.format or select_format(request)
    theme = get_theme(request.theme)
    metadata: dict[str, Any] = {
        "theme": theme.model_dump(),
        "visualization_type": request.visualization_type,
        "width": request.width,
        "height": request.height,
    }
    return {
        "format": selected_format,
        "theme": theme,
        "metadata": metadata,
    }


def extract_data_node(state: VisualizerState) -> dict[str, Any]:
    request = state["request"]
    metadata = dict(state.get("metadata") or {})
    try:
        rows = rows_from_data(request.data)
    except Exception:
        rows = []

    if not rows:
        return {
            "rows": [],
            "success": False,
            "error": "No visualization data was provided.",
            "commentary": "No chart was rendered.",
            "metadata": metadata,
        }

    metadata["row_count"] = len(rows)
    height = canvas_height(request.height, len(rows))
    return {
        "rows": rows,
        "height": height,
        "metadata": metadata,
        "success": True,
    }


def render_node(state: VisualizerState) -> dict[str, Any]:
    request = state["request"]
    selected_format = state["format"]
    theme = state["theme"]
    rows = state["rows"]
    height = state.get("height", request.height)
    metadata = dict(state.get("metadata") or {})

    content: str | None = None
    asset: bytes | None = None

    if selected_format == VisualizationFormat.HTML:
        content = render_html(request, rows, theme)
        metadata["content_type"] = "text/html"
    elif selected_format == VisualizationFormat.PNG:
        asset = render_png(request, rows, theme, height)
        metadata["content_type"] = "image/png"
        metadata["height"] = height
    else:
        content = render_svg(request, rows, theme, height)
        metadata["content_type"] = "image/svg+xml"
        metadata["height"] = height

    return {
        "content": content,
        "asset": asset,
        "metadata": metadata,
    }


def commentary_node(state: VisualizerState) -> dict[str, Any]:
    request = state["request"]
    rows = state["rows"]
    selected_format = state["format"]
    commentary = generate_commentary(request, rows, selected_format)
    return {"commentary": commentary}


def build_response_node(state: VisualizerState) -> dict[str, Any]:
    selected_format = state.get("format", VisualizationFormat.SVG)
    metadata = state.get("metadata") or {}
    success = state.get("success", False)
    error = state.get("error")
    commentary = state.get("commentary", "")

    if not success or error:
        response = VisualizationResponse(
            success=False,
            format=selected_format,
            commentary=commentary or "Visualization rendering failed.",
            metadata=metadata,
            error=error or "Unable to render visualization from the provided data.",
        )
    else:
        response = VisualizationResponse(
            success=True,
            format=selected_format,
            content=state.get("content"),
            asset=state.get("asset"),
            commentary=commentary,
            metadata=metadata,
        )

    return {"response": response}


def route_after_extract(state: VisualizerState) -> str:
    if not state.get("rows"):
        return "build_response"
    return "render"


def build_visualizer_graph() -> StateGraph:
    graph = StateGraph(VisualizerState)
    graph.add_node("resolve_request", resolve_request_node)
    graph.add_node("extract_data", extract_data_node)
    graph.add_node("render", render_node)
    graph.add_node("commentary", commentary_node)
    graph.add_node("build_response", build_response_node)

    graph.add_edge(START, "resolve_request")
    graph.add_edge("resolve_request", "extract_data")
    graph.add_conditional_edges(
        "extract_data",
        route_after_extract,
        {"render": "render", "build_response": "build_response"},
    )
    graph.add_edge("render", "commentary")
    graph.add_edge("commentary", "build_response")
    graph.add_edge("build_response", END)
    return graph


_COMPILED_GRAPH = build_visualizer_graph().compile()


def run_visualizer_pipeline(request: VisualizationRequest) -> VisualizationResponse:
    try:
        result = _COMPILED_GRAPH.invoke(
            {"request": request},
            config={
                "run_name": "visualizer_agent_pipeline",
                "metadata": {
                    "agent": "visualizer",
                    "visualization_type": request.visualization_type,
                },
                "tags": ["visualizer", "chart-rendering"],
            },
        )
        return result["response"]
    except Exception:
        theme = get_theme(request.theme)
        selected_format = request.format or select_format(request)
        return VisualizationResponse(
            success=False,
            format=selected_format,
            commentary="Visualization rendering failed.",
            metadata={
                "theme": theme.model_dump(),
                "visualization_type": request.visualization_type,
                "width": request.width,
                "height": request.height,
            },
            error="Unable to render visualization from the provided data.",
        )


__all__ = [
    "VisualizerState",
    "build_visualizer_graph",
    "generate_commentary",
    "rows_from_data",
    "rows_from_item",
    "rows_from_known_payload",
    "run_visualizer_pipeline",
    "select_format",
]
