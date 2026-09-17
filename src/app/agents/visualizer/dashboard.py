"""Standalone, adaptive HTML dashboard for employer talent intelligence.

The page embeds pre-rendered SVG charts and a few lines of vanilla JavaScript
that only show and hide elements, so every button works with no backend, no
internet, and no CDN. Cards and tabs are chosen from the data that is actually
present - nothing is invented.
"""

from __future__ import annotations

import html

from src.app.schemas.models import (
    ChartType,
    DataKind,
    Theme,
    VisualizationContext,
)

from .chart_data import ChartData, format_value, looks_chronological
from .svg_render import esc, render_svg

# Chart types the viewer may switch between, per family.
SWITCHABLE = {
    ChartType.LINE: (ChartType.LINE, ChartType.AREA),
    ChartType.AREA: (ChartType.AREA, ChartType.LINE),
    ChartType.BAR: (ChartType.BAR, ChartType.HORIZONTAL_BAR),
    ChartType.HORIZONTAL_BAR: (ChartType.HORIZONTAL_BAR, ChartType.BAR),
    ChartType.DONUT: (ChartType.DONUT, ChartType.PIE),
    ChartType.PIE: (ChartType.PIE, ChartType.DONUT),
    ChartType.GROUPED_BAR: (ChartType.GROUPED_BAR, ChartType.STACKED_BAR),
    ChartType.STACKED_BAR: (ChartType.STACKED_BAR, ChartType.GROUPED_BAR),
    ChartType.RADAR: (ChartType.RADAR, ChartType.BAR),
    ChartType.PROGRESS: (ChartType.PROGRESS,),
}

CHART_LABELS = {
    ChartType.BAR: "Bar",
    ChartType.HORIZONTAL_BAR: "Horizontal",
    ChartType.LINE: "Line",
    ChartType.AREA: "Area",
    ChartType.PIE: "Pie",
    ChartType.DONUT: "Donut",
    ChartType.RADAR: "Radar",
    ChartType.GROUPED_BAR: "Grouped",
    ChartType.STACKED_BAR: "Stacked",
    ChartType.PROGRESS: "Progress",
}

STYLE = """
*{box-sizing:border-box;}
body{margin:0;background:var(--background);color:var(--text);
font-family:Arial,Helvetica,sans-serif;padding:24px;}
main{max-width:1080px;margin:0 auto;}
header{margin-bottom:20px;}
h1{font-size:26px;margin:0 0 6px;}
.subtitle{margin:0;opacity:.72;font-size:14px;}
.cards{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
margin:20px 0;}
.card{background:#fff;border:1px solid color-mix(in srgb,var(--text) 12%,white);
border-radius:12px;padding:16px;}
.card dt{font-size:12px;text-transform:uppercase;letter-spacing:.04em;opacity:.65;
margin:0 0 6px;}
.card dd{margin:0;font-size:24px;font-weight:700;}
.card .hint{font-size:12px;font-weight:400;opacity:.7;margin-top:4px;}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}
button{font:inherit;cursor:pointer;border-radius:999px;padding:8px 16px;
border:1px solid color-mix(in srgb,var(--primary) 35%,white);background:#fff;
color:var(--text);transition:background .15s,color .15s;}
button:hover{background:color-mix(in srgb,var(--secondary) 22%,white);}
button:focus-visible{outline:3px solid var(--secondary);outline-offset:2px;}
button.is-active{background:var(--primary);color:#fff;border-color:var(--primary);}
.panel{background:#fff;border:1px solid color-mix(in srgb,var(--text) 12%,white);
border-radius:14px;padding:18px;}
.chart-controls{display:flex;align-items:center;gap:8px;margin-bottom:12px;
flex-wrap:wrap;}
.chart-controls .label{font-size:13px;opacity:.7;}
figure{margin:0;overflow-x:auto;}
svg{max-width:100%;height:auto;}
table{width:100%;border-collapse:collapse;font-size:14px;}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid
color-mix(in srgb,var(--text) 10%,white);}
th{font-size:12px;text-transform:uppercase;opacity:.65;}
.track{height:10px;border-radius:999px;background:color-mix(in srgb,
var(--secondary) 20%,white);overflow:hidden;min-width:90px;}
.bar{height:100%;background:var(--primary);}
.insight{margin:18px 0 0;line-height:1.55;font-size:14px;}
@media(max-width:640px){body{padding:14px;}h1{font-size:21px;}
.card dd{font-size:20px;}}
"""

