"""Pydantic request/response models for the Germinal API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    """Request body for POST /generate."""

    domain: str = Field(..., min_length=1, max_length=200, description="Mathematical domain to explore")
    n: int = Field(5, ge=1, le=20, description="Number of conjectures to generate")

    @field_validator("domain")
    @classmethod
    def strip_domain(cls, v: str) -> str:
        return v.strip()


class ConjectureItem(BaseModel):
    """A single generated conjecture."""

    id: str
    domain: str
    statement: str
    subfield: str
    motivation: str
    confidence_estimate: float = Field(ge=0.0, le=1.0)
    tags: list[str]


class GenerateResponse(BaseModel):
    """Response body for POST /generate."""

    conjectures: list[ConjectureItem]


class FormalizeRequest(BaseModel):
    """Request body for POST /formalize."""

    conjecture: str = Field(..., min_length=1, max_length=5000, description="Natural-language conjecture")

    @field_validator("conjecture")
    @classmethod
    def strip_conjecture(cls, v: str) -> str:
        return v.strip()


class FormalizeResponse(BaseModel):
    """Response body for POST /formalize."""

    lean_code: str
    is_valid: bool
    error_log: str


class VerifyRequest(BaseModel):
    """Request body for POST /verify."""

    lean_code: str = Field(..., min_length=1, max_length=20000, description="Lean 4 source code to prove")

    @field_validator("lean_code")
    @classmethod
    def strip_lean_code(cls, v: str) -> str:
        return v.strip()


class ProofAttempt(BaseModel):
    """A single proof attempt record."""

    attempt: int
    lean_code: str
    error: str
    success: bool


class VerifyResponse(BaseModel):
    """Response body for POST /verify."""

    proved: bool
    attempts: list[ProofAttempt]
    final_proof: str | None
    failure_reason: str | None


class PipelineRequest(BaseModel):
    """Request body for POST /pipeline — runs the full generate→formalize→verify flow."""

    domain: str = Field(..., min_length=1, max_length=200)
    n: int = Field(1, ge=1, le=5, description="Number of conjectures to run through full pipeline")

    @field_validator("domain")
    @classmethod
    def strip_domain(cls, v: str) -> str:
        return v.strip()


class ExperimentSummary(BaseModel):
    """Summary row returned by GET /experiments."""

    id: str
    timestamp: str
    domain: str
    conjecture: str
    is_valid: bool
    proved: bool
    model_used: str
    duration_ms: int


class ExperimentDetail(BaseModel):
    """Full experiment record returned by GET /experiments/{id}."""

    id: str
    timestamp: str
    domain: str
    conjecture: str
    lean_code: str
    is_valid: bool
    proved: bool
    final_proof: str | None
    model_used: str
    duration_ms: int
    extra: dict[str, Any] = Field(default_factory=dict)
