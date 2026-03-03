from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import analysis, analytics, tickets, traces
from app.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    seed_database()
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-powered customer support analysis platform.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(traces.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.app_name}
