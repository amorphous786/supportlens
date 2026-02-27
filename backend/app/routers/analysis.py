from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ollama_client import ollama_client

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/{ticket_id}", response_model=schemas.AnalysisRead)
async def analyse_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Trigger an LLM analysis for a ticket (logic to be implemented)."""
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Placeholder — real prompt engineering goes here
    _ = await ollama_client.generate(f"Analyse this support ticket:\n{ticket.description}")

    analysis = models.Analysis(ticket_id=ticket.id)
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
