import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.chatbot_service import generate_bot_response
from app.classification_service import classify_trace
from app.database import get_db

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("/", response_model=schemas.TraceResponse, status_code=status.HTTP_201_CREATED)
async def create_trace(payload: schemas.TraceCreate, db: Session = Depends(get_db)):
    """Accept a user message, call the LLM, classify the result, persist and return the trace."""

    # ── 1. Generate bot response, measuring wall-clock time ───────────────────
    t_start = time.perf_counter()
    bot_response = await generate_bot_response(payload.user_message)
    response_time_ms = int((time.perf_counter() - t_start) * 1000)

    if not bot_response:
        raise HTTPException(
            status_code=503,
            detail=(
                "The LLM returned an empty response. "
                "Make sure the llama3 model is pulled: "
                "docker exec -it supportlens_ollama ollama pull llama3"
            ),
        )

    # ── 2. Classify the conversation ──────────────────────────────────────────
    category_str = await classify_trace(payload.user_message, bot_response)

    # ── 3. Persist ────────────────────────────────────────────────────────────
    trace = models.Trace(
        id=str(uuid.uuid4()),
        user_message=payload.user_message,
        bot_response=bot_response,
        category=category_str,
        timestamp=datetime.now(timezone.utc),
        response_time_ms=response_time_ms,
    )
    db.add(trace)
    db.flush()
    db.refresh(trace)
    return trace


@router.get("/", response_model=list[schemas.TraceResponse])
def list_traces(
    category: models.Category | None = Query(
        None,
        description="Filter by category (e.g. Billing, Refund, Account Access, Cancellation, General Inquiry)",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return traces ordered most-recent first, with optional category filter and pagination."""
    q = db.query(models.Trace)
    if category:
        q = q.filter(models.Trace.category == category)
    return q.order_by(models.Trace.timestamp.desc()).offset(offset).limit(limit).all()


@router.get("/{trace_id}", response_model=schemas.TraceResponse)
def get_trace(trace_id: str, db: Session = Depends(get_db)):
    trace = db.query(models.Trace).filter(models.Trace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.delete("/{trace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trace(trace_id: str, db: Session = Depends(get_db)):
    trace = db.query(models.Trace).filter(models.Trace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    db.delete(trace)
