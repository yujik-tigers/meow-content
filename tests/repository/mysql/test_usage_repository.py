from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.repository.mysql.repository import MySQLTokenUsageRepository


async def test_record_adds_and_commits() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    repository = MySQLTokenUsageRepository(session)

    await repository.record("gpt-5.2", 100, 50)

    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.model == "gpt-5.2"
    assert added.input_tokens == 100
    assert added.output_tokens == 50
    session.commit.assert_awaited_once()


async def test_record_rolls_back_on_error() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit.side_effect = RuntimeError("boom")
    repository = MySQLTokenUsageRepository(session)

    try:
        await repository.record("gpt-5.2", 100, 50)
    except RuntimeError:
        pass

    session.rollback.assert_awaited_once()


async def test_aggregate_by_maps_rows_to_usage_aggregate() -> None:
    session = AsyncMock()
    rows = [
        SimpleNamespace(
            period="2026-06-15",
            model="gpt-5.2",
            request_count=3,
            input_tokens_sum=1000,
            output_tokens_sum=500,
        ),
    ]
    exec_result = SimpleNamespace(all=lambda: rows)
    session.exec.return_value = exec_result
    repository = MySQLTokenUsageRepository(session)

    result = await repository.aggregate_by(datetime(2026, 6, 1), datetime(2026, 7, 1))

    assert len(result) == 1
    assert result[0].period == "2026-06-15"
    assert result[0].model == "gpt-5.2"
    assert result[0].request_count == 3
    assert result[0].input_tokens_sum == 1000
    assert result[0].output_tokens_sum == 500
