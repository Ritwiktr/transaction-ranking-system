from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app.errors import not_found
from app.middleware.rate_limit import rate_limiter
from app.schemas import (
    ErrorResponse,
    RankingResponse,
    SummaryResponse,
    TransactionRequest,
    TransactionResponse,
)
from app.services.ranking_service import get_ranking, get_summary
from app.services.transaction_service import process_transaction


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Transaction Ranking System",
    description="Points ledger with idempotent transactions and fair multi-factor ranking.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        messages.append(f"{loc}: {error.get('msg')}" if loc else error.get("msg", "Invalid input"))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "; ".join(messages)},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/transaction",
    response_model=TransactionResponse,
    responses={
        200: {"model": TransactionResponse, "description": "Duplicate idempotency key"},
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def create_transaction(payload: TransactionRequest, db: Session = Depends(get_db)):
    rate_limiter.check(payload.userId)
    result = process_transaction(db, payload)
    status_code = status.HTTP_200_OK if result.is_duplicate else status.HTTP_201_CREATED
    return JSONResponse(status_code=status_code, content=result.response.model_dump())


@app.get(
    "/summary/{user_id}",
    response_model=SummaryResponse,
    responses={404: {"model": ErrorResponse}},
)
def user_summary(user_id: str, db: Session = Depends(get_db)):
    summary = get_summary(db, user_id)
    if summary is None:
        raise not_found(f"No transactions found for user '{user_id}'")
    return summary


@app.get("/ranking", response_model=RankingResponse)
def ranking(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_ranking(db, limit=limit)


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
