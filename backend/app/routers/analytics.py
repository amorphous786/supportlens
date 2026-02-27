from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_model=schemas.AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    """Return aggregate stats across all stored traces.

    Calculations:
    - total_traces: COUNT(*) on the traces table
    - average_response_time: AVG(response_time_ms), rounded to 2 dp; 0.0 when no traces
    - breakdown: per-category COUNT + percentage of total, sorted by count desc
    """
    total: int = db.query(func.count(models.Trace.id)).scalar() or 0

    avg_ms: float = 0.0
    if total > 0:
        raw_avg = db.query(func.avg(models.Trace.response_time_ms)).scalar()
        avg_ms = round(float(raw_avg), 2) if raw_avg is not None else 0.0

    # One DB round-trip for the per-category counts
    rows = (
        db.query(models.Trace.category, func.count(models.Trace.id).label("cnt"))
        .group_by(models.Trace.category)
        .order_by(func.count(models.Trace.id).desc())
        .all()
    )

    breakdown: list[schemas.CategoryBreakdown] = [
        schemas.CategoryBreakdown(
            category=row.category.value if hasattr(row.category, "value") else str(row.category),
            count=row.cnt,
            percentage=round((row.cnt / total) * 100, 2) if total > 0 else 0.0,
        )
        for row in rows
    ]

    return schemas.AnalyticsResponse(
        total_traces=total,
        average_response_time=avg_ms,
        breakdown=breakdown,
    )
