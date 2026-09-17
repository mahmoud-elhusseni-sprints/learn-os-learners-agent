"""Deterministic Visualizer Agent for employer talent intelligence data.

The flow is deliberately flat and easy to follow:

    data -> build_chart_data -> select_chart_type -> render -> commentary

Rendering lives in ``svg_render``, ``png_render`` and ``dashboard``; this file
only decides what to draw and describes the result.
"""

from __future__ import annotations

import re
from typing import Any

from src.app.schemas.models import (
    ChartType,
    Theme,
    VisualizationFormat,
    VisualizationRequest,
    VisualizationResponse,
    get_theme,
)

from .chart_data import (
    ChartData,
    build_chart_data,
    canvas_height,
    format_value,
    select_chart_type,
)
from .dashboard import render_dashboard
from .google_image import generate_concept_image
from .png_render import PNG_SUPPORTED, render_png
from .svg_render import render_svg

CHART_PHRASES = {
    ChartType.BAR: "bar chart",
    ChartType.HORIZONTAL_BAR: "horizontal bar chart",
    ChartType.LINE: "line chart",
    ChartType.AREA: "area chart",
    ChartType.PIE: "pie chart",
    ChartType.DONUT: "donut chart",
    ChartType.RADAR: "radar chart",
    ChartType.GROUPED_BAR: "grouped bar chart",
    ChartType.STACKED_BAR: "stacked bar chart",
    ChartType.PROGRESS: "progress meter",
}
DEFAULT_TITLE = "Talent Intelligence Visualization"


class VisualizerAgent:
    """Render structured talent intelligence data as SVG, HTML, or PNG."""

    def visualize(self, request: VisualizationRequest) -> VisualizationResponse:
        selected_format = request.format or self._select_format(request)
        theme = get_theme(request.theme)
        metadata: dict[str, Any] = {
            "theme": theme.model_dump(),
            "visualization_type": request.visualization_type,
            "width": request.width,
            "height": request.height,
        }
        try:
            data = build_chart_data(request.data)
            if data is None or not data.labels:
                return VisualizationResponse(
                    success=False,
                    format=selected_format,
                    commentary="No chart was rendered.",
                    metadata=metadata,
                    error="No visualization data was provided.",
                )
            metadata["row_count"] = data.point_count
            metadata["series_count"] = len(data.series)

            chart_type, reason = select_chart_type(
                data, request.context, request.chart_type
            )
            fallback = ""
            if selected_format is VisualizationFormat.PNG and (
                chart_type not in PNG_SUPPORTED
            ):
                fallback = (
                    f" A {CHART_PHRASES[chart_type]} cannot be drawn as PNG, so a "
                    "bar chart was used instead; request SVG or HTML for that "
                    "chart type."
                )
                metadata["requested_chart_type"] = chart_type.value
                metadata["fallback_reason"] = fallback.strip()
                chart_type, reason = ChartType.BAR, reason + " PNG fallback applied."
            metadata["selected_chart_type"] = chart_type.value
            metadata["selection_reason"] = reason

            height = request.height
            if chart_type is ChartType.HORIZONTAL_BAR:
                height = canvas_height(request.height, data.point_count)
            commentary = self._commentary(
                request, data, chart_type, selected_format, fallback
            )

            content: str | None = None
            asset: bytes | None = None
            if selected_format is VisualizationFormat.HTML:
                content = render_dashboard(
                    data,
                    theme,
                    chart_type,
                    title=request.title or "Talent Intelligence Dashboard",
                    description=request.description or "",
                    context=request.context,
                    commentary=commentary,
                    width=request.width,
                    height=height,
                )
                metadata["content_type"] = "text/html"
                metadata["interactive"] = True
            elif selected_format is VisualizationFormat.PNG:
                asset = render_png(
                    chart_type,
                    data,
                    theme,
                    request.width,
                    height,
                    title=request.title or DEFAULT_TITLE,
                    description=request.description or "",
                )
                metadata["content_type"] = "image/png"
                metadata["height"] = height
            else:
                content = render_svg(
                    chart_type,
                    data,
                    theme,
                    title=request.title or DEFAULT_TITLE,
                    description=request.description or "",
                    width=request.width,
                    height=height,
                )
                metadata["content_type"] = "image/svg+xml"
                metadata["height"] = height
            return VisualizationResponse(
                success=True,
                format=selected_format,
                content=content,
                asset=asset,
                commentary=commentary,
                metadata=metadata,
            )
        except Exception:
            return VisualizationResponse(
                success=False,
                format=selected_format,
                commentary="Visualization rendering failed.",
                metadata=metadata,
                error="Unable to render visualization from the provided data.",
            )

    def generate_image(
        self, prompt: str, theme: Theme | None = None
    ) -> VisualizationResponse:
        """Create a conceptual illustration with Google Gemini (never raises)."""
        return generate_concept_image(prompt, theme)

    @staticmethod
    def _select_format(request: VisualizationRequest) -> VisualizationFormat:
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

    def _commentary(
        self,
        request: VisualizationRequest,
        data: ChartData,
        chart_type: ChartType,
        selected_format: VisualizationFormat,
        fallback: str = "",
    ) -> str:
        """Describe the chart that was actually drawn, using only real values."""
        title = request.title or DEFAULT_TITLE
        names = ", ".join(data.labels[:8])
        if data.point_count > 8:
            names += f" and {data.point_count - 8} more"
        text = (
            f"{selected_format.value.upper()} {CHART_PHRASES[chart_type]} '{title}' "
            f"showing {data.point_count} item(s): {names}. "
        )
        values = data.values
        ranked = sorted(
            zip(data.labels, values, strict=True),
            key=lambda pair: pair[1],
            reverse=True,
        )

        if data.is_multi_series:
            totals = {series.name: sum(series.values) for series in data.series}
            best = max(totals, key=lambda name: totals[name])
            text += (
                f"{len(data.series)} series compared ("
                f"{', '.join(series.name for series in data.series)}); "
                f"{best} has the highest total at {format_value(totals[best])}."
            )
            return text + fallback

        if chart_type is ChartType.PROGRESS or data.point_count == 1:
            text += f"{ranked[0][0]} has a value of {format_value(ranked[0][1])}."
            return text + fallback

        if chart_type in (ChartType.LINE, ChartType.AREA):
            change = values[-1] - values[0]
            direction = "rose" if change >= 0 else "fell"
            text += (
                f"Values {direction} from {format_value(values[0])} "
                f"({data.labels[0]}) to {format_value(values[-1])} "
                f"({data.labels[-1]}), a change of {format_value(abs(change))}. "
            )
        if chart_type in (ChartType.PIE, ChartType.DONUT):
            total = data.total() or 1.0
            text += (
                f"{ranked[0][0]} is the largest share at "
                f"{ranked[0][1] / total * 100:.0f}% of {format_value(data.total())}. "
            )
        average = sum(values) / len(values)
        text += (
            f"Highest is {ranked[0][0]} ({format_value(ranked[0][1])}), "
            f"lowest is {ranked[-1][0]} ({format_value(ranked[-1][1])}), "
            f"average is {format_value(average)}."
        )
        if chart_type is ChartType.HORIZONTAL_BAR:
            text += " Bars appear top to bottom in the order listed."
        return text + fallback
