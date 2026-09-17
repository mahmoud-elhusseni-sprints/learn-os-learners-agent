"""SVG renderers: one small function per chart type, sharing a few helpers.

Every function returns a list of SVG elements drawn inside the same frame, so
adding a chart type never touches the other ones.
"""

from __future__ import annotations

import html
import math

from src.app.schemas.models import ChartType, Theme

from .chart_data import BAR_HEIGHT, PAD, ROW_GAP, TOP, ChartData, format_value

FONT = 'font-family="Arial, sans-serif"'
AXIS_SPACE = 56
LEGEND_HEIGHT = 26


def esc(text: object) -> str:
    return html.escape(str(text))


def short(label: str, limit: int = 16) -> str:
    return label if len(label) <= limit else label[: limit - 1] + "…"


def series_paint(index: int, theme: Theme) -> tuple[str, float]:
    """Deterministic color per series: cycle the theme, then fade."""
    palette = (theme.primary, theme.secondary, theme.accent)
    opacity = max(1.0 - 0.18 * (index // 2), 0.4)
    return palette[index % len(palette)], opacity


def polar(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    angle = math.radians(degrees - 90)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def _text(x: float, y: float, value: str, fill: str, size: int, **kw: object) -> str:
    extra = "".join(f' {key.replace("_", "-")}="{val}"' for key, val in kw.items())
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" {FONT} font-size="{size}" '
        f'fill="{fill}"{extra}>{value}</text>'
    )


def _grid(
    x0: float, y0: float, x1: float, y1: float, theme: Theme, top_value: float
) -> list[str]:
    parts = []
    for step in range(5):
        y = y1 - (y1 - y0) * step / 4
        parts.append(
            f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" '
            f'stroke="{theme.text}" stroke-opacity="0.12"/>'
        )
        parts.append(
            _text(
                x0 - 8,
                y + 4,
                esc(format_value(top_value * step / 4)),
                theme.text,
                10,
                text_anchor="end",
                opacity="0.7",
            )
        )
    return parts


def _legend(names: list[str], theme: Theme, x: float, y: float) -> list[str]:
    parts = []
    offset = x
    for index, name in enumerate(names):
        color, opacity = series_paint(index, theme)
        parts.append(
            f'<rect x="{offset:.1f}" y="{y - 10:.1f}" width="12" height="12" rx="3" '
            f'fill="{color}" opacity="{opacity:.2f}"/>'
        )
        parts.append(_text(offset + 18, y, esc(short(name, 18)), theme.text, 12))
        offset += 34 + 7 * len(short(name, 18))
    return parts


def _plot_box(width: int, height: int, top: int, left: int = 64) -> tuple[float, ...]:
    return (left, float(top), width - PAD, height - AXIS_SPACE)


def _vertical_bars(
    data: ChartData, theme: Theme, width: int, height: int, top: int, stacked: bool
) -> list[str]:
    x0, y0, x1, y1 = _plot_box(width, height, top)
    if data.is_multi_series:
        y0 += LEGEND_HEIGHT
    top_value = data.stacked_max if stacked else data.max_value
    parts = _grid(x0, y0, x1, y1, theme, top_value)
    band = (x1 - x0) / max(data.point_count, 1)
    count = len(data.series)
    for index, label in enumerate(data.labels):
        band_x = x0 + index * band
        if stacked:
            cursor = y1
            for s_index, series in enumerate(data.series):
                value = max(series.values[index], 0.0)
                bar_height = (value / top_value) * (y1 - y0)
                color, opacity = series_paint(s_index, theme)
                parts.append(
                    f'<rect x="{band_x + band * 0.2:.1f}" '
                    f'y="{cursor - bar_height:.1f}" width="{band * 0.6:.1f}" '
                    f'height="{bar_height:.1f}" fill="{color}" '
                    f'opacity="{opacity:.2f}"/>'
                )
                cursor -= bar_height
        else:
            slot = band * 0.6 / count
            for s_index, series in enumerate(data.series):
                value = max(series.values[index], 0.0)
                bar_height = (value / top_value) * (y1 - y0)
                color, opacity = series_paint(s_index, theme)
                bar_x = band_x + band * 0.2 + s_index * slot
                parts.append(
                    f'<rect x="{bar_x:.1f}" y="{y1 - bar_height:.1f}" '
                    f'width="{max(slot - 2, 2):.1f}" height="{bar_height:.1f}" '
                    f'rx="4" fill="{color}" opacity="{opacity:.2f}"/>'
                )
                if count == 1:
                    parts.append(
                        _text(
                            bar_x + slot / 2,
                            y1 - bar_height - 6,
                            esc(format_value(value)),
                            theme.text,
                            12,
                            text_anchor="middle",
                        )
                    )
        parts.append(
            _text(
                band_x + band / 2,
                y1 + 18,
                esc(short(label, 12)),
                theme.text,
                11,
                text_anchor="middle",
            )
        )
    if data.is_multi_series:
        parts.extend(_legend([s.name for s in data.series], theme, x0, top + 16))
    return parts


def bar_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _vertical_bars(data, theme, width, height, top, stacked=False)


def grouped_bar_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _vertical_bars(data, theme, width, height, top, stacked=False)


def stacked_bar_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _vertical_bars(data, theme, width, height, top, stacked=True)


def horizontal_bar_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    left = 180
    track_width = max(80, width - left - 48)
    top_value = data.max_value
    parts = []
    for index, label in enumerate(data.labels):
        y = top + index * (BAR_HEIGHT + ROW_GAP)
        value = data.values[index]
        length = int((max(value, 0.0) / top_value) * track_width)
        parts.append(_text(PAD, y + 19, esc(short(label, 22)), theme.text, 13))
        parts.append(
            f'<rect x="{left}" y="{y}" width="{track_width}" height="{BAR_HEIGHT}" '
            f'rx="4" fill="{theme.secondary}" opacity="0.18"/>'
        )
        parts.append(
            f'<rect x="{left}" y="{y}" width="{length}" height="{BAR_HEIGHT}" '
            f'rx="4" fill="{theme.primary}"/>'
        )
        parts.append(
            _text(left + length + 8, y + 18, esc(format_value(value)), theme.text, 12)
        )
    return parts


def _points(
    data: ChartData, width: int, height: int, top: int
) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = _plot_box(width, height, top)
    top_value = data.max_value
    count = max(data.point_count - 1, 1)
    return [
        (
            x0 + (x1 - x0) * index / count,
            y1 - (max(value, 0.0) / top_value) * (y1 - y0),
        )
        for index, value in enumerate(data.values)
    ]


def _line_like(
    data: ChartData, theme: Theme, width: int, height: int, top: int, area: bool
) -> list[str]:
    x0, y0, x1, y1 = _plot_box(width, height, top)
    parts = _grid(x0, y0, x1, y1, theme, data.max_value)
    points = _points(data, width, height, top)
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    if area:
        parts.append(
            f'<polygon points="{points[0][0]:.1f},{y1:.1f} {path} '
            f'{points[-1][0]:.1f},{y1:.1f}" fill="{theme.primary}" opacity="0.22"/>'
        )
    parts.append(
        f'<polyline points="{path}" fill="none" stroke="{theme.primary}" '
        f'stroke-width="3" stroke-linejoin="round"/>'
    )
    for index, (x, y) in enumerate(points):
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{theme.primary}"/>'
        )
        parts.append(
            _text(
                x,
                y - 10,
                esc(format_value(data.values[index])),
                theme.text,
                11,
                text_anchor="middle",
            )
        )
        parts.append(
            _text(
                x,
                y1 + 18,
                esc(short(data.labels[index], 10)),
                theme.text,
                11,
                text_anchor="middle",
            )
        )
    return parts


def line_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _line_like(data, theme, width, height, top, area=False)


def area_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _line_like(data, theme, width, height, top, area=True)


def _slices(
    data: ChartData, theme: Theme, width: int, height: int, top: int, hole: float
) -> list[str]:
    total = data.total() or 1.0
    radius = min((height - top - PAD) / 2, (width - 260) / 2, 150)
    cx, cy = PAD + radius + 20, top + radius + 10
    parts: list[str] = []
    angle = 0.0
    for index, value in enumerate(data.values):
        share = max(value, 0.0) / total
        sweep = share * 360
        color, opacity = series_paint(index, theme)
        if sweep >= 359.99:
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" '
                f'fill="{color}" opacity="{opacity:.2f}"/>'
            )
        else:
            start = polar(cx, cy, radius, angle)
            end = polar(cx, cy, radius, angle + sweep)
            large = 1 if sweep > 180 else 0
            parts.append(
                f'<path d="M {cx:.1f} {cy:.1f} L {start[0]:.1f} {start[1]:.1f} '
                f'A {radius:.1f} {radius:.1f} 0 {large} 1 {end[0]:.1f} {end[1]:.1f} Z" '
                f'fill="{color}" opacity="{opacity:.2f}"/>'
            )
        label_y = top + 24 + index * 24
        parts.append(
            f'<rect x="{cx + radius + 40:.1f}" y="{label_y - 10:.1f}" width="12" '
            f'height="12" rx="3" fill="{color}" opacity="{opacity:.2f}"/>'
        )
        parts.append(
            _text(
                cx + radius + 58,
                label_y,
                f"{esc(short(data.labels[index], 18))} "
                f"{esc(format_value(value))} ({share * 100:.0f}%)",
                theme.text,
                12,
            )
        )
        angle += sweep
    if hole:
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius * hole:.1f}" '
            f'fill="{theme.background}"/>'
        )
        parts.append(
            _text(
                cx,
                cy + 6,
                esc(format_value(total)),
                theme.text,
                20,
                text_anchor="middle",
                font_weight="700",
            )
        )
    return parts


