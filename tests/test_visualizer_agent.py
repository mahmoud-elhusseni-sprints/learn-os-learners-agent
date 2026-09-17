import base64
import io
import json
import re
import urllib.error
import xml.etree.ElementTree as ET

import pytest
from PIL import Image
from pydantic import ValidationError

from src.app.agents.visualizer import (
    SPRINTS_DEFAULT_THEME,
    ChartType,
    VisualizationFormat,
    VisualizationRequest,
    VisualizationResponse,
    VisualizerAgent,
)
from src.app.agents.visualizer.png_render import _x_label_stride

GOOGLE_MODULE = "src.app.agents.visualizer.google_image"

SKILLS = {"Python": 90, "FastAPI": 70, "SQL": 45}
TREND = {"Jan": 55, "Feb": 63, "Mar": 71, "Apr": 78, "May": 85}
SPLIT = {"Technical": 50, "Communication": 30, "Leadership": 20}
CANDIDATES = {
    "Candidate A": {"Python": 90, "SQL": 80, "Communication": 75},
    "Candidate B": {"Python": 70, "SQL": 85, "Communication": 90},
}
MANY = {f"Skill {index}": 50 + index for index in range(10)}


def render(data=SKILLS, **kwargs):
    return VisualizerAgent().visualize(VisualizationRequest(data=data, **kwargs))


def open_png(asset):
    """Real PNG bytes in, decoded RGB image out."""
    assert asset.startswith(b"\x89PNG\r\n\x1a\n")
    return Image.open(io.BytesIO(asset)).convert("RGB")


def pixel(image, x, y):
    return "%02X%02X%02X" % image.getpixel((x, y))


def colors_used(image):
    return {"%02X%02X%02X" % color for _, color in image.getcolors(maxcolors=500000)}


def ink(image, box, background="FBFBFD"):
    """Count non-background pixels in a region - how we detect drawn text."""
    return sum(
        1 for color in image.crop(box).getdata() if "%02X%02X%02X" % color != background
    )


def tags_in(svg):
    return set(re.findall(r"<(\w+)", svg))


# --- themes -----------------------------------------------------------------


def test_missing_theme_uses_sprints_default_palette():
    response = render(title="Skill scores")

    assert response.success is True
    assert response.metadata["theme"] == SPRINTS_DEFAULT_THEME.model_dump()
    assert response.metadata["theme"]["primary"] == "#004EFF"


def test_fallback_palette_uses_only_documented_sprints_colors():
    official = {"#004EFF", "#33D7D1", "#FBFBFD"}

    assert SPRINTS_DEFAULT_THEME.primary == "#004EFF"
    assert SPRINTS_DEFAULT_THEME.accent == "#33D7D1"
    assert SPRINTS_DEFAULT_THEME.background == "#FBFBFD"
    assert set(SPRINTS_DEFAULT_THEME.model_dump().values()) <= official


@pytest.mark.parametrize("theme", [None, {}])
def test_null_or_empty_theme_falls_back_to_sprints_colors(theme):
    response = render(theme=theme, format="svg")

    assert response.metadata["theme"] == SPRINTS_DEFAULT_THEME.model_dump()
    assert 'fill="#004EFF"' in response.content
    assert 'fill="#FBFBFD"' in response.content


def test_custom_theme_overrides_colors_in_every_format():
    theme = {"primary": "#FF0000", "background": "#000000"}

    svg = render(theme=theme, format="svg").content
    page = render(theme=theme, format="html").content
    png = render(theme=theme, format="png", chart_type="horizontal_bar").asset

    assert 'rx="4" fill="#FF0000"' in svg and 'rx="4" fill="#004EFF"' not in svg
    assert "--primary:#FF0000" in page and "--secondary:#33D7D1" in page
    image = open_png(png)
    assert pixel(image, 0, 0) == "000000"
    assert "FF0000" in colors_used(image)


