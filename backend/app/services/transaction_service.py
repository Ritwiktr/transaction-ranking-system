from datetime import UTC, datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Transaction, UserStats
from app.schemas import TransactionRequest, TransactionResponse


@dataclass
class ProcessResult:
    response: TransactionResponse
    is_duplicate: bool


def _build_response(
    transaction: Transaction, stats: UserStats, duplicate: bool
) -> TransactionResponse:
    return TransactionResponse(
        transactionId=transaction.id,
        userId=transaction.user_id,
        amount=transaction.amount,
        totalPoints=stats.total_points,
        transactionCount=stats.transaction_count,
        duplicate=duplicate,
    )


def _get_stats_for_update(db: Session, user_id: str) -> UserStats | None:
    stmt = select(UserStats).where(UserStats.user_id == user_id).with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def _increment_stats(db: Session, user_id: str, amount: int, now: datetime) -> UserStats:
    stats = _get_stats_for_update(db, user_id)
    if stats is None:
        stats = UserStats(
            user_id=user_id,
            total_points=amount,
            transaction_count=1,
            first_transaction_at=now,
            updated_at=now,
        )
        db.add(stats)
        db.flush()
        return stats

    stats.total_points += amount
    stats.transaction_count += 1
    stats.updated_at = now
    db.flush()
    return stats


def _fetch_duplicate(db: Session, idempotency_key: str) -> ProcessResult | None:
    existing = db.execute(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing is None:
        return None

    stats = db.execute(
        select(UserStats).where(UserStats.user_id == existing.user_id)
    ).scalar_one_or_none()
    if stats is None:
        raise RuntimeError("Transaction exists without user stats")

    return ProcessResult(
        response=_build_response(existing, stats, duplicate=True),
        is_duplicate=True,
    )


def process_transaction(db: Session, payload: TransactionRequest) -> ProcessResult:
    duplicate_result = _fetch_duplicate(db, payload.idempotencyKey)
    if duplicate_result is not None:
        return duplicate_result

    now = datetime.now(UTC)
    transaction = Transaction(
        user_id=payload.userId,
        amount=payload.amount,
        idempotency_key=payload.idempotencyKey,
        created_at=now,
    )
    db.add(transaction)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        duplicate_result = _fetch_duplicate(db, payload.idempotencyKey)
        if duplicate_result is not None:
            return duplicate_result
        raise

    stats = _increment_stats(db, payload.userId, payload.amount, now)
    db.commit()
    db.refresh(transaction)

    return ProcessResult(
        response=_build_response(transaction, stats, duplicate=False),
        is_duplicate=False,
    )