def pie_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _slices(data, theme, width, height, top, hole=0.0)


def donut_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    return _slices(data, theme, width, height, top, hole=0.58)


def radar_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    radius = min((height - top - PAD) / 2, width / 2 - 120, 150)
    cx, cy = width / 2, top + radius + 16
    count = data.point_count
    top_value = data.max_value
    parts: list[str] = []
    for ring in range(1, 5):
        points = " ".join(
            "{:.1f},{:.1f}".format(*polar(cx, cy, radius * ring / 4, i * 360 / count))
            for i in range(count)
        )
        parts.append(
            f'<polygon points="{points}" fill="none" stroke="{theme.text}" '
            f'stroke-opacity="0.15"/>'
        )
    shape = " ".join(
        "{:.1f},{:.1f}".format(
            *polar(cx, cy, radius * max(value, 0.0) / top_value, i * 360 / count)
        )
        for i, value in enumerate(data.values)
    )
    parts.append(
        f'<polygon points="{shape}" fill="{theme.primary}" opacity="0.28" '
        f'stroke="{theme.primary}" stroke-width="2"/>'
    )
    for index, label in enumerate(data.labels):
        x, y = polar(cx, cy, radius + 22, index * 360 / count)
        parts.append(
            _text(
                x,
                y,
                f"{esc(short(label, 14))} {esc(format_value(data.values[index]))}",
                theme.text,
                11,
                text_anchor="middle",
            )
        )
    return parts


