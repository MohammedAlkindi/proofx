"""FastAPI route definitions for the Germinal API."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.models import (
    ExperimentDetail,
    ExperimentSummary,
    FormalizeRequest,
    FormalizeResponse,
    GenerateRequest,
    GenerateResponse,
    PipelineRequest,
    VerifyRequest,
    VerifyResponse,
)
from src.conjecture_generator import ConjectureGenerator
from src.formalizer import Formalizer
from src.settings import Settings
from src.snapshot import SnapshotManager
from src.verifier import Verifier

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


def get_settings() -> Settings:
    return Settings()


def get_generator(settings: Annotated[Settings, Depends(get_settings)]) -> ConjectureGenerator:
    return ConjectureGenerator(settings)


def get_formalizer(settings: Annotated[Settings, Depends(get_settings)]) -> Formalizer:
    return Formalizer(settings)


def get_verifier(settings: Annotated[Settings, Depends(get_settings)]) -> Verifier:
    return Verifier(settings)


def get_snapshot(settings: Annotated[Settings, Depends(get_settings)]) -> SnapshotManager:
    return SnapshotManager(settings=settings)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate mathematical conjectures",
    status_code=status.HTTP_200_OK,
)
async def generate_conjectures(
    body: GenerateRequest,
    generator: Annotated[ConjectureGenerator, Depends(get_generator)],
) -> GenerateResponse:
    """Generate N candidate mathematical conjectures for the given domain."""
    logger.info("POST /generate domain=%r n=%d", body.domain, body.n)
    try:
        conjectures = generator.generate(domain=body.domain, n=body.n)
    except Exception as exc:
        logger.exception("Generation failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return GenerateResponse(conjectures=conjectures)  # type: ignore[arg-type]


@router.post(
    "/formalize",
    response_model=FormalizeResponse,
    summary="Formalize a conjecture in Lean 4",
    status_code=status.HTTP_200_OK,
)
async def formalize_conjecture(
    body: FormalizeRequest,
    formalizer: Annotated[Formalizer, Depends(get_formalizer)],
) -> FormalizeResponse:
    """Translate a natural-language conjecture into Lean 4 and validate it."""
    logger.info("POST /formalize conjecture_len=%d", len(body.conjecture))
    try:
        result = formalizer.formalize(conjecture=body.conjecture)
    except Exception as exc:
        logger.exception("Formalization failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return FormalizeResponse(**result)


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Attempt automated proof of Lean 4 code",
    status_code=status.HTTP_200_OK,
)
async def verify_lean(
    body: VerifyRequest,
    verifier: Annotated[Verifier, Depends(get_verifier)],
) -> VerifyResponse:
    """Attempt up to 3 automated proof attempts for the given Lean 4 statement."""
    logger.info("POST /verify lean_len=%d", len(body.lean_code))
    try:
        result = verifier.verify(lean_code=body.lean_code)
    except Exception as exc:
        logger.exception("Verification failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VerifyResponse(**result)


@router.post(
    "/pipeline",
    summary="Run the full generate→formalize→verify pipeline",
    status_code=status.HTTP_200_OK,
)
async def run_pipeline(
    body: PipelineRequest,
    generator: Annotated[ConjectureGenerator, Depends(get_generator)],
    formalizer: Annotated[Formalizer, Depends(get_formalizer)],
    verifier: Annotated[Verifier, Depends(get_verifier)],
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Run the full pipeline for N conjectures and save each as a snapshot."""
    logger.info("POST /pipeline domain=%r n=%d", body.domain, body.n)
    t_start = time.monotonic()

    try:
        conjectures = generator.generate(domain=body.domain, n=body.n)
    except Exception as exc:
        logger.exception("Pipeline generation step failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    results = []
    for conjecture in conjectures:
        exp_id = str(uuid.uuid4())
        step_start = time.monotonic()

        formalize_result = formalizer.formalize(conjecture["statement"])
        verify_result: dict = {"proved": False, "attempts": [], "final_proof": None, "failure_reason": None}

        if formalize_result["is_valid"] and formalize_result["lean_code"]:
            verify_result = verifier.verify(formalize_result["lean_code"])

        duration_ms = int((time.monotonic() - step_start) * 1000)

        try:
            sha = snapshot.commit_experiment(
                experiment_id=exp_id,
                domain=body.domain,
                conjecture=conjecture["statement"],
                lean_code=formalize_result.get("lean_code", ""),
                is_valid=formalize_result.get("is_valid", False),
                proved=verify_result.get("proved", False),
                final_proof=verify_result.get("final_proof"),
                model_used=settings.claude_model,
                duration_ms=duration_ms,
                extra={
                    "subfield": conjecture.get("subfield", ""),
                    "motivation": conjecture.get("motivation", ""),
                    "confidence_estimate": conjecture.get("confidence_estimate", 0.0),
                    "tags": conjecture.get("tags", []),
                    "verification_attempts": len(verify_result.get("attempts", [])),
                    "git_sha": "",
                },
            )
            results.append(
                {
                    "experiment_id": exp_id,
                    "conjecture": conjecture["statement"],
                    "is_valid": formalize_result["is_valid"],
                    "proved": verify_result["proved"],
                    "duration_ms": duration_ms,
                    "git_sha": sha,
                }
            )
        except Exception as exc:
            logger.error("Snapshot commit failed for %s: %s", exp_id, exc)
            results.append(
                {
                    "experiment_id": exp_id,
                    "conjecture": conjecture["statement"],
                    "is_valid": formalize_result["is_valid"],
                    "proved": verify_result["proved"],
                    "duration_ms": duration_ms,
                    "git_sha": None,
                    "snapshot_error": str(exc),
                }
            )

    total_ms = int((time.monotonic() - t_start) * 1000)
    return {"domain": body.domain, "total_duration_ms": total_ms, "results": results}


@router.get(
    "/experiments",
    response_model=list[ExperimentSummary],
    summary="List all experiments",
    status_code=status.HTTP_200_OK,
)
async def list_experiments(
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
) -> list[ExperimentSummary]:
    """Return a list of all committed experiments, newest first."""
    experiments = snapshot.list_experiments()
    summaries = []
    for exp in experiments:
        summaries.append(
            ExperimentSummary(
                id=exp.get("id", ""),
                timestamp=exp.get("timestamp", ""),
                domain=exp.get("domain", ""),
                conjecture=exp.get("conjecture", ""),
                is_valid=exp.get("is_valid", False),
                proved=exp.get("proved", False),
                model_used=exp.get("model_used", ""),
                duration_ms=exp.get("duration_ms", 0),
            )
        )
    return summaries


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentDetail,
    summary="Get full experiment details",
    status_code=status.HTTP_200_OK,
)
async def get_experiment(
    experiment_id: str,
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
) -> ExperimentDetail:
    """Return the full metadata and code for a single experiment."""
    exp = snapshot.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    known_keys = {
        "id", "timestamp", "domain", "conjecture", "lean_code",
        "is_valid", "proved", "final_proof", "model_used", "duration_ms",
    }
    extra = {k: v for k, v in exp.items() if k not in known_keys}

    return ExperimentDetail(
        id=exp.get("id", ""),
        timestamp=exp.get("timestamp", ""),
        domain=exp.get("domain", ""),
        conjecture=exp.get("conjecture", ""),
        lean_code=exp.get("lean_code", ""),
        is_valid=exp.get("is_valid", False),
        proved=exp.get("proved", False),
        final_proof=exp.get("final_proof"),
        model_used=exp.get("model_used", ""),
        duration_ms=exp.get("duration_ms", 0),
        extra=extra,
    )
