"""Celery tasks for the Germinal pipeline.

Each task runs in a Celery worker process.  Async helpers are bridged via
`asyncio.run()` since Celery workers are synchronous by default.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from api.celery_app import celery_app
from src.complexity import ComplexityEstimator
from src.conjecture_generator import ConjectureGenerator
from src.counterexample import search_dual
from src.failure_registry import FailureRegistry
from src.formalizer import Formalizer
from src.novelty import NoveltyChecker
from src.settings import Settings
from src.snapshot import SnapshotManager
from src.verifier import Verifier

logger = logging.getLogger(__name__)


def _update_job_status(
    job_id: str, status: str, result: Any = None, error: str | None = None
) -> None:
    """Write job status back to the DB (runs in a thread inside Celery worker)."""

    async def _write() -> None:
        from sqlalchemy import update as sa_update

        from src.db import JobRow, get_session

        async with get_session() as session:
            await session.execute(
                sa_update(JobRow)
                .where(JobRow.id == job_id)
                .values(status=status, result=result, error=error)
            )
            await session.commit()

    try:
        asyncio.run(_write())
    except Exception as exc:
        logger.warning("Could not update job %s status: %s", job_id, exc)


def _write_experiment(exp_row_kwargs: dict[str, Any]) -> None:
    async def _write() -> None:
        from src.db import ExperimentRow, get_session

        async with get_session() as session:
            session.add(ExperimentRow(**exp_row_kwargs))
            await session.commit()

    try:
        asyncio.run(_write())
    except Exception as exc:
        logger.warning("Could not persist experiment to DB: %s", exc)


@celery_app.task(bind=True, name="germinal.pipeline")
def run_pipeline_task(
    self: Any,
    job_id: str,
    domain: str,
    n: int,
) -> dict[str, Any]:
    """Full generate → formalize → verify pipeline as a Celery task."""
    settings = Settings()
    t_start = time.monotonic()

    _update_job_status(job_id, "running")

    try:
        generator = ConjectureGenerator(settings)
        formalizer = Formalizer(settings)
        verifier = Verifier(settings)
        estimator = ComplexityEstimator(settings)
        novelty_checker = NoveltyChecker(threshold=settings.novelty_threshold)
        failure_registry = FailureRegistry(settings.redis_url)
        snapshot = SnapshotManager(settings=settings)

        # Fetch arXiv context asynchronously
        arxiv_papers = asyncio.run(_fetch_arxiv(domain, settings.arxiv_max_results))

        # Generate conjectures (with arXiv context + failure feedback)
        avoidance_hint = failure_registry.build_avoidance_hint()
        conjectures = generator.generate(
            domain=domain,
            n=n,
            arxiv_context=arxiv_papers,
            avoidance_hint=avoidance_hint,
        )

        # Filter near-duplicates
        novel, dupes = novelty_checker.filter_novel(conjectures)
        if dupes:
            logger.info("Filtered %d near-duplicate conjecture(s)", len(dupes))

        results = []
        for conjecture in novel:
            exp_id = str(uuid.uuid4())
            step_start = time.monotonic()

            # Complexity estimate → route proof strategy
            complexity = estimator.estimate(conjecture["statement"])
            strategy = complexity.get("recommended_strategy", "claude_standard")

            if strategy == "human_review":
                logger.info("Conjecture flagged for human review — skipping Lean steps")
                formalize_result: dict[str, Any] = {
                    "lean_code": "",
                    "is_valid": False,
                    "error_log": "Complexity too high — flagged for human review",
                }
                verify_result: dict[str, Any] = {
                    "proved": False,
                    "attempts": [],
                    "final_proof": None,
                    "failure_reason": "Skipped — human review required",
                }
            else:
                formalize_result = formalizer.formalize(
                    conjecture=conjecture["statement"],
                    subfield=conjecture.get("subfield", ""),
                )
                if formalize_result["is_valid"]:
                    failure_registry.record_success(
                        conjecture.get("subfield", ""), "formalize"
                    )
                    verify_result = asyncio.run(
                        verifier.verify_async(
                            lean_code=formalize_result["lean_code"],
                            strategy=strategy,
                        )
                    )
                    if verify_result["proved"]:
                        failure_registry.record_success(
                            conjecture.get("subfield", ""), "verify"
                        )
                        cx_result: dict[str, Any] = {
                            "found": False,
                            "counterexample": None,
                            "reasoning": "Proof succeeded — no counterexample search needed",
                        }
                    else:
                        failure_registry.record_failure(
                            conjecture.get("subfield", ""), "verify"
                        )
                        # Run the counterexample ensemble.
                        # Multiple independent failures-to-disprove are more informative than one.
                        try:
                            cx_result = search_dual(
                                conjecture["statement"],
                                conjecture.get("subfield", ""),
                                settings,
                            )
                        except Exception as cx_exc:
                            logger.warning(
                                "Counterexample ensemble search failed: %s", cx_exc
                            )
                            cx_result = {
                                "found": False,
                                "counterexample": None,
                                "reasoning": str(cx_exc),
                                "llm_result": None,
                                "symbolic_result": None,
                                "wolfram_result": None,
                            }
                else:
                    failure_registry.record_failure(
                        conjecture.get("subfield", ""), "formalize"
                    )
                    verify_result = {
                        "proved": False,
                        "attempts": [],
                        "final_proof": None,
                        "failure_reason": "Formalization failed",
                    }
                    cx_result = {
                        "found": False,
                        "counterexample": None,
                        "reasoning": "Formalization failed — counterexample search skipped",
                    }

            duration_ms = int((time.monotonic() - step_start) * 1000)

            try:
                sha = snapshot.commit_experiment(
                    experiment_id=exp_id,
                    domain=domain,
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
                        "confidence_estimate": conjecture.get(
                            "confidence_estimate", 0.0
                        ),
                        "novelty_score": conjecture.get("novelty_score", 1.0),
                        "tags": conjecture.get("tags", []),
                        "complexity": complexity,
                        "proof_strategy": strategy,
                        "verification_attempts": len(verify_result.get("attempts", [])),
                        "counterexample_result": cx_result,
                        "git_sha": "",
                        "job_id": job_id,
                    },
                )
            except Exception as exc:
                logger.error("Snapshot failed for %s: %s", exp_id, exc)
                sha = None

            _write_experiment(
                {
                    "id": exp_id,
                    "domain": domain,
                    "subfield": conjecture.get("subfield", ""),
                    "conjecture": conjecture["statement"],
                    "lean_code": formalize_result.get("lean_code", ""),
                    "is_valid": formalize_result.get("is_valid", False),
                    "proved": verify_result.get("proved", False),
                    "final_proof": verify_result.get("final_proof"),
                    "model_used": settings.claude_model,
                    "duration_ms": duration_ms,
                    "confidence_estimate": conjecture.get("confidence_estimate", 0.5),
                    "novelty_score": conjecture.get("novelty_score", 1.0),
                    "complexity_formalizability": complexity.get("formalizability", 3),
                    "complexity_proof_difficulty": complexity.get(
                        "proof_difficulty", 3
                    ),
                    "proof_strategy": strategy,
                    "git_sha": sha,
                    "tags": conjecture.get("tags", []),
                    "job_id": job_id,
                    "counterexample_result": cx_result,
                }
            )

            cx_checked = isinstance(cx_result, dict) and (
                "llm_result" in cx_result
                or "symbolic_result" in cx_result
                or "wolfram_result" in cx_result
            )
            results.append(
                {
                    "experiment_id": exp_id,
                    "conjecture": conjecture["statement"],
                    "is_valid": formalize_result.get("is_valid", False),
                    "proved": verify_result.get("proved", False),
                    "duration_ms": duration_ms,
                    "git_sha": sha,
                    "proof_strategy": strategy,
                    "novelty_score": conjecture.get("novelty_score", 1.0),
                    "complexity": complexity,
                    "counterexample_checked": cx_checked,
                    "counterexample_found": bool(cx_result.get("found", False))
                    if cx_checked
                    else False,
                }
            )

        total_ms = int((time.monotonic() - t_start) * 1000)
        payload = {
            "domain": domain,
            "total_duration_ms": total_ms,
            "results": results,
            "filtered_duplicates": len(dupes),
        }
        _update_job_status(job_id, "done", result=payload)
        return payload

    except Exception as exc:
        logger.exception("Pipeline task %s failed", job_id)
        _update_job_status(job_id, "error", error=str(exc))
        raise


async def _fetch_arxiv(domain: str, max_results: int) -> list[dict[str, Any]]:
    from src.arxiv_client import fetch_context_papers

    return await fetch_context_papers(domain, max_results)
