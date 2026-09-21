"""PNG renderers drawn with Pillow: shapes *and* text in one image.

Same flow as before - the agent picks the chart type, this module draws it and
returns PNG bytes. Pillow only replaces the hand-rolled pixel fills, so titles,
labels, values and legends can be measured and placed without clipping.

Fonts: Pillow's built-in default font is used at several sizes, so nothing
depends on a font file being installed on the machine or in CI.

RADAR is still not drawn here; the agent falls back to bars and says so.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from src.app.schemas.models import ChartType, Theme

from .chart_data import ChartData, format_value

PNG_SUPPORTED = frozenset(
    {
        ChartType.BAR,
        ChartType.GROUPED_BAR,
        ChartType.STACKED_BAR,
        ChartType.HORIZONTAL_BAR,
        ChartType.LINE,
        ChartType.AREA,
        ChartType.PIE,
        ChartType.DONUT,
        ChartType.PROGRESS,
    }
)

PAD = 28
TITLE_SIZE = 24
SUBTITLE_SIZE = 14
LABEL_SIZE = 14
VALUE_SIZE = 13
TICK_SIZE = 12
SCORE_SIZE = 46
MAX_X_LABELS = 10
# Pillow's built-in font has no "—" or "…" glyph, so PNG text stays ASCII.
ELLIPSIS = "..."
LEGEND_SEPARATOR = " - "

RGB = tuple[int, int, int]
Font = ImageFont.FreeTypeFont | ImageFont.ImageFont


def _font(size: int) -> Font:
    """Pillow's bundled font at the requested size (portable, no font files)."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no size argument
        return ImageFont.load_default()


def hex_to_rgb(value: str) -> RGB:
    raw = bytes.fromhex(value.lstrip("#"))
    return raw[0], raw[1], raw[2]


def blend(color: RGB, background: RGB, opacity: float) -> RGB:
    mixed = tuple(
        int(c * opacity + b * (1 - opacity))
        for c, b in zip(color, background, strict=True)
    )
    return mixed[0], mixed[1], mixed[2]