@pytest.mark.parametrize(
    "chart_type", ["bar", "line", "donut", "radar", "progress", "horizontal_bar"]
)
def test_every_chart_type_respects_a_custom_theme(chart_type):
    theme = {"primary": "#FF0000", "text": "#111111", "background": "#FFFFFF"}

    svg = render(theme=theme, chart_type=chart_type, format="svg").content

    assert "#FF0000" in svg
    assert "#004EFF" not in svg
    assert "#FBFBFD" not in svg


@pytest.mark.parametrize(
    "theme",
    [{"primary": "red;}</style><script>alert(1)</script>"}, {"bogus": "#000000"}],
)
def test_invalid_theme_is_rejected_by_the_contract(theme):
    with pytest.raises(ValidationError):
        VisualizationRequest(data=SKILLS, theme=theme)


# --- chart selection ---------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "context", "expected"),
    [
        (SKILLS, None, ChartType.BAR),
        (MANY, None, ChartType.HORIZONTAL_BAR),
        (TREND, None, ChartType.LINE),
        ({"Overall Score": 87}, None, ChartType.PROGRESS),
        (CANDIDATES, None, ChartType.GROUPED_BAR),
        (SPLIT, {"kind": "composition"}, ChartType.DONUT),
        (CANDIDATES, {"kind": "composition"}, ChartType.STACKED_BAR),
        (SPLIT, {"kind": "profile"}, ChartType.RADAR),
        (SKILLS, {"kind": "kpi"}, ChartType.PROGRESS),
        ({"2021": 4, "2022": 6, "2023": 9}, None, ChartType.LINE),
    ],
)
def test_automatic_chart_selection(data, context, expected):
    response = render(data=data, context=context, format="svg")

    assert response.metadata["selected_chart_type"] == expected.value
    assert response.metadata["selection_reason"]


def test_values_summing_to_100_are_not_a_pie_without_context():
    response = render(data=SPLIT, format="svg")

    assert response.metadata["selected_chart_type"] == ChartType.BAR.value


@pytest.mark.parametrize(
    "chart_type", [c for c in ChartType if c is not ChartType.AUTO]
)
def test_explicit_chart_type_is_always_respected(chart_type):
    response = render(data=CANDIDATES, chart_type=chart_type, format="svg")

    assert response.success is True
    assert response.metadata["selected_chart_type"] == chart_type.value
    assert "explicitly requested" in response.metadata["selection_reason"]


def test_requests_without_chart_type_still_work():
    response = render(title="Skill scores", format="svg")

    assert response.success is True
    assert response.metadata["selected_chart_type"] == ChartType.BAR.value


# --- SVG ---------------------------------------------------------------------


def test_svg_renderer_returns_parseable_svg_with_labels_and_values():
    response = render(
        data={"Python": 90, "FastAPI": 70},
        title="Skill scores",
        format=VisualizationFormat.SVG,
    )

    assert response.success is True
    assert response.format == VisualizationFormat.SVG
    root = ET.fromstring(response.content)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert "Skill scores" in response.content
    assert "Python" in response.content
    assert ">90<" in response.content


@pytest.mark.parametrize(
    ("chart_type", "required_tags"),
    [
        ("bar", {"rect"}),
        ("horizontal_bar", {"rect"}),
        ("line", {"polyline", "circle"}),
        ("area", {"polygon", "polyline"}),
        ("pie", {"path"}),
        ("donut", {"path", "circle"}),
        ("radar", {"polygon"}),
        ("progress", {"circle"}),
    ],
)
def test_each_svg_chart_type_uses_its_own_geometry(chart_type, required_tags):
    svg = render(data=SPLIT, chart_type=chart_type, format="svg").content

    ET.fromstring(svg)
    assert required_tags <= tags_in(svg)


def test_svg_chart_types_are_not_all_the_same_drawing():
    drawings = {
        chart_type: render(data=SPLIT, chart_type=chart_type, format="svg").content
        for chart_type in ("bar", "line", "pie", "radar", "progress")
    }

    assert len(set(drawings.values())) == len(drawings)
    assert "polyline" not in drawings["bar"]
    assert "<path" not in drawings["line"]


