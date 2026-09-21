"""Visualizer Agent for employer talent intelligence data, powered by LangGraph."""

from __future__ import annotations

from typing import Any

from src.app.schemas.models import (
    Theme,
    VisualizationFormat,
    VisualizationRequest,
    VisualizationResponse,
)

from .google_image import generate_concept_image
from .graph import (
    generate_commentary,
    rows_from_data,
    rows_from_item,
    rows_from_known_payload,
    run_visualizer_pipeline,
    select_format,
)
from .renderers import (
    BAR_HEIGHT,
    BOTTOM,
    ROW_GAP,
    TOP,
    ChartRow,
    canvas_height,
    format_value,
    is_number,
    max_value,
    render_html,
    render_png,
    render_svg,
)


class VisualizerAgent:

    def visualize(self, request: VisualizationRequest) -> VisualizationResponse:
        return run_visualizer_pipeline(request)

    def generate_image(
        self, prompt: str, theme: Theme | None = None
    ) -> VisualizationResponse:
        return generate_concept_image(prompt, theme)

    @staticmethod
    def _select_format(request: VisualizationRequest) -> VisualizationFormat:
        return select_format(request)

    def _rows_from_data(self, data: Any) -> list[ChartRow]:
        return rows_from_data(data)

    def _rows_from_known_payload(self, data: dict[Any, Any]) -> list[ChartRow]:
        return rows_from_known_payload(data)

    def _rows_from_item(self, item: dict[str, Any]) -> list[ChartRow]:
        return rows_from_item(item)

    @staticmethod
    def _is_number(value: Any) -> bool:
        return is_number(value)

    @staticmethod
    def _canvas_height(requested: int, row_count: int) -> int:
        return canvas_height(requested, row_count)

    @staticmethod
    def _max_value(rows: list[ChartRow]) -> float:
        return max_value(rows)

    @staticmethod
    def _format_value(value: float) -> str:
        return format_value(value)

    def _commentary(
        self,
        request: VisualizationRequest,
        rows: list[ChartRow],
        selected_format: VisualizationFormat,
    ) -> str:
        return generate_commentary(request, rows, selected_format)

    def _render_svg(
        self, request: VisualizationRequest, rows: list[ChartRow], height: int
    ) -> str:
        from src.app.schemas.models import get_theme

        return render_svg(request, rows, get_theme(request.theme), height)

    def _render_html(self, request: VisualizationRequest, rows: list[ChartRow]) -> str:
        from src.app.schemas.models import get_theme

        return render_html(request, rows, get_theme(request.theme))

    def _render_png(
        self, request: VisualizationRequest, rows: list[ChartRow], height: int
    ) -> bytes:
        from src.app.schemas.models import get_theme

        return render_png(request, rows, get_theme(request.theme), height)


__all__ = [
    "BAR_HEIGHT",
    "BOTTOM",
    "ChartRow",
    "ROW_GAP",
    "TOP",
    "VisualizerAgent",
]
