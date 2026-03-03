import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.llm_client import call_llama

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

_ANALYSIS_PROMPT = """\
Analyse this customer support ticket and reply in EXACTLY this format — no extra text:

SUMMARY: <one sentence summary of the issue>
SENTIMENT: <Positive|Neutral|Negative>
SUGGESTED_RESPONSE: <a helpful reply to send to the customer>

Ticket:
{description}"""

_VALID_SENTIMENTS = {"Positive", "Neutral", "Negative"}


def _parse_analysis(raw: str) -> dict[str, str | None]:
    result: dict[str, str | None] = {
        "summary": None,
        "sentiment": None,
        "suggested_response": None,
    }

    summary_m = re.search(r"SUMMARY:\s*(.+?)(?=\nSENTIMENT:|\Z)", raw, re.IGNORECASE | re.DOTALL)
    sentiment_m = re.search(r"SENTIMENT:\s*(\w+)", raw, re.IGNORECASE)
    response_m = re.search(
        r"SUGGESTED_RESPONSE:\s*(.+?)(?=\n[A-Z_]+:|\Z)", raw, re.IGNORECASE | re.DOTALL
    )

    if summary_m:
        result["summary"] = summary_m.group(1).strip()
    if sentiment_m:
        candidate = sentiment_m.group(1).capitalize()
        result["sentiment"] = candidate if candidate in _VALID_SENTIMENTS else "Neutral"
    if response_m:
        result["suggested_response"] = response_m.group(1).strip()

    if not any(result.values()):
        logger.warning("_parse_analysis: could not extract structured fields from LLM output")

    return result


@router.post("/{ticket_id}", response_model=schemas.AnalysisRead)
async def analyse_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    raw = await call_llama(
        messages=[
            {"role": "user", "content": _ANALYSIS_PROMPT.format(description=ticket.description)}
        ],
        temperature=0.3,
        num_predict=400,
    )

    parsed = _parse_analysis(raw)

    analysis = models.Analysis(
        ticket_id=ticket.id,
        summary=parsed["summary"],
        sentiment=parsed["sentiment"],
        suggested_response=parsed["suggested_response"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/{ticket_id}", response_model=list[schemas.AnalysisRead])
def get_analyses(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket.analyses