def test_line_chart_scales_points_inside_the_canvas():
    svg = render(data=TREND, chart_type="line", format="svg", height=400).content

    points = re.search(r'<polyline points="([^"]+)"', svg).group(1).split()
    ys = [float(point.split(",")[1]) for point in points]
    assert len(points) == len(TREND)
    assert all(0 < y < 400 for y in ys)
    assert ys[0] > ys[-1]  # values rise, so the line goes up


@pytest.mark.parametrize("fmt", ["svg", "html"])
def test_labels_are_escaped(fmt):
    response = render(data={"<script>alert(1)</script>": 5}, format=fmt)

    assert "<script>alert(1)" not in response.content
    assert "&lt;script&gt;" in response.content


def test_zero_scores_are_kept_and_negative_bars_are_clamped():
    response = render(
        data=[
            {"skill": "Python", "score": 80},
            {"skill": "Docker", "score": 0},
            {"skill": "Legacy", "score": -5},
        ],
        format="svg",
    )

    assert response.metadata["row_count"] == 3
    assert "Docker" in response.content
    assert 'width="-' not in response.content
    assert 'height="-' not in response.content


@pytest.mark.parametrize("fmt", ["svg", "png"])
def test_canvas_grows_so_many_rows_are_not_cut_off(fmt):
    response = render(data={f"Skill {i}": i + 1 for i in range(15)}, format=fmt)

    height = response.metadata["height"]
    last_bar_bottom = 88 + 14 * (26 + 18) + 26
    assert response.metadata["selected_chart_type"] == "horizontal_bar"
    assert height >= last_bar_bottom
    if fmt == "png":
        assert open_png(response.asset).height == height
    else:
        assert f'height="{height}"' in response.content


# --- PNG ---------------------------------------------------------------------


def test_png_renderer_returns_a_real_image_with_theme_colors():
    response = render(
        data={"Python": 90}, format="png", chart_type="horizontal_bar", width=400
    )

    assert response.success is True
    assert response.format == VisualizationFormat.PNG
    assert response.metadata["content_type"] == "image/png"
    image = open_png(response.asset)
    assert image.size == (400, 480)
    assert pixel(image, 0, 0) == "FBFBFD"
    assert "004EFF" in colors_used(image)


@pytest.mark.parametrize(
    "chart_type",
    ["bar", "horizontal_bar", "line", "area", "pie", "donut", "progress"],
)
def test_supported_png_chart_types_draw_real_pixels(chart_type):
    response = render(data=SPLIT, chart_type=chart_type, format="png")

    image = open_png(response.asset)
    used = colors_used(image)
    assert response.metadata["selected_chart_type"] == chart_type
    assert "004EFF" in used
    assert len(used) > 3


def test_png_chart_types_produce_different_images():
    images = {
        chart_type: render(data=SPLIT, chart_type=chart_type, format="png").asset
        for chart_type in ("bar", "horizontal_bar", "line", "donut", "progress")
    }

    assert len(set(images.values())) == len(images)


def test_png_says_so_when_a_chart_type_cannot_be_drawn():
    response = render(data=SPLIT, chart_type="radar", format="png")

    assert response.success is True
    assert response.metadata["requested_chart_type"] == "radar"
    assert response.metadata["selected_chart_type"] == "bar"
    assert "cannot be drawn as PNG" in response.metadata["fallback_reason"]
    assert "cannot be drawn as PNG" in response.commentary


@pytest.mark.parametrize(
    "chart_type", ["bar", "horizontal_bar", "line", "donut", "progress"]
)
def test_png_charts_draw_a_title(chart_type):
    image = open_png(
        render(
            data=SPLIT, chart_type=chart_type, format="png", title="Skill Performance"
        ).asset
    )

    assert ink(image, (0, 24, image.width, 58)) > 200


def test_png_bar_chart_draws_category_labels_under_the_bars():
    image = open_png(render(data=SKILLS, chart_type="bar", format="png").asset)

    assert ink(image, (0, image.height - 48, image.width, image.height - 24)) > 100


