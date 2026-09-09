from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.api.deps import DbDep
from app.schemas.common import HealthResponse
from app.services.llm import get_llm_provider

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(db: DbDep) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:  # noqa: BLE001
        db_status = "unavailable"

    try:
        llm_status = get_llm_provider().health()
    except Exception:  # noqa: BLE001
        llm_status = "unavailable"

    overall = "healthy" if db_status == "healthy" else "degraded"
    return HealthResponse(
        status=overall, database=db_status, llm=llm_status, version=__version__
    )
