"""Typed contracts for the Visualizer Agent."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class VisualizationFormat(StrEnum):
    """Supported visual output formats."""

    SVG = "svg"
    HTML = "html"
    PNG = "png"


# Only #RRGGBB is accepted, so a color can never inject markup into SVG/HTML
# and always converts to PNG pixels.
HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class Theme(BaseModel):
    """Small color palette used by every renderer."""

    model_config = ConfigDict(extra="forbid")

    primary: HexColor = "#004EFF"
    secondary: HexColor = "#33D7D1"
    accent: HexColor = "#33D7D1"
    background: HexColor = "#FBFBFD"
    text: HexColor = "#004EFF"


# The repository documents exactly three official Sprints colors
# (docs/data/interaction_logs.jsonl): #004EFF primary, #33D7D1 accent and
# #FBFBFD background. No official text color exists, so the fallback uses only
# those three: `secondary` and `accent` reuse #33D7D1, and `text` reuses
# #004EFF (about 5.7:1 contrast on #FBFBFD).
SPRINTS_DEFAULT_THEME = Theme()


class VisualizationRequest(BaseModel):
    """Input from the Employer Talent Intelligence Agent."""

    model_config = ConfigDict(extra="forbid")

    data: Any
    title: str | None = None
    description: str | None = None
    visualization_type: str = "bar"
    format: VisualizationFormat | None = None
    theme: Theme | None = None
    width: int = Field(800, ge=320, le=2400)
    height: int = Field(480, ge=240, le=1600)


class VisualizationResponse(BaseModel):
    """Output from a visualization render attempt."""

    model_config = ConfigDict(
        extra="forbid", ser_json_bytes="base64", val_json_bytes="base64"
    )

    success: bool
    format: VisualizationFormat
    content: str | None = None
    asset: bytes | None = None
    commentary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


def get_theme(theme: Theme | None) -> Theme:
    """Return a custom theme or the centralized Sprints fallback."""
    return theme if theme is not None else SPRINTS_DEFAULT_THEME
