"""FastAPI route definitions for the Germinal API."""

from __future__ import annotations

import asyncio
import logging
import textwrap
import time
import uuid
from typing import Annotated, Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from api.models import (
    AnnotateRequest,
    AnnotateResponse,
    ExperimentDetail,
    ExperimentSummary,
    FormalizeRequest,
    FormalizeResponse,
    GenerateRequest,
    GenerateResponse,
    JobResponse,
    JobStatusResponse,
    PipelineRequest,
    StatsResponse,
    VerifyRequest,
    VerifyResponse,
)
from src.conjecture_generator import ConjectureGenerator
from src.failure_registry import FailureRegistry
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


def get_failure_registry(settings: Annotated[Settings, Depends(get_settings)]) -> FailureRegistry:
    return FailureRegistry(settings.redis_url)


# ---------------------------------------------------------------------------
# Generate  (with SSE streaming option)
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_conjectures(
    body: GenerateRequest,
    generator: Annotated[ConjectureGenerator, Depends(get_generator)],
    settings: Annotated[Settings, Depends(get_settings)],
    stream: bool = Query(False, description="Stream tokens via SSE"),
) -> Any:
    """Generate N candidate mathematical conjectures.

    Pass `?stream=true` to receive a Server-Sent Events stream of conjecture
    objects as they are parsed from the Claude response.
    """
    logger.info("POST /generate domain=%r n=%d stream=%s", body.domain, body.n, stream)

    if stream:
        from src.arxiv_client import fetch_context_papers, format_papers_for_prompt

        async def sse_generator() -> AsyncGenerator[dict[str, Any], None]:
            try:
                papers = await fetch_context_papers(body.domain, settings.arxiv_max_results)
                arxiv_str = format_papers_for_prompt(papers)
                conjectures = await asyncio.to_thread(
                    generator.generate,
                    body.domain,
                    body.n,
                    papers,
                )
                for c in conjectures:
                    yield {"event": "conjecture", "data": __import__("json").dumps(c)}
                yield {"event": "done", "data": "{}"}
            except Exception as exc:
                yield {"event": "error", "data": str(exc)}

        return EventSourceResponse(sse_generator())

    try:
        conjectures = await asyncio.to_thread(generator.generate, domain=body.domain, n=body.n)
    except Exception as exc:
        logger.exception("Generation failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return GenerateResponse(conjectures=conjectures)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Formalize
# ---------------------------------------------------------------------------


@router.post("/formalize", response_model=FormalizeResponse, status_code=status.HTTP_200_OK)
async def formalize_conjecture(
    body: FormalizeRequest,
    formalizer: Annotated[Formalizer, Depends(get_formalizer)],
) -> FormalizeResponse:
    """Translate a natural-language conjecture into Lean 4 and validate it."""
    logger.info("POST /formalize len=%d", len(body.conjecture))
    try:
        result = await asyncio.to_thread(
            formalizer.formalize, conjecture=body.conjecture, subfield=body.subfield
        )
    except Exception as exc:
        logger.exception("Formalization failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return FormalizeResponse(**result)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


@router.post("/verify", response_model=VerifyResponse, status_code=status.HTTP_200_OK)
async def verify_lean(
    body: VerifyRequest,
    verifier: Annotated[Verifier, Depends(get_verifier)],
) -> VerifyResponse:
    """Attempt automated proof of Lean 4 code with multi-strategy search."""
    logger.info("POST /verify len=%d strategy=%s", len(body.lean_code), body.strategy)
    try:
        result = await verifier.verify_async(lean_code=body.lean_code, strategy=body.strategy)
    except Exception as exc:
        logger.exception("Verification failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VerifyResponse(**result)


# ---------------------------------------------------------------------------
# Pipeline — async via Celery
# ---------------------------------------------------------------------------


@router.post("/pipeline", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(
    body: PipelineRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JobResponse:
    """Submit a pipeline job (generate → formalize → verify) and return a job_id.

    Poll `GET /jobs/{job_id}` for status, or stream `GET /jobs/{job_id}/stream`.
    """
    logger.info("POST /pipeline domain=%r n=%d", body.domain, body.n)
    job_id = str(uuid.uuid4())

    # Persist the job row
    try:
        from src.db import JobRow, get_session

        async with get_session() as session:
            session.add(JobRow(id=job_id, domain=body.domain, n=body.n, status="pending"))
            await session.commit()
    except Exception as exc:
        logger.warning("Could not persist job row: %s", exc)

    # Submit to Celery
    try:
        from api.tasks import run_pipeline_task

        task = run_pipeline_task.apply_async(
            args=[job_id, body.domain, body.n],
            task_id=job_id,
        )
        logger.info("Celery task submitted: %s", task.id)
    except Exception as exc:
        logger.warning("Celery unavailable (%s) — running pipeline synchronously", exc)
        # Fallback: run in background thread so we don't block the HTTP response
        asyncio.create_task(_run_pipeline_sync(job_id, body.domain, body.n, settings))

    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Pipeline job submitted. Poll /api/v1/jobs/{job_id} for status.",
    )


async def _run_pipeline_sync(job_id: str, domain: str, n: int, settings: Settings) -> None:
    """Fallback: run the pipeline in the same process when Celery is unavailable."""
    try:
        from api.tasks import run_pipeline_task

        await asyncio.to_thread(run_pipeline_task, job_id, domain, n)
    except Exception as exc:
        logger.error("Sync pipeline fallback failed: %s", exc)


# ---------------------------------------------------------------------------
# Job status + SSE stream
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Poll job status and result."""
    try:
        from src.db import JobRow, get_session

        async with get_session() as session:
            from sqlalchemy import select

            row = (await session.execute(select(JobRow).where(JobRow.id == job_id))).scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobStatusResponse(
                job_id=row.id,
                status=row.status,
                result=row.result,
                error=row.error,
                total_duration_ms=row.total_duration_ms,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> EventSourceResponse:
    """Stream job status updates via Server-Sent Events until completion."""

    async def _events() -> AsyncGenerator[dict[str, Any], None]:
        import json

        for _ in range(300):  # max 5 minutes at 1s intervals
            try:
                from sqlalchemy import select

                from src.db import JobRow, get_session

                async with get_session() as session:
                    row = (
                        await session.execute(select(JobRow).where(JobRow.id == job_id))
                    ).scalar_one_or_none()

                if row is None:
                    yield {"event": "error", "data": json.dumps({"detail": "Job not found"})}
                    return

                yield {
                    "event": "status",
                    "data": json.dumps({"status": row.status, "job_id": job_id}),
                }

                if row.status in ("done", "error"):
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "status": row.status,
                            "result": row.result,
                            "error": row.error,
                        }),
                    }
                    return

            except Exception as exc:
                yield {"event": "error", "data": str(exc)}
                return

            await asyncio.sleep(1)

        yield {"event": "timeout", "data": "{}"}

    return EventSourceResponse(_events())


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


@router.get("/experiments", response_model=list[ExperimentSummary], status_code=status.HTTP_200_OK)
async def list_experiments(
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
    domain: str | None = Query(None),
    proved: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> list[ExperimentSummary]:
    """List experiments with optional domain / proved filters."""
    experiments = snapshot.list_experiments()

    if domain:
        experiments = [e for e in experiments if e.get("domain", "").lower() == domain.lower()]
    if proved is not None:
        experiments = [e for e in experiments if e.get("proved", False) == proved]

    experiments = experiments[:limit]

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
                novelty_score=float(exp.get("novelty_score", 1.0)),
                proof_strategy=str(exp.get("proof_strategy", "claude_standard")),
            )
        )
    return summaries


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    experiment_id: str,
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
) -> ExperimentDetail:
    exp = snapshot.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

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


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.get("/experiments/{experiment_id}/export")
async def export_experiment(
    experiment_id: str,
    fmt: str = Query("lean", description="Export format: lean or latex"),
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)] = ...,
) -> PlainTextResponse:
    """Export a single experiment as a standalone Lean 4 file or LaTeX document."""
    exp = snapshot.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if fmt == "lean":
        return PlainTextResponse(
            content=_render_lean_export(exp),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="experiment_{experiment_id[:8]}.lean"'
            },
        )
    elif fmt == "latex":
        return PlainTextResponse(
            content=_render_latex_export(exp),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="experiment_{experiment_id[:8]}.tex"'
            },
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'lean' or 'latex'.")


def _render_lean_export(exp: dict[str, Any]) -> str:
    lines = [
        "-- Generated by Germinal — AI Mathematical Conjecture Explorer",
        f"-- Domain: {exp.get('domain', '')}",
        f"-- Conjecture: {exp.get('conjecture', '')}",
        f"-- Proved: {exp.get('proved', False)}",
        f"-- Model: {exp.get('model_used', '')}",
        "",
        "import Mathlib",
        "",
    ]
    if exp.get("lean_code"):
        lines.append(exp["lean_code"])
    if exp.get("proved") and exp.get("final_proof"):
        lines += ["", "-- Automated proof:", exp["final_proof"]]
    return "\n".join(lines)


def _render_latex_export(exp: dict[str, Any]) -> str:
    def escape(s: str) -> str:
        return (
            s.replace("\\", "\\textbackslash{}")
             .replace("_", "\\_")
             .replace("{", "\\{")
             .replace("}", "\\}")
             .replace("$", "\\$")
             .replace("%", "\\%")
             .replace("&", "\\&")
             .replace("#", "\\#")
             .replace("^", "\\textasciicircum{}")
             .replace("~", "\\textasciitilde{}")
        )

    domain = escape(exp.get("domain", ""))
    conjecture = escape(exp.get("conjecture", ""))
    proved = exp.get("proved", False)
    lean_code = exp.get("lean_code", "")
    proof = exp.get("final_proof", "")

    return textwrap.dedent(f"""\
        \\documentclass{{amsart}}
        \\usepackage{{listings,hyperref}}
        \\lstdefinelanguage{{Lean4}}{{morekeywords={{theorem,lemma,def,import,by,sorry,
          simp,ring,decide,norm_num,aesop,tauto,omega}},sensitive=true,
          morecomment=[l]{{--}},morestring=[b]"}}
        \\begin{{document}}

        \\title{{Germinal Conjecture: {domain}}}
        \\maketitle

        \\begin{{conjecture}}
        {conjecture}
        \\end{{conjecture}}

        \\textbf{{Status:}} {'\\textcolor{{green}}{{Proved automatically}}' if proved else 'Open'}

        \\section*{{Lean 4 Formalization}}
        \\begin{{lstlisting}}[language=Lean4]
        {lean_code}
        \\end{{lstlisting}}
        {(chr(10) + "\\section*{Automated Proof}" + chr(10) + "\\begin{lstlisting}[language=Lean4]" + chr(10) + proof + chr(10) + "\\end{lstlisting}") if proved and proof else ""}

        \\end{{document}}
    """)


# ---------------------------------------------------------------------------
# Annotation (human-in-the-loop)
# ---------------------------------------------------------------------------


@router.post("/experiments/{experiment_id}/annotate", response_model=AnnotateResponse)
async def annotate_experiment(
    experiment_id: str,
    body: AnnotateRequest,
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
) -> AnnotateResponse:
    """Submit a human annotation for an experiment."""
    exp = snapshot.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    annotation_id = str(uuid.uuid4())

    try:
        from src.db import AnnotationRow, get_session

        async with get_session() as session:
            session.add(
                AnnotationRow(
                    id=annotation_id,
                    experiment_id=experiment_id,
                    interesting=body.interesting,
                    notes=body.notes,
                    correct_proof=body.correct_proof,
                    annotator=body.annotator,
                )
            )
            await session.commit()
    except Exception as exc:
        logger.warning("Could not persist annotation: %s", exc)

    return AnnotateResponse(
        annotation_id=annotation_id,
        experiment_id=experiment_id,
        message="Annotation saved.",
    )


@router.get("/experiments/{experiment_id}/annotations")
async def get_annotations(experiment_id: str) -> list[dict[str, Any]]:
    """Return all human annotations for an experiment."""
    try:
        from sqlalchemy import select

        from src.db import AnnotationRow, get_session

        async with get_session() as session:
            rows = (
                await session.execute(
                    select(AnnotationRow).where(AnnotationRow.experiment_id == experiment_id)
                )
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "experiment_id": r.experiment_id,
                    "created_at": r.created_at.isoformat(),
                    "interesting": r.interesting,
                    "notes": r.notes,
                    "correct_proof": r.correct_proof,
                    "annotator": r.annotator,
                }
                for r in rows
            ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    snapshot: Annotated[SnapshotManager, Depends(get_snapshot)],
    failure_registry: Annotated[FailureRegistry, Depends(get_failure_registry)],
) -> StatsResponse:
    """Return aggregate system statistics."""
    experiments = snapshot.list_experiments()
    proved = sum(1 for e in experiments if e.get("proved", False))
    valid = sum(1 for e in experiments if e.get("is_valid", False))
    return StatsResponse(
        total_experiments=len(experiments),
        proved_count=proved,
        valid_count=valid,
        failure_registry=failure_registry.all_stats(),
    )