def test_png_label_text_is_really_drawn():
    """Same numbers, different label text -> different pixels."""
    python = render(data={"Python": 90, "SQL": 80}, chart_type="bar", format="png")
    ruby = render(data={"Ruby": 90, "SQL": 80}, chart_type="bar", format="png")

    assert python.asset != ruby.asset


def test_png_progress_label_text_is_really_drawn():
    score = render(data={"Overall Score": 87}, chart_type="progress", format="png")
    other = render(data={"Readiness": 87}, chart_type="progress", format="png")

    assert score.asset != other.asset


def test_png_donut_draws_a_legend_beside_the_ring():
    image = open_png(
        render(data=SPLIT, chart_type="donut", format="png", width=900).asset
    )

    assert ink(image, (int(image.width * 0.62), 0, image.width, image.height)) > 100


def test_png_grouped_bars_draw_the_series_names():
    a = render(data=CANDIDATES, chart_type="grouped_bar", format="png").asset
    renamed = {
        "Team Alpha": CANDIDATES["Candidate A"],
        "Team Beta": CANDIDATES["Candidate B"],
    }
    b = render(data=renamed, chart_type="grouped_bar", format="png").asset

    assert a != b


@pytest.mark.parametrize("chart_type", ["bar", "horizontal_bar", "line", "donut"])
def test_png_long_labels_never_touch_the_canvas_edge(chart_type):
    data = {
        "Extremely long behavioural engagement effort signal label": 70,
        "Another quite long communication clarity dimension": 55,
        "Short": 40,
    }

    image = open_png(
        render(
            data=data,
            chart_type=chart_type,
            format="png",
            title="A very long dashboard title that must be trimmed to fit the canvas",
            width=800,
            height=420,
        ).asset
    )

    assert ink(image, (0, 0, image.width, 2)) == 0
    assert ink(image, (0, image.height - 2, image.width, image.height)) == 0
    assert ink(image, (0, 0, 2, image.height)) == 0
    assert ink(image, (image.width - 2, 0, image.width, image.height)) == 0


def test_x_label_stride_skips_labels_that_would_overlap():
    assert _x_label_stride(count=5, slot=160, widest=40) == 1
    assert _x_label_stride(count=4, slot=170, widest=190) == 2
    assert _x_label_stride(count=40, slot=18, widest=30) >= 4


def test_png_response_survives_json_round_trip():
    response = render(format="png")

    restored = VisualizationResponse.model_validate_json(response.model_dump_json())
    assert restored.asset == response.asset


# --- HTML dashboard ----------------------------------------------------------


def test_html_renderer_returns_standalone_html_with_theme():
    response = render(
        data={
            "strengths": [
                {
                    "area": "behavioral_engagement.effort_signals",
                    "observation": "Demonstrated steady follow-through.",
                }
            ]
        },
        title="Talent snapshot",
        description="Observed employer-facing signals",
        format="html",
    )

    assert response.success is True
    assert response.format == VisualizationFormat.HTML
    assert response.content.startswith("<!doctype html>")
    assert "Talent snapshot" in response.content
    assert "behavioral_engagement.effort_signals" in response.content
    assert "#004EFF" in response.content


def test_dashboard_loads_nothing_from_the_internet():
    page = render(format="html").content

    assert re.search(r'(src|href)\s*=\s*"https?://', page) is None
    assert "cdn" not in page.lower()
    assert "<script src" not in page
    assert "<link" not in page


def test_dashboard_has_working_tab_buttons():
    page = render(format="html").content

    tabs = re.findall(r'class="tab[^"]*" data-tab="([a-z]+)"', page)
    panels = re.findall(r'class="panel" id="panel-([a-z]+)"', page)
    assert len(tabs) >= 3
    assert set(tabs) == set(panels)  # every button has a panel to show
    assert page.count('aria-selected="true"') == 1
    assert "addEventListener" in page
    assert "panel.hidden" in page


