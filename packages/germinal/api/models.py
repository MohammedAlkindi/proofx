"""Pydantic request/response models for the Germinal API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=200)
    n: int = Field(5, ge=1, le=20)

    @field_validator("domain")
    @classmethod
    def strip_domain(cls, v: str) -> str:
        return v.strip()


class ConjectureItem(BaseModel):
    id: str
    domain: str
    statement: str
    subfield: str
    motivation: str
    confidence_estimate: float = Field(ge=0.0, le=1.0)
    tags: list[str]


class GenerateResponse(BaseModel):
    conjectures: list[ConjectureItem]


# ---------------------------------------------------------------------------
# Formalize
# ---------------------------------------------------------------------------


class FormalizeRequest(BaseModel):
    conjecture: str = Field(..., min_length=1, max_length=5000)
    subfield: str = Field("", max_length=200)

    @field_validator("conjecture")
    @classmethod
    def strip_conjecture(cls, v: str) -> str:
        return v.strip()


class FormalizeResponse(BaseModel):
    lean_code: str
    is_valid: bool
    error_log: str


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    lean_code: str = Field(..., min_length=1, max_length=20000)
    strategy: str = Field("claude_standard")

    @field_validator("lean_code")
    @classmethod
    def strip_lean_code(cls, v: str) -> str:
        return v.strip()


class ProofAttempt(BaseModel):
    attempt: Any  # int or str (e.g. "auto:decide")
    lean_code: str
    error: str
    success: bool


class VerifyResponse(BaseModel):
    proved: bool
    attempts: list[ProofAttempt]
    final_proof: str | None
    failure_reason: str | None


# ---------------------------------------------------------------------------
# Pipeline (async job)
# ---------------------------------------------------------------------------


class PipelineRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=200)
    n: int = Field(1, ge=1, le=5)

    @field_validator("domain")
    @classmethod
    def strip_domain(cls, v: str) -> str:
        return v.strip()


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    total_duration_ms: int | None = None


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


class ExperimentSummary(BaseModel):
    id: str
    timestamp: str
    domain: str
    conjecture: str
    is_valid: bool
    proved: bool
    model_used: str
    duration_ms: int
    novelty_score: float = 1.0
    proof_strategy: str = "claude_standard"
    # Populated when ensemble counterexample search has been run for this experiment.
    # None means the search has never been run (e.g. proved conjectures, or old records).
    counterexample_checked: bool | None = None
    counterexample_found: bool | None = None


class ExperimentDetail(BaseModel):
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


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------


class AnnotateRequest(BaseModel):
    interesting: bool = False
    notes: str = Field("", max_length=5000)
    correct_proof: str | None = None
    annotator: str = Field("human", max_length=100)


class AnnotateResponse(BaseModel):
    annotation_id: str
    experiment_id: str
    message: str


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):
    total_experiments: int
    proved_count: int
    valid_count: int
    failure_registry: dict[str, Any]


# ---------------------------------------------------------------------------
# Counterexample
# ---------------------------------------------------------------------------


class MethodResult(BaseModel):
    """Result from a single counterexample-search method."""

    method: str  # "llm", "symbolic", or "wolfram"
    source: str | None = None  # "claude", "sympy", or "wolfram_alpha"
    applicable: bool = True  # False when a method is out-of-scope or unavailable
    found: bool
    counterexample: str | None = None
    reasoning: str
    verified_locally: bool | None = None


class CounterexampleResponse(BaseModel):
    # Top-level fields preserved for backward compatibility
    experiment_id: str
    found: bool
    counterexample: str | None
    reasoning: str
    # Per-method detail (absent for old records that pre-date dual search)
    llm_result: MethodResult | None = None
    symbolic_result: MethodResult | None = None
    wolfram_result: MethodResult | None = None
    methods_attempted: int | None = None
    methods_applicable: int | None = None
    methods_found_counterexample: int | None = None
    consensus: str | None = None
    method_disagreement: dict[str, bool] | None = None


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------


class LineageNode(BaseModel):
    id: str
    conjecture: str
    domain: str
    proved: bool
    is_valid: bool


class LineageResponse(BaseModel):
    experiment_id: str
    parent: LineageNode | None
    children: list[LineageNode]


# ---------------------------------------------------------------------------
# Derive (generate conjectures derived from an existing one)
# ---------------------------------------------------------------------------


class DeriveRequest(BaseModel):
    n: int = Field(3, ge=1, le=10)
    relation: str = Field(
        "generalization",
        description="Relationship to explore: 'generalization', 'special_case', or 'analogue'",
    )

    @field_validator("relation")
    @classmethod
    def validate_relation(cls, v: str) -> str:
        allowed = {"generalization", "special_case", "analogue"}
        if v not in allowed:
            raise ValueError(f"relation must be one of {allowed}")
        return v


class DeriveResponse(BaseModel):
    parent_experiment_id: str
    job_id: str
    status: str
    message: str
