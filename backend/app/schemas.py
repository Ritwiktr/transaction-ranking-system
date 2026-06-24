import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


class TransactionRequest(BaseModel):
    userId: Annotated[str, Field(min_length=3, max_length=64)]
    amount: Annotated[int, Field(ge=1, le=10_000)]
    idempotencyKey: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("userId")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        if not USER_ID_PATTERN.match(value):
            raise ValueError(
                "userId must be 3-64 characters and contain only letters, numbers, hyphens, or underscores"
            )
        return value


class TransactionResponse(BaseModel):
    transactionId: str
    userId: str
    amount: int
    totalPoints: int
    transactionCount: int
    duplicate: bool


class SummaryResponse(BaseModel):
    userId: str
    totalPoints: int
    transactionCount: int
    averageTransactionAmount: float
    rank: int
    rankingScore: float


class RankingEntry(BaseModel):
    rank: int
    userId: str
    totalPoints: int
    transactionCount: int
    averageTransactionAmount: float
    rankingScore: float


class RankingResponse(BaseModel):
    rankings: list[RankingEntry]


class ErrorResponse(BaseModel):
    detail: str
