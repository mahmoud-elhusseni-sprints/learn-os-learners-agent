"""Turn incoming talent data into chart-ready series and pick a chart type.

Two jobs live here, both deterministic and both explainable in one sentence:

1. ``build_chart_data`` reshapes whatever the Talent Intelligence Agent sends
   (a score dict, a list of records, a candidate-by-skill table) into labels
   plus one or more numeric series.
2. ``select_chart_type`` looks at that shape and returns the chart type plus
   the reason, so the choice can always be explained.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from src.app.schemas.models import ChartType, DataKind, VisualizationContext

MONTH_NAMES = {
    "jan",
    "january",
    "feb",
    "february",
    "mar",
    "march",
    "apr",
    "april",
    "may",
    "jun",
    "june",
    "jul",
    "july",
    "aug",
    "august",
    "sep",
    "sept",
    "september",
    "oct",
    "october",
    "nov",
    "november",
    "dec",
    "december",
}
WEEKDAY_NAMES = {
    "mon",
    "monday",
    "tue",
    "tuesday",
    "wed",
    "wednesday",
    "thu",
    "thursday",
    "fri",
    "friday",
    "sat",
    "saturday",
    "sun",
    "sunday",
}
TIME_PATTERNS = (
    re.compile(r"^(19|20)\d{2}$"),
    re.compile(r"^(19|20)\d{2}-\d{1,2}(-\d{1,2})?$"),
    re.compile(r"^q[1-4]([ -](19|20)\d{2})?$"),
    re.compile(r"^(week|wk|day|sprint|month)[ -]?\d{1,3}$"),
)
VALUE_KEYS = ("value", "score", "count", "confidence")
LABEL_KEYS = ("label", "name", "area", "skill", "period", "category")

MANY_CATEGORIES = 8
RADAR_MIN, RADAR_MAX = 3, 8

# Shared layout constants so SVG and PNG place horizontal bars identically.
PAD = 32
TOP = 88
BAR_HEIGHT = 26
ROW_GAP = 18
BOTTOM = 32


def canvas_height(requested: int, row_count: int) -> int:
    """Grow the canvas so stacked rows are never cut off."""
    needed = TOP + row_count * (BAR_HEIGHT + ROW_GAP) - ROW_GAP + BOTTOM
    return max(requested, needed)


@dataclass(frozen=True)
class ChartSeries:
    """One named line/bar set. ``values`` lines up with ``ChartData.labels``."""

    name: str
    values: list[float]


@dataclass(frozen=True)
class ChartData:
    """Labels plus one or more series - everything a renderer needs."""

    labels: list[str]
    series: list[ChartSeries]
    notes: list[str] = field(default_factory=list)

    @property
    def values(self) -> list[float]:
        return self.series[0].values

    @property
    def is_multi_series(self) -> bool:
        return len(self.series) > 1

    @property
    def point_count(self) -> int:
        return len(self.labels)

    @property
    def max_value(self) -> float:
        highest = max((max(s.values) for s in self.series if s.values), default=0.0)
        return max(highest, 0.0) or 1.0

    @property
    def stacked_max(self) -> float:
        totals = [
            sum(max(s.values[i], 0.0) for s in self.series)
            for i in range(self.point_count)
        ]
        return max(max(totals, default=0.0), 0.0) or 1.0

    def total(self) -> float:
        return sum(max(value, 0.0) for value in self.values)

    def note_for(self, index: int) -> str:
        return self.notes[index] if index < len(self.notes) else ""


def is_number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def format_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def _label_of(item: dict[str, Any]) -> str | None:
    for key in LABEL_KEYS:
        if item.get(key) is not None:
            return str(item[key])
    return None


def _single_value_of(item: dict[str, Any]) -> float | None:
    for key in VALUE_KEYS:
        if item.get(key) is not None and is_number(item[key]):
            return float(item[key])
    return None


def _extra_numeric_fields(item: dict[str, Any]) -> dict[str, float]:
    """Numeric fields that are not the label or a standard value key."""
    return {
        key: float(value)
        for key, value in item.items()
        if key not in LABEL_KEYS and key not in VALUE_KEYS and is_number(value)
    }


def _from_flat_mapping(data: dict[Any, Any]) -> ChartData | None:
    pairs = [(str(k), float(v)) for k, v in data.items() if is_number(v)]
    if not pairs:
        return None
    labels = [label for label, _ in pairs]
    values = [value for _, value in pairs]
    return ChartData(labels=labels, series=[ChartSeries("Value", values)])


def _from_nested_mapping(data: dict[Any, Any]) -> ChartData | None:
    """``{"Candidate A": {"Python": 90}, "Candidate B": {...}}`` -> 2 series."""
    nested = {
        str(name): inner
        for name, inner in data.items()
        if isinstance(inner, dict) and any(is_number(v) for v in inner.values())
    }
    if len(nested) < 2:
        return None
    labels: list[str] = []
    for inner in nested.values():
        for key, value in inner.items():
            if is_number(value) and str(key) not in labels:
                labels.append(str(key))
    if not labels:
        return None
    series = [
        ChartSeries(
            name,
            [
                float(inner[label]) if is_number(inner.get(label)) else 0.0
                for label in labels
            ],
        )
        for name, inner in nested.items()
    ]
    return ChartData(labels=labels, series=series)


def _from_known_payload(data: dict[Any, Any]) -> ChartData | None:
    """The Talent Intelligence Agent's strengths/gaps output."""
    strengths = data.get("strengths")
    if isinstance(strengths, list):
        labels, values, notes = [], [], []
        for index, item in enumerate(strengths, start=1):
            if not isinstance(item, dict):
                continue
            labels.append(str(item.get("area") or item.get("skill") or f"Area {index}"))
            evidence = item.get("evidence_ids")
            values.append(float(len(evidence)) if isinstance(evidence, list) else 1.0)
            notes.append(str(item.get("observation") or ""))
        if labels:
            return ChartData(labels, [ChartSeries("Evidence", values)], notes)
    gaps = data.get("gaps")
    if isinstance(gaps, list):
        labels = [
            str(item.get("area") or f"Gap {index}")
            for index, item in enumerate(gaps, start=1)
            if isinstance(item, dict)
        ]
        if labels:
            return ChartData(
                labels,
                [ChartSeries("Gap", [1.0] * len(labels))],
                ["Gap"] * len(labels),
            )
    return None