def progress_chart(
    data: ChartData, theme: Theme, width: int, height: int, top: int
) -> list[str]:
    value = data.values[0]
    scale = 100.0 if 0 <= value <= 100 else data.max_value
    share = min(max(value, 0.0) / (scale or 1.0), 1.0)
    radius = min((height - top - PAD) / 2, 120)
    cx, cy = width / 2, top + radius + 10
    circumference = 2 * math.pi * radius
    parts = [
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="none" '
        f'stroke="{theme.secondary}" stroke-opacity="0.25" stroke-width="22"/>',
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="none" '
        f'stroke="{theme.primary}" stroke-width="22" stroke-linecap="round" '
        f'stroke-dasharray="{circumference * share:.1f} {circumference:.1f}" '
        f'transform="rotate(-90 {cx:.1f} {cy:.1f})"/>',
        _text(
            cx,
            cy + 10,
            esc(format_value(value)),
            theme.text,
            38,
            text_anchor="middle",
            font_weight="700",
        ),
        _text(
            cx,
            cy + radius + 34,
            esc(short(data.labels[0], 28)),
            theme.text,
            14,
            text_anchor="middle",
        ),
    ]
    return parts


RENDERERS = {
    ChartType.BAR: bar_chart,
    ChartType.GROUPED_BAR: grouped_bar_chart,
    ChartType.STACKED_BAR: stacked_bar_chart,
    ChartType.HORIZONTAL_BAR: horizontal_bar_chart,
    ChartType.LINE: line_chart,
    ChartType.AREA: area_chart,
    ChartType.PIE: pie_chart,
    ChartType.DONUT: donut_chart,
    ChartType.RADAR: radar_chart,
    ChartType.PROGRESS: progress_chart,
}


def render_svg(
    chart_type: ChartType,
    data: ChartData,
    theme: Theme,
    title: str = "",
    description: str = "",
    width: int = 800,
    height: int = 480,
) -> str:
    """Draw one chart as a standalone SVG document."""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<rect width="{width}" height="{height}" fill="{theme.background}"/>',
    ]
    chart_top = PAD
    if title:
        parts.append(
            _text(PAD, 42, esc(title), theme.text, 24, font_weight="700"),
        )
        chart_top = TOP
    if description:
        parts.append(_text(PAD, 68, esc(description), theme.text, 13, opacity="0.72"))
        chart_top = TOP
    renderer = RENDERERS.get(chart_type, bar_chart)
    parts.extend(renderer(data, theme, width, height, chart_top))
    parts.append("</svg>")
    return "".join(parts)