def series_rgb(index: int, theme: Theme, background: RGB) -> RGB:
    palette = (theme.primary, theme.secondary, theme.accent)
    opacity = max(1.0 - 0.18 * (index // 2), 0.4)
    return blend(hex_to_rgb(palette[index % len(palette)]), background, opacity)


def _size(draw: ImageDraw.ImageDraw, text: str, font: Font) -> tuple[int, int, int]:
    """Return (width, height, top offset) of the rendered text."""
    box = draw.textbbox((0, 0), text, font=font)
    return int(box[2] - box[0]), int(box[3] - box[1]), int(box[1])


def _width_of(draw: ImageDraw.ImageDraw, text: str, font: Font) -> int:
    return _size(draw, text, font)[0]


def _fit(draw: ImageDraw.ImageDraw, text: str, font: Font, limit: float) -> str:
    """Shorten with an ellipsis until the text fits inside ``limit`` pixels."""
    if _width_of(draw, text, font) <= limit:
        return text
    trimmed = text
    while trimmed and _width_of(draw, trimmed + ELLIPSIS, font) > limit:
        trimmed = trimmed[:-1]
    return trimmed + ELLIPSIS if trimmed else ""


def _draw_header(
    draw: ImageDraw.ImageDraw,
    theme: Theme,
    width: int,
    title: str,
    description: str,
) -> int:
    """Draw the title block and return the y where the chart may start."""
    y = PAD
    text_color = hex_to_rgb(theme.text)
    if title:
        font = _font(TITLE_SIZE)
        draw.text(
            (PAD, y),
            _fit(draw, title, font, width - 2 * PAD),
            font=font,
            fill=text_color,
        )
        y += TITLE_SIZE + 8
    if description:
        font = _font(SUBTITLE_SIZE)
        draw.text(
            (PAD, y),
            _fit(draw, description, font, width - 2 * PAD),
            font=font,
            fill=blend(text_color, hex_to_rgb(theme.background), 0.72),
        )
        y += SUBTITLE_SIZE + 8
    return y + (12 if y > PAD else 0)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    names: list[str],
    theme: Theme,
    background: RGB,
    x: int,
    y: int,
    limit: float,
) -> int:
    """One legend row per name; returns the y below the legend."""
    font = _font(LABEL_SIZE)
    for index, name in enumerate(names):
        draw.rectangle(
            [x, y + 3, x + 12, y + 15], fill=series_rgb(index, theme, background)
        )
        draw.text(
            (x + 20, y),
            _fit(draw, name, font, limit - 20),
            font=font,
            fill=hex_to_rgb(theme.text),
        )
        y += LABEL_SIZE + 10
    return y


def _y_axis(
    draw: ImageDraw.ImageDraw,
    theme: Theme,
    left: float,
    top: float,
    right: float,
    bottom: float,
    top_value: float,
) -> None:
    font = _font(TICK_SIZE)
    grid = blend(hex_to_rgb(theme.text), hex_to_rgb(theme.background), 0.14)
    for step in range(5):
        y = bottom - (bottom - top) * step / 4
        draw.line([(left, y), (right, y)], fill=grid, width=1)
        label = format_value(top_value * step / 4)
        text_width, text_height, offset = _size(draw, label, font)
        draw.text(
            (left - 8 - text_width, y - text_height / 2 - offset),
            label,
            font=font,
            fill=blend(hex_to_rgb(theme.text), hex_to_rgb(theme.background), 0.75),
        )


def _tick_margin(draw: ImageDraw.ImageDraw, top_value: float) -> int:
    font = _font(TICK_SIZE)
    widest = max(
        _width_of(draw, format_value(top_value * step / 4), font) for step in range(5)
    )
    return PAD + widest + 10


def _vertical_bars(
    draw: ImageDraw.ImageDraw,
    data: ChartData,
    theme: Theme,
    width: int,
    height: int,
    top: int,
    background: RGB,
    stacked: bool,
) -> None:
    label_font, value_font = _font(LABEL_SIZE), _font(VALUE_SIZE)
    top_value = data.stacked_max if stacked else data.max_value
    left = _tick_margin(draw, top_value)
    right: float = width - PAD
    if data.is_multi_series:
        legend_width = (
            max(_width_of(draw, s.name, label_font) for s in data.series) + 34
        )
        right -= min(legend_width, width * 0.28)
        _draw_legend(
            draw,
            [s.name for s in data.series],
            theme,
            background,
            int(right + 16),
            top,
            width - right - 24,
        )
    bottom = height - PAD - LABEL_SIZE - 10
    _y_axis(draw, theme, left, top, right, bottom, top_value)
    draw.line([(left, bottom), (right, bottom)], fill=hex_to_rgb(theme.text), width=2)

    band = (right - left) / max(data.point_count, 1)
    count = len(data.series)
    for index, label in enumerate(data.labels):
        band_x = left + index * band
        if stacked:
            cursor: float = bottom
            for s_index, series in enumerate(data.series):
                bar = (max(series.values[index], 0.0) / top_value) * (bottom - top)
                draw.rectangle(
                    [band_x + band * 0.2, cursor - bar, band_x + band * 0.8, cursor],
                    fill=series_rgb(s_index, theme, background),
                )
                cursor -= bar
        else:
            slot = band * 0.6 / count
            for s_index, series in enumerate(data.series):
                value = max(series.values[index], 0.0)
                bar = (value / top_value) * (bottom - top)
                x = band_x + band * 0.2 + s_index * slot
                draw.rectangle(
                    [x, bottom - bar, x + max(slot - 2, 2), bottom],
                    fill=series_rgb(s_index, theme, background),
                )
                text = format_value(value)
                if _width_of(draw, text, value_font) <= slot:
                    draw.text(
                        (x + slot / 2, bottom - bar - 6),
                        text,
                        font=value_font,
                        fill=hex_to_rgb(theme.text),
                        anchor="mb",
                    )
        draw.text(
            (band_x + band / 2, bottom + 8),
            _fit(draw, label, label_font, band - 4),
            font=label_font,
            fill=hex_to_rgb(theme.text),
            anchor="ma",
        )


def _horizontal_bars(
    draw: ImageDraw.ImageDraw,
    data: ChartData,
    theme: Theme,
    width: int,
    height: int,
    top: int,
    background: RGB,
) -> None:
    label_font, value_font = _font(LABEL_SIZE), _font(VALUE_SIZE)
    label_space = min(
        max(_width_of(draw, label, label_font) for label in data.labels) + 16,
        width * 0.38,
    )
    left = PAD + label_space
    value_space = (
        max(_width_of(draw, format_value(v), value_font) for v in data.values) + 12
    )
    track_width = max(20.0, width - left - PAD - value_space)
    rows = max(data.point_count, 1)
    row_height = (height - top - PAD) / rows
    bar_height = min(row_height * 0.62, 30)
    top_value = data.max_value
    track_color = blend(hex_to_rgb(theme.secondary), hex_to_rgb(theme.background), 0.25)
    for index, value in enumerate(data.values):
        center = top + row_height * (index + 0.5)
        y0, y1 = center - bar_height / 2, center + bar_height / 2
        draw.rectangle([left, y0, left + track_width, y1], fill=track_color)
        length = (max(value, 0.0) / top_value) * track_width
        draw.rectangle([left, y0, left + length, y1], fill=hex_to_rgb(theme.primary))
        draw.text(
            (left - 10, center),
            _fit(draw, data.labels[index], label_font, label_space - 16),
            font=label_font,
            fill=hex_to_rgb(theme.text),
            anchor="rm",
        )
        draw.text(
            (left + length + 8, center),
            format_value(value),
            font=value_font,
            fill=hex_to_rgb(theme.text),
            anchor="lm",
        )


def _x_label_stride(count: int, slot: float, widest: int) -> int:
    """Draw every Nth x label so neighbouring labels can never overlap."""
    by_width = -(-(widest + 12) // max(int(slot), 1))
    return max(1, -(-count // MAX_X_LABELS), by_width)


def _line_like(
    draw: ImageDraw.ImageDraw,
    data: ChartData,
    theme: Theme,
    width: int,
    height: int,
    top: int,
    background: RGB,
    area: bool,
) -> None:
    label_font, value_font = _font(LABEL_SIZE), _font(VALUE_SIZE)
    top_value = data.max_value
    left = _tick_margin(draw, top_value)
    right: float = width - PAD
    bottom = height - PAD - LABEL_SIZE - 10
    plot_top = top + (VALUE_SIZE + 8)
    _y_axis(draw, theme, left, plot_top, right, bottom, top_value)

    steps = max(data.point_count - 1, 1)
    points = [
        (
            left + (right - left) * index / steps,
            bottom - (max(value, 0.0) / top_value) * (bottom - plot_top),
        )
        for index, value in enumerate(data.values)
    ]
    if area:
        shade = blend(hex_to_rgb(theme.primary), hex_to_rgb(theme.background), 0.22)
        draw.polygon(
            [(points[0][0], bottom), *points, (points[-1][0], bottom)], fill=shade
        )
    draw.line(points, fill=hex_to_rgb(theme.primary), width=3, joint="curve")
    draw.line([(left, bottom), (right, bottom)], fill=hex_to_rgb(theme.text), width=2)

    slot = (right - left) / max(data.point_count, 1)
    widest = max(_width_of(draw, label, label_font) for label in data.labels)
    every = _x_label_stride(data.point_count, slot, widest)
    for index, (x, y) in enumerate(points):
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=hex_to_rgb(theme.primary))
        if data.point_count <= MAX_X_LABELS:
            value_text = format_value(data.values[index])
            value_half = _width_of(draw, value_text, value_font) / 2
            draw.text(
                (min(max(x, left + value_half), right - value_half), y - 8),
                value_text,
                font=value_font,
                fill=hex_to_rgb(theme.text),
                anchor="mb",
            )
        if index % every == 0:
            text = _fit(draw, data.labels[index], label_font, slot * every - 8)
            half = _width_of(draw, text, label_font) / 2
            centre = min(max(x, PAD + half), width - PAD - half)
            draw.text(
                (centre, bottom + 8),
                text,
                font=label_font,
                fill=hex_to_rgb(theme.text),
                anchor="ma",
            )


def _pie_like(
    draw: ImageDraw.ImageDraw,
    data: ChartData,
    theme: Theme,
    width: int,
    height: int,
    top: int,
    background: RGB,
    hole: float,
) -> None:
    label_font = _font(LABEL_SIZE)
    total = data.total() or 1.0
    entries = [
        f"{label}{LEGEND_SEPARATOR}{max(value, 0.0) / total * 100:.0f}%"
        for label, value in zip(data.labels, data.values, strict=True)
    ]
    legend_width = min(
        max(_width_of(draw, entry, label_font) for entry in entries) + 40, width * 0.42
    )
    radius = min((height - top - PAD) / 2, (width - legend_width - 2 * PAD) / 2)
    cx, cy = PAD + radius, top + radius
    angle = -90.0
    for index, value in enumerate(data.values):
        sweep = max(value, 0.0) / total * 360.0
        draw.pieslice(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            angle,
            angle + sweep,
            fill=series_rgb(index, theme, background),
        )
        angle += sweep
    if hole:
        inner = radius * hole
        draw.ellipse(
            [cx - inner, cy - inner, cx + inner, cy + inner],
            fill=hex_to_rgb(theme.background),
        )
        draw.text(
            (cx, cy),
            format_value(data.total()),
            font=_font(SCORE_SIZE - 14),
            fill=hex_to_rgb(theme.text),
            anchor="mm",
        )
    _draw_legend(
        draw,
        entries,
        theme,
        background,
        int(cx + radius + 24),
        int(max(top, cy - len(entries) * (LABEL_SIZE + 10) / 2)),
        legend_width,
    )


def _progress(
    draw: ImageDraw.ImageDraw,
    data: ChartData,
    theme: Theme,
    width: int,
    height: int,
    top: int,
    background: RGB,
) -> None:
    value = data.values[0]
    percentage = 0 <= value <= 100
    scale = 100.0 if percentage else data.max_value
    share = min(max(value, 0.0) / (scale or 1.0), 1.0)
    radius = min((height - top - PAD - LABEL_SIZE - 12) / 2, width / 4)
    cx, cy = width / 2, top + radius
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.pieslice(
        box,
        -90,
        270,
        fill=blend(hex_to_rgb(theme.secondary), hex_to_rgb(theme.background), 0.25),
    )
    draw.pieslice(box, -90, -90 + share * 360, fill=hex_to_rgb(theme.primary))
    inner = radius * 0.62
    draw.ellipse(
        [cx - inner, cy - inner, cx + inner, cy + inner],
        fill=hex_to_rgb(theme.background),
    )
    score = format_value(value) + ("%" if percentage else "")
    draw.text(
        (cx, cy),
        score,
        font=_font(SCORE_SIZE),
        fill=hex_to_rgb(theme.text),
        anchor="mm",
    )
    label_font = _font(LABEL_SIZE)
    draw.text(
        (cx, cy + radius + 12),
        _fit(draw, data.labels[0], label_font, width - 2 * PAD),
        font=label_font,
        fill=hex_to_rgb(theme.text),
        anchor="ma",
    )


def render_png(
    chart_type: ChartType,
    data: ChartData,
    theme: Theme,
    width: int = 800,
    height: int = 480,
    title: str = "",
    description: str = "",
) -> bytes:
    """Draw one labelled chart and return real PNG bytes."""
    background = hex_to_rgb(theme.background)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    top = _draw_header(draw, theme, width, title, description)

    if chart_type is ChartType.HORIZONTAL_BAR:
        _horizontal_bars(draw, data, theme, width, height, top, background)
    elif chart_type is ChartType.LINE:
        _line_like(draw, data, theme, width, height, top, background, area=False)
    elif chart_type is ChartType.AREA:
        _line_like(draw, data, theme, width, height, top, background, area=True)
    elif chart_type is ChartType.PIE:
        _pie_like(draw, data, theme, width, height, top, background, hole=0.0)
    elif chart_type is ChartType.DONUT:
        _pie_like(draw, data, theme, width, height, top, background, hole=0.58)
    elif chart_type is ChartType.PROGRESS:
        _progress(draw, data, theme, width, height, top, background)
    elif chart_type is ChartType.STACKED_BAR:
        _vertical_bars(draw, data, theme, width, height, top, background, stacked=True)
    else:
        _vertical_bars(draw, data, theme, width, height, top, background, stacked=False)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
