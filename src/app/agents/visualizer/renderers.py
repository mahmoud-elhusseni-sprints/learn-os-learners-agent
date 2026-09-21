"""Low-level format renderers for the Visualizer Agent."""

from __future__ import annotations

import binascii
import html
import math
import struct
import zlib
from typing import Any

from src.app.schemas.models import (
    ChartRow,
    Theme,
    VisualizationRequest,
)

TOP = 88
BAR_HEIGHT = 26
ROW_GAP = 18
BOTTOM = 32


def format_value(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.2f}"


def canvas_height(requested: int, row_count: int) -> int:
    needed = TOP + row_count * (BAR_HEIGHT + ROW_GAP) - ROW_GAP + BOTTOM
    return max(requested, needed)


def max_value(rows: list[ChartRow]) -> float:
    return max(max(row.value for row in rows), 0.0) or 1.0


def bar_length(value: float, max_val: float, full: int) -> int:
    return int((max(value, 0.0) / max_val) * full)


def is_number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def hex_to_rgb(value: str) -> bytes:
    return bytes.fromhex(value.lstrip("#"))


def fill_rect(
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


def png_from_rgb(width: int, height: int, pixels: bytes) -> bytes:
    rows = [
        b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3] for y in range(height)
    ]
    raw = b"".join(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = binascii.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def render_svg(
    request: VisualizationRequest, rows: list[ChartRow], theme: Theme, height: int
) -> str:
    width = request.width
    margin_left = 180
    margin_right = 48
    chart_width = max(80, width - margin_left - margin_right)
    max_val = max_value(rows)
    title = html.escape(request.title or "Talent Intelligence Visualization")
    description = html.escape(request.description or "")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<rect width="{width}" height="{height}" fill="{theme.background}"/>',
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
        length = bar_length(row.value, max_val, chart_width)
        label = html.escape(row.label)
        val_str = format_value(row.value)
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
                f'fill="{theme.text}">{val_str}</text>',
            ]
        )
    parts.append("</svg>")
    return "".join(parts)


def html_row(row: ChartRow, max_val: float) -> str:
    percent = bar_length(row.value, max_val, 100)
    label = html.escape(row.label)
    val_str = html.escape(format_value(row.value))
    note = html.escape(row.note)
    note_html = f'<div class="note">{note}</div>' if note else ""
    return (
        '<section class="row">'
        f'<div class="meta"><strong>{label}</strong><span>{val_str}</span></div>'
        f'<div class="track"><div class="bar" style="width:{percent}%"></div></div>'
        f"{note_html}</section>"
    )


def render_html(
    request: VisualizationRequest, rows: list[ChartRow], theme: Theme
) -> str:
    title = html.escape(request.title or "Talent Intelligence Visualization")
    description = html.escape(request.description or "")
    max_val = max_value(rows)
    items = "\n".join(html_row(row, max_val) for row in rows)
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


def render_png(
    request: VisualizationRequest, rows: list[ChartRow], theme: Theme, height: int
) -> bytes:
    width = request.width
    background = hex_to_rgb(theme.background)
    primary = hex_to_rgb(theme.primary)
    secondary = hex_to_rgb(theme.secondary)
    pixels = bytearray(background * width * height)
    max_val = max_value(rows)
    left = 120
    right = 40
    chart_width = max(20, width - left - right)
    for index, row in enumerate(rows):
        y = TOP + index * (BAR_HEIGHT + ROW_GAP)
        fill_rect(pixels, width, left, y, chart_width, BAR_HEIGHT, secondary)
        length = bar_length(row.value, max_val, chart_width)
        fill_rect(pixels, width, left, y, length, BAR_HEIGHT, primary)
    return png_from_rgb(width, height, bytes(pixels))