SCRIPT = """
document.querySelectorAll('.tab').forEach(function (button) {
  button.addEventListener('click', function () {
    var name = button.getAttribute('data-tab');
    document.querySelectorAll('.tab').forEach(function (other) {
      var on = other === button;
      other.classList.toggle('is-active', on);
      other.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('.panel').forEach(function (panel) {
      panel.hidden = panel.id !== 'panel-' + name;
    });
  });
});
document.querySelectorAll('.chart-switch').forEach(function (button) {
  button.addEventListener('click', function () {
    var name = button.getAttribute('data-chart');
    document.querySelectorAll('.chart-switch').forEach(function (other) {
      var on = other === button;
      other.classList.toggle('is-active', on);
      other.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    document.querySelectorAll('.chart-view').forEach(function (view) {
      view.hidden = view.getAttribute('data-chart') !== name;
    });
  });
});
"""


def _card(title: str, value: str, hint: str = "") -> str:
    hint_html = f'<div class="hint">{esc(hint)}</div>' if hint else ""
    return (
        f'<div class="card"><dt>{esc(title)}</dt>'
        f"<dd>{esc(value)}{hint_html}</dd></div>"
    )


def _cards(
    data: ChartData, chart_type: ChartType, context: VisualizationContext | None
) -> str:
    values = data.values
    ranked = sorted(
        zip(data.labels, values, strict=True), key=lambda pair: pair[1], reverse=True
    )
    cards: list[str] = []
    if data.is_multi_series:
        totals = {s.name: sum(s.values) for s in data.series}
        best = max(totals, key=lambda name: totals[name])
        cards = [
            _card("Series compared", str(len(data.series))),
            _card("Categories", str(data.point_count)),
            _card("Highest total", best, f"{format_value(totals[best])} points"),
            _card("Top category", ranked[0][0] if ranked else "-"),
        ]
    elif chart_type is ChartType.PROGRESS:
        cards = [
            _card(data.labels[0], format_value(values[0])),
            _card("Metrics", str(data.point_count)),
        ]
    elif chart_type in (ChartType.LINE, ChartType.AREA):
        change = values[-1] - values[0]
        direction = "increase" if change >= 0 else "decrease"
        peak = ranked[0]
        cards = [
            _card("Latest", format_value(values[-1]), data.labels[-1]),
            _card(
                "Change",
                f"{'+' if change >= 0 else ''}{format_value(change)}",
                f"{direction} since {data.labels[0]}",
            ),
            _card("Peak", format_value(peak[1]), peak[0]),
            _card("Periods", str(data.point_count)),
        ]
    elif chart_type in (ChartType.DONUT, ChartType.PIE):
        total = data.total() or 1.0
        top_label, top_value = ranked[0]
        cards = [
            _card("Total", format_value(data.total())),
            _card("Largest share", top_label, f"{top_value / total * 100:.0f}%"),
            _card("Parts", str(data.point_count)),
        ]
    else:
        average = sum(values) / len(values)
        cards = [
            _card("Average", format_value(average)),
            _card("Strongest", ranked[0][0], format_value(ranked[0][1])),
            _card("Lowest", ranked[-1][0], format_value(ranked[-1][1])),
            _card("Measured", str(data.point_count)),
        ]
    subject = getattr(context, "subject", None)
    if subject:
        cards.insert(0, _card("Subject", str(subject)))
    return '<dl class="cards">' + "".join(cards) + "</dl>"


def _breakdown(data: ChartData) -> str:
    top_value = data.max_value
    header = "".join(f"<th>{esc(s.name)}</th>" for s in data.series)
    rows = []
    for index, label in enumerate(data.labels):
        cells = "".join(
            f"<td>{esc(format_value(s.values[index]))}</td>" for s in data.series
        )
        share = max(data.series[0].values[index], 0.0) / top_value * 100
        note = data.note_for(index)
        note_html = f"<td>{esc(note)}</td>" if note else "<td></td>"
        rows.append(
            f'<tr><th scope="row">{esc(label)}</th>{cells}'
            f'<td><div class="track" title="{share:.0f}% of the highest value">'
            f'<div class="bar" style="width:{share:.0f}%"></div></div></td>'
            f"{note_html}</tr>"
        )
    return (
        "<table><thead><tr><th>Item</th>"
        f"{header}<th>Relative</th><th>Note</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _chart_views(
    data: ChartData, theme: Theme, chart_type: ChartType, width: int, height: int
) -> tuple[str, str]:
    options = SWITCHABLE.get(chart_type, (chart_type,))
    buttons, views = [], []
    for index, option in enumerate(options):
        active = " is-active" if index == 0 else ""
        buttons.append(
            f'<button type="button" class="chart-switch{active}" '
            f'data-chart="{option.value}" aria-pressed="{str(index == 0).lower()}">'
            f"{CHART_LABELS[option]}</button>"
        )
        hidden = "" if index == 0 else " hidden"
        views.append(
            f'<figure class="chart-view" data-chart="{option.value}"{hidden}>'
            f"{render_svg(option, data, theme, width=width, height=height)}"
            f"</figure>"
        )
    controls = ""
    if len(options) > 1:
        controls = (
            '<div class="chart-controls"><span class="label">Chart:</span>'
            + "".join(buttons)
            + "</div>"
        )
    return controls, "".join(views)


