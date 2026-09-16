import base64
import io
import json
import struct
import urllib.error
import xml.etree.ElementTree as ET
import zlib

import pytest
from pydantic import ValidationError

from src.app.agents.visualizer import (
    SPRINTS_DEFAULT_THEME,
    VisualizationFormat,
    VisualizationRequest,
    VisualizationResponse,
    VisualizerAgent,
)

GOOGLE_MODULE = "src.app.agents.visualizer.google_image"

SKILLS = {"Python": 90, "FastAPI": 70, "SQL": 45}


def render(data=SKILLS, **kwargs):
    return VisualizerAgent().visualize(VisualizationRequest(data=data, **kwargs))


def decode_png(data):
    """Parse every chunk, check CRCs, and return (width, height, raw rows)."""
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    pos, width, height, idat = 8, 0, 0, b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])
        assert zlib.crc32(kind + body) & 0xFFFFFFFF == crc
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    assert len(raw) == height * (width * 3 + 1)
    return width, height, raw


def pixel(raw, width, x, y):
    start = y * (width * 3 + 1) + 1 + x * 3
    return raw[start : start + 3].hex().upper()


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
    png = render(theme=theme, format="png").asset

    assert 'rx="4" fill="#FF0000"' in svg and 'rx="4" fill="#004EFF"' not in svg
    assert "--primary:#FF0000" in page and "--secondary:#33D7D1" in page
    width, _, raw = decode_png(png)
    assert pixel(raw, width, 0, 0) == "000000"
    assert pixel(raw, width, 121, 90) == "FF0000"


@pytest.mark.parametrize(
    "theme",
    [{"primary": "red;}</style><script>alert(1)</script>"}, {"bogus": "#000000"}],
)
def test_invalid_theme_is_rejected_by_the_contract(theme):
    with pytest.raises(ValidationError):
        VisualizationRequest(data=SKILLS, theme=theme)


# --- rendering ----------------------------------------------------------------


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
    assert "http" not in response.content
    assert "<script" not in response.content


def test_png_renderer_returns_decodable_png_with_theme_pixels():
    response = render(data={"Python": 90}, format="png", width=400, height=300)

    assert response.success is True
    assert response.format == VisualizationFormat.PNG
    assert response.metadata["content_type"] == "image/png"
    width, height, raw = decode_png(response.asset)
    assert (width, height) == (400, 300)
    assert pixel(raw, width, 0, 0) == "FBFBFD"
    assert pixel(raw, width, 121, 90) == "004EFF"


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


@pytest.mark.parametrize("fmt", ["svg", "png"])
def test_canvas_grows_so_many_rows_are_not_cut_off(fmt):
    response = render(data={f"Skill {i}": i + 1 for i in range(15)}, format=fmt)

    height = response.metadata["height"]
    last_bar_bottom = 88 + 14 * (26 + 18) + 26
    assert height >= last_bar_bottom
    if fmt == "png":
        assert decode_png(response.asset)[1] == height
    else:
        assert f'height="{height}"' in response.content


def test_png_response_survives_json_round_trip():
    response = render(format="png")

    restored = VisualizationResponse.model_validate_json(response.model_dump_json())
    assert restored.asset == response.asset


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