def test_dashboard_chart_switching_offers_only_sensible_charts():
    trend = render(data=TREND, format="html").content
    skills = render(data=SKILLS, format="html").content
    parts = render(data=SPLIT, context={"kind": "composition"}, format="html").content

    assert set(re.findall(r'class="chart-view" data-chart="(\w+)"', trend)) == {
        "line",
        "area",
    }
    assert set(re.findall(r'class="chart-view" data-chart="(\w+)"', skills)) == {
        "bar",
        "horizontal_bar",
    }
    assert set(re.findall(r'class="chart-view" data-chart="(\w+)"', parts)) == {
        "donut",
        "pie",
    }


def test_dashboard_chart_buttons_match_the_available_views():
    page = render(data=TREND, format="html").content

    buttons = re.findall(r'class="chart-switch[^"]*" data-chart="(\w+)"', page)
    views = re.findall(r'class="chart-view" data-chart="(\w+)"', page)
    assert set(buttons) == set(views)
    assert page.count('aria-pressed="true"') == 1
    assert page.count("hidden>") >= 1  # the inactive view starts hidden


def test_dashboard_cards_adapt_to_the_data():
    skills = render(data=SKILLS, format="html").content
    trend = render(data=TREND, format="html").content
    parts = render(data=SPLIT, context={"kind": "composition"}, format="html").content
    people = render(data=CANDIDATES, format="html").content

    assert re.findall(r"<dt>([^<]+)</dt>", skills) == [
        "Average",
        "Strongest",
        "Lowest",
        "Measured",
    ]
    assert re.findall(r"<dt>([^<]+)</dt>", trend) == [
        "Latest",
        "Change",
        "Peak",
        "Periods",
    ]
    assert re.findall(r"<dt>([^<]+)</dt>", parts) == [
        "Total",
        "Largest share",
        "Parts",
    ]
    assert re.findall(r"<dt>([^<]+)</dt>", people) == [
        "Series compared",
        "Categories",
        "Highest total",
        "Top category",
    ]


def test_dashboard_tabs_adapt_to_the_data():
    assert re.findall(r'data-tab="([a-z]+)"', render(format="html").content) == [
        "overview",
        "skills",
        "breakdown",
    ]
    assert re.findall(
        r'data-tab="([a-z]+)"', render(data=TREND, format="html").content
    ) == ["overview", "trends", "breakdown"]
    assert re.findall(
        r'data-tab="([a-z]+)"', render(data=CANDIDATES, format="html").content
    ) == ["overview", "comparison", "breakdown"]


def test_dashboard_numbers_come_from_the_data_only():
    page = render(data=SKILLS, format="html").content

    assert ">Python<" in page
    assert "68.33" in page  # average of 90, 70 and 45
    assert ">90<" in page and ">45<" in page
    assert "Candidate" not in page  # nothing invented


def test_dashboard_subject_card_only_appears_when_provided():
    without = render(format="html").content
    with_subject = render(format="html", context={"subject": "Learner A4"}).content

    assert "Subject" not in without
    assert "Learner A4" in with_subject


# --- routing ------------------------------------------------------------------


@pytest.mark.parametrize("fmt", list(VisualizationFormat))
def test_explicit_format_is_always_respected(fmt):
    response = render(format=fmt, title="Interactive dashboard export image")

    assert response.format == fmt


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Interactive dashboard", VisualizationFormat.HTML),
        ("Export image for the report", VisualizationFormat.PNG),
        ("Skill scores", VisualizationFormat.SVG),
        ("Webinar attendance", VisualizationFormat.SVG),
    ],
)
def test_automatic_format_selection(title, expected):
    assert render(title=title).format == expected


# --- commentary and failures -------------------------------------------------


@pytest.mark.parametrize("fmt", list(VisualizationFormat))
def test_every_visual_has_descriptive_commentary(fmt):
    response = render(format=fmt, title="Skill scores")

    assert response.success is True
    assert fmt.value.upper() in response.commentary
    assert "Skill scores" in response.commentary
    assert "Highest is Python (90)" in response.commentary
    assert "lowest is SQL (45)" in response.commentary


