from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Category


# ── Trace ──────────────────────────────────────────────────────────────────────

class TraceCreate(BaseModel):
    """Input for POST /traces — only the raw user message is required.
    The bot response, category, and timing are all derived server-side.
    """
    user_message: str = Field(..., min_length=1, max_length=2000, description="The message sent by the user")


class TraceResponse(BaseModel):
    id: str
    user_message: str
    bot_response: str
    category: Category
    timestamp: datetime
    response_time_ms: int

    model_config = {"from_attributes": True}


# ── Analytics ─────────────────────────────────────────────────────────────────

class CategoryBreakdown(BaseModel):
    category: str
    count: int
    percentage: float


class AnalyticsResponse(BaseModel):
    total_traces: int
    average_response_time: float
    breakdown: list[CategoryBreakdown]


# ── Ticket ────────────────────────────────────────────────────────────────────

class TicketBase(BaseModel):
    title: str
    description: str
    status: str = "open"


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


class TicketRead(TicketBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Analysis ──────────────────────────────────────────────────────────────────

class AnalysisBase(BaseModel):
    summary: str | None = None
    sentiment: str | None = None
    suggested_response: str | None = None


class AnalysisRead(AnalysisBase):
    id: int
    ticket_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