def _tabs(
    data: ChartData, chart_type: ChartType, context: VisualizationContext | None
) -> list[tuple[str, str]]:
    kind = context.kind if context else None
    tabs = [("overview", "Overview")]
    if data.is_multi_series:
        tabs.append(("comparison", "Comparison"))
    elif chart_type in (ChartType.LINE, ChartType.AREA) or looks_chronological(
        data.labels
    ):
        tabs.append(("trends", "Trends"))
    elif kind is DataKind.COMPOSITION or chart_type in (
        ChartType.DONUT,
        ChartType.PIE,
    ):
        tabs.append(("distribution", "Distribution"))
    else:
        tabs.append(("skills", "Skills"))
    tabs.append(("breakdown", "Breakdown"))
    return tabs


def _detail_panel(name: str, data: ChartData, chart_type: ChartType) -> str:
    values = data.values
    if name == "comparison":
        lines = [
            f"<li><strong>{esc(series.name)}</strong>: total "
            f"{esc(format_value(sum(series.values)))}, best on "
            f"{esc(data.labels[series.values.index(max(series.values))])}</li>"
            for series in data.series
        ]
        return f"<ul>{''.join(lines)}</ul>"
    if name == "trends":
        steps = [
            f"<li>{esc(data.labels[i])}: {esc(format_value(values[i]))} "
            f"({'+' if values[i] - values[i - 1] >= 0 else ''}"
            f"{esc(format_value(values[i] - values[i - 1]))})</li>"
            for i in range(1, len(values))
        ]
        first = f"<li>{esc(data.labels[0])}: {esc(format_value(values[0]))}</li>"
        return f"<ul>{first}{''.join(steps)}</ul>"
    if name == "distribution":
        total = data.total() or 1.0
        shares = [
            f"<li>{esc(label)}: {esc(format_value(value))} "
            f"({value / total * 100:.0f}%)</li>"
            for label, value in zip(data.labels, values, strict=True)
        ]
        return f"<ul>{''.join(shares)}</ul>"
    ranked = sorted(
        zip(data.labels, values, strict=True), key=lambda pair: pair[1], reverse=True
    )
    items = [
        f"<li>{esc(label)}: {esc(format_value(value))}</li>" for label, value in ranked
    ]
    return f"<ul>{''.join(items)}</ul>"


def render_dashboard(
    data: ChartData,
    theme: Theme,
    chart_type: ChartType,
    title: str = "Talent Intelligence Dashboard",
    description: str = "",
    context: VisualizationContext | None = None,
    commentary: str = "",
    width: int = 820,
    height: int = 420,
) -> str:
    """Build the whole standalone dashboard page."""
    controls, views = _chart_views(data, theme, chart_type, width, height)
    tabs = _tabs(data, chart_type, context)
    nav = "".join(
        f'<button type="button" class="tab{" is-active" if index == 0 else ""}" '
        f'data-tab="{name}" role="tab" '
        f'aria-selected="{str(index == 0).lower()}">{esc(label)}</button>'
        for index, (name, label) in enumerate(tabs)
    )
    panels = [f'<section class="panel" id="panel-overview">{controls}{views}</section>']
    for name, label in tabs[1:]:
        body = (
            _breakdown(data)
            if name == "breakdown"
            else _detail_panel(name, data, chart_type)
        )
        panels.append(
            f'<section class="panel" id="panel-{name}" hidden>'
            f"<h2>{esc(label)}</h2>{body}</section>"
        )
    insight = f'<p class="insight">{esc(commentary)}</p>' if commentary else ""
    subtitle = html.escape(description) if description else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n<style>\n"
        f":root{{--primary:{theme.primary};--secondary:{theme.secondary};"
        f"--accent:{theme.accent};--background:{theme.background};"
        f"--text:{theme.text};}}\n{STYLE}</style>\n</head>\n"
        "<body>\n<main>\n"
        f"<header><h1>{esc(title)}</h1>"
        f'<p class="subtitle">{subtitle}</p></header>\n'
        f"{_cards(data, chart_type, context)}\n"
        f'<nav role="tablist">{nav}</nav>\n'
        f"{''.join(panels)}\n"
        f"{insight}\n"
        f"</main>\n<script>{SCRIPT}</script>\n</body>\n</html>\n"
    )
