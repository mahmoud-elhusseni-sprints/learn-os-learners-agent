"""Task 19 transport contracts, independent of FastAPI and chat persistence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.app.schemas.models import Theme, VisualizationFormat


class VisualOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: VisualizationFormat = VisualizationFormat.SVG
    theme: Theme | None = None


class VerifiedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    date: str | None = None


class VisualArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: VisualizationFormat
    data: str
    encoding: Literal["text", "base64"]
    commentary: str
    evidence: list[VerifiedEvidence]


class VisualFallback(BaseModel):
    code: Literal["unsupported", "insufficient_evidence", "timeout", "error", "busy"]
    notice: str


class EmployerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    markdown: str
    artifacts: list[VisualArtifact] = Field(default_factory=list)
    fallback: VisualFallback | None = None