def test_commentary_names_the_chart_type_that_was_drawn():
    assert "line chart" in render(data=TREND, format="svg").commentary
    assert "progress meter" in render(data={"Score": 87}, format="svg").commentary
    assert "grouped bar chart" in render(data=CANDIDATES, format="svg").commentary
    assert (
        "donut chart"
        in render(data=SPLIT, context={"kind": "composition"}, format="svg").commentary
    )


def test_trend_commentary_describes_the_movement():
    commentary = render(data=TREND, format="svg").commentary

    assert "rose from 55 (Jan) to 85 (May)" in commentary
    assert "change of 30" in commentary


def test_composition_commentary_describes_the_largest_share():
    commentary = render(
        data=SPLIT, context={"kind": "composition"}, format="svg"
    ).commentary

    assert "Technical is the largest share at 50%" in commentary


@pytest.mark.parametrize("data", [{}, 42, [{"name": "no value"}]])
def test_unchartable_data_fails_gracefully(data):
    response = render(data=data)

    assert response.success is False
    assert response.error == "No visualization data was provided."
    assert response.commentary


# --- Google image tool (network is always mocked) ---------------------------


FAKE_PNG = b"\x89PNG\r\n\x1a\nfake-image-body"


def _gemini_payload(image=FAKE_PNG, mime_type="image/png"):
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "A calm illustration."},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64.b64encode(image).decode(),
                            }
                        },
                    ]
                }
            }
        ]
    }


@pytest.fixture
def google_env(monkeypatch):
    monkeypatch.setattr(f"{GOOGLE_MODULE}.GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(f"{GOOGLE_MODULE}.GOOGLE_IMAGE_MODEL", None)


def test_google_image_success(google_env, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps(_gemini_payload()).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    response = VisualizerAgent().generate_image("Team collaboration concept")

    assert response.success is True
    assert response.format == VisualizationFormat.PNG
    assert response.asset == FAKE_PNG
    assert response.metadata["content_type"] == "image/png"
    assert response.metadata["provider"] == "google"
    assert "Team collaboration concept" in response.commentary
    request, timeout = calls[0]
    assert "gemini-3.1-flash-image:generateContent" in request.full_url
    assert "test-google-key" not in request.full_url
    assert request.get_header("X-goog-api-key") == "test-google-key"
    body = json.loads(request.data)
    assert "#004EFF" in body["contents"][0]["parts"][0]["text"]
    assert body["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
    assert timeout == 60.0


def test_google_non_png_image_is_never_reported_as_png(google_env, monkeypatch):
    jpeg = b"\xff\xd8\xff\xe0fake-jpeg-body"
    payload = _gemini_payload(image=jpeg, mime_type="image/jpeg")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: io.BytesIO(json.dumps(payload).encode()),
    )

    response = VisualizerAgent().generate_image("Concept art")

    assert response.success is False
    assert response.asset is None
    assert "image/jpeg" in response.error


def test_google_image_without_api_key_does_not_call_network(monkeypatch):
    monkeypatch.setattr(f"{GOOGLE_MODULE}.GOOGLE_API_KEY", None)

    def fail(*args, **kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr("urllib.request.urlopen", fail)

    response = VisualizerAgent().generate_image("Concept art")

    assert response.success is False
    assert "GOOGLE_API_KEY" in response.error


@pytest.mark.parametrize(
    "outcome",
    [
        TimeoutError("timed out"),
        urllib.error.URLError("connection refused"),
        urllib.error.HTTPError("https://x", 500, "Server Error", None, None),
        b"not json",
        json.dumps({"candidates": []}).encode(),
        json.dumps(
            {"candidates": [{"content": {"parts": [{"inlineData": {"data": "%%%"}}]}}]}
        ).encode(),
    ],
)
def test_google_image_failures_never_raise(google_env, monkeypatch, outcome):
    def fake_urlopen(request, timeout):
        if isinstance(outcome, Exception):
            raise outcome
        return io.BytesIO(outcome)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    response = VisualizerAgent().generate_image("Concept art")

    assert response.success is False
    assert response.error
    assert "test-google-key" not in response.error + response.commentary
