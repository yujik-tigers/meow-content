from datetime import datetime

import pytest
from sqlmodel import select

from app.repository.mysql._models import TokenUsageRecord
from app.repository.mysql.repository import MySQLTokenUsageRepository


@pytest.fixture
def usage_repository(db_session) -> MySQLTokenUsageRepository:
    return MySQLTokenUsageRepository(db_session)


async def test_record_adds_and_commits(usage_repository, db_session) -> None:
    """토큰 사용량을 기록하면 token_usage 테이블에 실제 행이 생성된다."""
    await usage_repository.record("gpt-5.2", 100, 50)

    rows = (await db_session.exec(select(TokenUsageRecord))).all()
    assert len(rows) == 1
    assert rows[0].model == "gpt-5.2"
    assert rows[0].input_tokens == 100
    assert rows[0].output_tokens == 50


async def test_aggregate_by_maps_rows_to_usage_aggregate(
    usage_repository, db_session
) -> None:
    """기간 내 토큰 사용량을 일자·모델별로 집계하여 UsageAggregate로 반환한다."""
    db_session.add_all(
        [
            TokenUsageRecord(
                model="gpt-5.2",
                input_tokens=100,
                output_tokens=50,
                created_at=datetime(2026, 6, 15, 10, 0),
            ),
            TokenUsageRecord(
                model="gpt-5.2",
                input_tokens=200,
                output_tokens=100,
                created_at=datetime(2026, 6, 15, 14, 0),
            ),
            TokenUsageRecord(
                model="nano-banana",
                input_tokens=30,
                output_tokens=10,
                created_at=datetime(2026, 6, 16, 9, 0),
            ),
        ]
    )
    await db_session.commit()

    result = await usage_repository.aggregate_by(
        datetime(2026, 6, 1), datetime(2026, 7, 1)
    )

    assert len(result) == 2
    gpt = next(r for r in result if r.model == "gpt-5.2")
    assert gpt.period == "2026-06-15"
    assert gpt.request_count == 2
    assert gpt.input_tokens_sum == 300
    assert gpt.output_tokens_sum == 150
    nano = next(r for r in result if r.model == "nano-banana")
    assert nano.period == "2026-06-16"
    assert nano.request_count == 1


async def test_aggregate_by_excludes_out_of_range_rows(
    usage_repository, db_session
) -> None:
    """조회 기간 밖의 사용량은 집계에 포함되지 않는다."""
    db_session.add(
        TokenUsageRecord(
            model="gpt-5.2",
            input_tokens=100,
            output_tokens=50,
            created_at=datetime(2026, 5, 31, 23, 0),
        )
    )
    await db_session.commit()

    result = await usage_repository.aggregate_by(
        datetime(2026, 6, 1), datetime(2026, 7, 1)
    )

    assert result == []