def _from_records(items: list[Any]) -> ChartData | None:
    """A list of dicts: one value each, or several named values per row."""
    records = [item for item in items if isinstance(item, dict)]
    if not records:
        return None

    labels: list[str] = []
    notes: list[str] = []
    wide_rows: list[dict[str, float]] = []
    simple_values: list[float] = []
    for item in records:
        label = _label_of(item)
        if label is None:
            continue
        extras = _extra_numeric_fields(item)
        single = _single_value_of(item)
        if not extras and single is None:
            continue
        labels.append(label)
        notes.append(str(item.get("observation") or item.get("summary") or ""))
        wide_rows.append(extras)
        simple_values.append(single if single is not None else 0.0)

    if not labels:
        return None

    series_names: list[str] = []
    for row in wide_rows:
        for name in row:
            if name not in series_names:
                series_names.append(name)
    if series_names and all(wide_rows):
        series = [
            ChartSeries(name, [row.get(name, 0.0) for row in wide_rows])
            for name in series_names
        ]
        return ChartData(labels, series, notes)
    return ChartData(labels, [ChartSeries("Value", simple_values)], notes)


def build_chart_data(data: Any) -> ChartData | None:
    """Reshape supported payloads into labels + series, or return None."""
    if isinstance(data, dict):
        return (
            _from_known_payload(data)
            or _from_nested_mapping(data)
            or _from_flat_mapping(data)
        )
    if isinstance(data, list):
        return _from_records(data)
    return None


def looks_chronological(labels: list[str]) -> bool:
    """True when every label reads like a period (month, quarter, year...)."""
    if len(labels) < 3:
        return False
    for raw in labels:
        text = raw.strip().lower()
        stem = re.split(r"[ -]", text)[0]
        if stem in MONTH_NAMES or stem in WEEKDAY_NAMES:
            continue
        if any(pattern.match(text) for pattern in TIME_PATTERNS):
            continue
        return False
    return True


def select_chart_type(
    chart_data: ChartData,
    context: VisualizationContext | None = None,
    requested: ChartType = ChartType.AUTO,
) -> tuple[ChartType, str]:
    """Pick a chart type and say why. Rules are checked top to bottom."""
    if requested is not ChartType.AUTO:
        return requested, f"The caller explicitly requested a {requested.value} chart."

    kind = context.kind if context else None

    if chart_data.is_multi_series:
        if kind is DataKind.COMPOSITION:
            return (
                ChartType.STACKED_BAR,
                f"{len(chart_data.series)} series marked as composition stack into "
                "one bar per category.",
            )
        return (
            ChartType.GROUPED_BAR,
            f"{len(chart_data.series)} comparable series are shown side by side "
            "per category.",
        )

    if chart_data.point_count == 1 or kind is DataKind.KPI:
        return (
            ChartType.PROGRESS,
            "A single metric is shown as a progress meter rather than a chart.",
        )

    if kind is DataKind.TIME_SERIES or looks_chronological(chart_data.labels):
        return (
            ChartType.LINE,
            "Labels read as consecutive periods, so the trend is drawn as a line.",
        )

    if kind is DataKind.COMPOSITION:
        return (
            ChartType.DONUT,
            "The caller marked the values as parts of a whole.",
        )

    if kind is DataKind.PROFILE and RADAR_MIN <= chart_data.point_count <= RADAR_MAX:
        return (
            ChartType.RADAR,
            f"A profile across {chart_data.point_count} dimensions fits a radar "
            "chart.",
        )

    if chart_data.point_count >= MANY_CATEGORIES:
        return (
            ChartType.HORIZONTAL_BAR,
            f"{chart_data.point_count} categories are easier to read as "
            "horizontal bars.",
        )

    return (
        ChartType.BAR,
        f"{chart_data.point_count} categories are compared as vertical bars.",
    )
