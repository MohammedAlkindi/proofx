"""FastAPI application entry point for Germinal."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from src.settings import Settings

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenTelemetry setup (no-op when otel_endpoint is empty)
# ---------------------------------------------------------------------------


def _setup_otel() -> None:
    if not settings.otel_endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        HTTPXClientInstrumentor().instrument()
        logger.info(
            "OpenTelemetry configured — exporting to %s", settings.otel_endpoint
        )
    except ImportError as exc:
        logger.warning("OpenTelemetry packages not available: %s", exc)
    except Exception as exc:
        logger.warning("OpenTelemetry setup failed: %s", exc)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    logger.info("Germinal API starting up")

    # Initialise database
    try:
        from src.db import init_db

        await init_db(settings.database_url)
        logger.info("Database initialised: %s", settings.database_url)
    except Exception as exc:
        logger.error("Database init failed: %s", exc)

    # Warm up the Lean sandbox in the background so the first request isn't slow
    try:
        from src.lean_sandbox import get_sandbox

        sandbox = get_sandbox(settings.lean_sandbox_dir, settings.lean_timeout)
        import asyncio

        asyncio.create_task(_warm_sandbox(sandbox))
    except Exception as exc:
        logger.warning("Could not schedule Lean sandbox warmup: %s", exc)

    yield

    logger.info("Germinal API shutting down")


async def _warm_sandbox(sandbox: object) -> None:
    try:
        await sandbox.ensure_ready()  # type: ignore[attr-defined]
        logger.info("Lean sandbox warmed up successfully")
    except Exception as exc:
        logger.warning("Lean sandbox warmup failed: %s", exc)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

_setup_otel()

app = FastAPI(
    title="Germinal API",
    description=(
        "AI-powered mathematical conjecture explorer. "
        "Generate conjectures, formalize them in Lean 4, and attempt automated proofs."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "version": "0.2.0"}
