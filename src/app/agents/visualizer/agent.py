"""Deterministic Visualizer Agent for employer talent intelligence data."""

from __future__ import annotations

import binascii
import html
import math
import re
import struct
import zlib
from dataclasses import dataclass
from typing import Any

from src.app.schemas.models import (
    Theme,
    VisualizationFormat,
    VisualizationRequest,
    VisualizationResponse,
    get_theme,
)

from .google_image import generate_concept_image

TOP = 88
BAR_HEIGHT = 26
ROW_GAP = 18
BOTTOM = 32


@dataclass(frozen=True)
class ChartRow:
    label: str
    value: float
    note: str = ""


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
            rows = self._rows_from_data(request.data)
            if not rows:
                return VisualizationResponse(
                    success=False,
                    format=selected_format,
                    commentary="No chart was rendered.",
                    metadata=metadata,
                    error="No visualization data was provided.",
                )
            metadata["row_count"] = len(rows)
            height = self._canvas_height(request.height, len(rows))
            content: str | None = None
            asset: bytes | None = None
            if selected_format == VisualizationFormat.HTML:
                content = self._render_html(request, rows)
                metadata["content_type"] = "text/html"
            elif selected_format == VisualizationFormat.PNG:
                asset = self._render_png(request, rows, height)
                metadata["content_type"] = "image/png"
                metadata["height"] = height
            else:
                content = self._render_svg(request, rows, height)
                metadata["content_type"] = "image/svg+xml"
                metadata["height"] = height
            return VisualizationResponse(
                success=True,
                format=selected_format,
                content=content,
                asset=asset,
                commentary=self._commentary(request, rows, selected_format),
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

    def _rows_from_data(self, data: Any) -> list[ChartRow]:
        if isinstance(data, dict):
            known = self._rows_from_known_payload(data)
            if known:
                return known
            return [
                ChartRow(str(label), float(value))
                for label, value in data.items()
                if self._is_number(value)
            ]
        if isinstance(data, list):
            return [
                row
                for item in data
                if isinstance(item, dict)
                for row in self._rows_from_item(item)
            ]
        return []

    def _rows_from_known_payload(self, data: dict[Any, Any]) -> list[ChartRow]:
        strengths = data.get("strengths")
        if isinstance(strengths, list):
            rows: list[ChartRow] = []
            for index, item in enumerate(strengths, start=1):
                if not isinstance(item, dict):
                    continue
                label = str(
                    item.get("area") or item.get("skill") or f"Strength {index}"
                )
                evidence_ids = item.get("evidence_ids")
                value = (
                    float(len(evidence_ids)) if isinstance(evidence_ids, list) else 1.0
                )
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

    def _rows_from_item(self, item: dict[str, Any]) -> list[ChartRow]:
        label = (
            item.get("label")
            or item.get("name")
            or item.get("area")
            or item.get("skill")
        )
        value = next(
            (
                item[key]
                for key in ("value", "score", "count", "confidence")
                if item.get(key) is not None
            ),
            None,
        )
        if label is None or value is None or not self._is_number(value):
            return []
        note = str(item.get("observation") or item.get("summary") or "")
        return [ChartRow(str(label), float(value), note)]

    @staticmethod
    def _is_number(value: Any) -> bool:
        return (
            isinstance(value, int | float)
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    @staticmethod
    def _canvas_height(requested: int, row_count: int) -> int:
        needed = TOP + row_count * (BAR_HEIGHT + ROW_GAP) - ROW_GAP + BOTTOM
        return max(requested, needed)

    @staticmethod
    def _max_value(rows: list[ChartRow]) -> float:
        return max(max(row.value for row in rows), 0.0) or 1.0

    @staticmethod
    def _bar_length(value: float, max_value: float, full: int) -> int:
        return int((max(value, 0.0) / max_value) * full)

    def _commentary(
        self,
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
            text += f"{self._format_value(highest.value)}."
        else:
            average = sum(row.value for row in rows) / len(rows)
            text += (
                f"Highest is {highest.label} ({self._format_value(highest.value)}), "
                f"lowest is {lowest.label} ({self._format_value(lowest.value)}), "
                f"average is {self._format_value(average)}."
            )
        if selected_format == VisualizationFormat.PNG:
            text += " Bars appear top to bottom in the order listed."
        return text

    def _render_svg(
        self, request: VisualizationRequest, rows: list[ChartRow], height: int
    ) -> str:
        theme = get_theme(request.theme)
        width = request.width
        margin_left = 180
        margin_right = 48
        chart_width = max(80, width - margin_left - margin_right)
        max_value = self._max_value(rows)
        title = html.escape(request.title or "Talent Intelligence Visualization")
        description = html.escape(request.description or "")
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">',
            f'<rect width="{width}" height="{height}" ' f'fill="{theme.background}"/>',
            f'<text x="32" y="42" font-family="Arial, sans-serif" font-size="24" '
            f'font-weight="700" fill="{theme.text}">{title}</text>',
        ]
        if description:
            parts.append(
                f'<text x="32" y="68" font-family="Arial, sans-serif" font-size="13" '
                f'fill="{theme.text}" opacity="0.72">{description}</text>'
            )
        for index, row in enumerate(rows):
            y = TOP + index * (BAR_HEIGHT + ROW_GAP)
            length = self._bar_length(row.value, max_value, chart_width)
            label = html.escape(row.label)
            value = self._format_value(row.value)
            parts.extend(
                [
                    f'<text x="32" y="{y + 19}" font-family="Arial, sans-serif" '
                    f'font-size="13" fill="{theme.text}">{label}</text>',
                    f'<rect x="{margin_left}" y="{y}" width="{chart_width}" '
                    f'height="{BAR_HEIGHT}" rx="4" '
                    f'fill="{theme.secondary}" opacity="0.18"/>',
                    f'<rect x="{margin_left}" y="{y}" width="{length}" '
                    f'height="{BAR_HEIGHT}" rx="4" fill="{theme.primary}"/>',
                    f'<text x="{margin_left + length + 8}" y="{y + 18}" '
                    f'font-family="Arial, sans-serif" font-size="12" '
                    f'fill="{theme.text}">{value}</text>',
                ]
            )
        parts.append("</svg>")
        return "".join(parts)

    def _render_html(self, request: VisualizationRequest, rows: list[ChartRow]) -> str:
        theme = get_theme(request.theme)
        title = html.escape(request.title or "Talent Intelligence Visualization")
        description = html.escape(request.description or "")
        max_value = self._max_value(rows)
        items = "\n".join(self._html_row(row, max_value) for row in rows)
        return (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{title}</title>\n"
            "<style>\n"
            f":root{{--primary:{theme.primary};--secondary:{theme.secondary};"
            f"--accent:{theme.accent};--background:{theme.background};--text:{theme.text};}}\n"
            "body{margin:0;background:var(--background);color:var(--text);"
            "font-family:Arial,sans-serif;padding:32px;}\n"
            "main{max-width:880px;margin:0 auto;}\n"
            "h1{font-size:28px;margin:0 0 8px;}\n"
            "p{margin:0 0 24px;opacity:.72;}\n"
            ".row{margin:18px 0;}\n"
            ".meta{display:flex;justify-content:space-between;gap:16px;font-size:14px;}\n"
            ".track{height:28px;"
            "background:color-mix(in srgb,var(--secondary) 18%,white);"
            "border-radius:6px;overflow:hidden;margin-top:6px;}\n"
            ".bar{height:100%;background:var(--primary);}\n"
            ".note{font-size:12px;opacity:.7;margin-top:4px;}\n"
            "</style>\n"
            "</head>\n"
            "<body><main>\n"
            f"<h1>{title}</h1>\n"
            f"<p>{description}</p>\n"
            f"{items}\n"
            "</main></body>\n"
            "</html>\n"
        )

    def _html_row(self, row: ChartRow, max_value: float) -> str:
        percent = self._bar_length(row.value, max_value, 100)
        label = html.escape(row.label)
        value = html.escape(self._format_value(row.value))
        note = html.escape(row.note)
        note_html = f'<div class="note">{note}</div>' if note else ""
        return (
            '<section class="row">'
            f'<div class="meta"><strong>{label}</strong><span>{value}</span></div>'
            f'<div class="track"><div class="bar" style="width:{percent}%"></div></div>'
            f"{note_html}</section>"
        )

    def _render_png(
        self, request: VisualizationRequest, rows: list[ChartRow], height: int
    ) -> bytes:
        theme = get_theme(request.theme)
        width = request.width
        background = self._hex_to_rgb(theme.background)
        primary = self._hex_to_rgb(theme.primary)
        secondary = self._hex_to_rgb(theme.secondary)
        pixels = bytearray(background * width * height)
        max_value = self._max_value(rows)
        left = 120
        right = 40
        chart_width = max(20, width - left - right)
        for index, row in enumerate(rows):
            y = TOP + index * (BAR_HEIGHT + ROW_GAP)
            self._fill_rect(pixels, width, left, y, chart_width, BAR_HEIGHT, secondary)
            length = self._bar_length(row.value, max_value, chart_width)
            self._fill_rect(pixels, width, left, y, length, BAR_HEIGHT, primary)
        return self._png_from_rgb(width, height, bytes(pixels))

    @staticmethod
    def _fill_rect(
        pixels: bytearray,
        image_width: int,
        x: int,
        y: int,
        width: int,
        height: int,
        color: bytes,
    ) -> None:
        for row in range(y, y + height):
            start = (row * image_width + x) * 3
            end = start + width * 3
            pixels[start:end] = color * width

    @staticmethod
    def _hex_to_rgb(value: str) -> bytes:
        return bytes.fromhex(value.lstrip("#"))

    @staticmethod
    def _png_from_rgb(width: int, height: int, pixels: bytes) -> bytes:
        rows = [
            b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3] for y in range(height)
        ]
        raw = b"".join(rows)

        def chunk(kind: bytes, data: bytes) -> bytes:
            checksum = binascii.crc32(kind + data) & 0xFFFFFFFF
            return (
                struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)
            )

        header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )

    @staticmethod
    def _format_value(value: float) -> str:
        return str(int(value)) if value.is_integer() else f"{value:.2f}"
