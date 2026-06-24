from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserStats
from app.schemas import RankingEntry, RankingResponse, SummaryResponse


def compute_average(total_points: int, transaction_count: int) -> float:
    if transaction_count == 0:
        return 0.0
    return round(total_points / transaction_count, 2)


def compute_ranking_score(total_points: int, transaction_count: int) -> float:
    average = compute_average(total_points, transaction_count)
    return round(total_points + average * 0.1, 2)


def _sort_key(stats: UserStats) -> tuple:
    average = compute_average(stats.total_points, stats.transaction_count)
    return (
        -stats.total_points,
        -average,
        stats.first_transaction_at,
    )


def _load_all_stats(db: Session) -> list[UserStats]:
    return list(db.execute(select(UserStats)).scalars().all())


def _ordered_stats(db: Session) -> list[UserStats]:
    stats_list = _load_all_stats(db)
    return sorted(stats_list, key=_sort_key)


def get_user_rank(db: Session, user_id: str) -> int | None:
    ordered = _ordered_stats(db)
    for index, stats in enumerate(ordered, start=1):
        if stats.user_id == user_id:
            return index
    return None


def get_summary(db: Session, user_id: str) -> SummaryResponse | None:
    stats = db.execute(
        select(UserStats).where(UserStats.user_id == user_id)
    ).scalar_one_or_none()
    if stats is None:
        return None

    rank = get_user_rank(db, user_id)
    if rank is None:
        return None

    return SummaryResponse(
        userId=stats.user_id,
        totalPoints=stats.total_points,
        transactionCount=stats.transaction_count,
        averageTransactionAmount=compute_average(stats.total_points, stats.transaction_count),
        rank=rank,
        rankingScore=compute_ranking_score(stats.total_points, stats.transaction_count),
    )


def get_ranking(db: Session, limit: int = 50) -> RankingResponse:
    ordered = _ordered_stats(db)[:limit]
    rankings = [
        RankingEntry(
            rank=index,
            userId=stats.user_id,
            totalPoints=stats.total_points,
            transactionCount=stats.transaction_count,
            averageTransactionAmount=compute_average(stats.total_points, stats.transaction_count),
            rankingScore=compute_ranking_score(stats.total_points, stats.transaction_count),
        )
        for index, stats in enumerate(ordered, start=1)
    ]
    return RankingResponse(rankings=rankings)
