from sqlalchemy import Float, cast, func, select
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


def _average_amount_expression():
    return cast(UserStats.total_points, Float) / UserStats.transaction_count


def _ranking_order():
    return (
        UserStats.total_points.desc(),
        _average_amount_expression().desc(),
        UserStats.first_transaction_at.asc(),
    )


def _ranked_stats_statement():
    return select(
        UserStats,
        func.row_number().over(order_by=_ranking_order()).label("rank"),
    ).order_by(*_ranking_order())


def _to_entry(stats: UserStats, rank: int) -> RankingEntry:
    return RankingEntry(
        rank=rank,
        userId=stats.user_id,
        totalPoints=stats.total_points,
        transactionCount=stats.transaction_count,
        averageTransactionAmount=compute_average(stats.total_points, stats.transaction_count),
        rankingScore=compute_ranking_score(stats.total_points, stats.transaction_count),
    )


def get_summary(db: Session, user_id: str) -> SummaryResponse | None:
    ranked = _ranked_stats_statement().subquery()
    row = db.execute(select(ranked).where(ranked.c.user_id == user_id)).first()
    if row is None:
        return None

    return SummaryResponse(
        userId=row.user_id,
        totalPoints=row.total_points,
        transactionCount=row.transaction_count,
        averageTransactionAmount=compute_average(row.total_points, row.transaction_count),
        rank=row.rank,
        rankingScore=compute_ranking_score(row.total_points, row.transaction_count),
    )


def get_ranking(db: Session, limit: int = 50) -> RankingResponse:
    rows = db.execute(_ranked_stats_statement().limit(limit)).all()
    return RankingResponse(rankings=[_to_entry(stats, rank) for stats, rank in rows])
