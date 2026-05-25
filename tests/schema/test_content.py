import pytest

from app.enums import ContentStatus
from app.schema.content import UpdateContentStatusRequest


def make_req(
    from_status: ContentStatus, to_status: ContentStatus
) -> UpdateContentStatusRequest:
    return UpdateContentStatusRequest(from_status=from_status, to_status=to_status)


@pytest.mark.parametrize(
    "from_status, to_status",
    [
        (ContentStatus.PENDING, ContentStatus.APPROVED),
        (ContentStatus.PENDING, ContentStatus.REJECTED),
        (ContentStatus.RAW, ContentStatus.PENDING),
        (ContentStatus.ANALYZED, ContentStatus.PENDING),
        (ContentStatus.APPROVED, ContentStatus.PENDING),
        (ContentStatus.REJECTED, ContentStatus.PENDING),
    ],
)
def test_valid_transitions(
    from_status: ContentStatus, to_status: ContentStatus
) -> None:
    req = make_req(from_status, to_status)
    assert req.from_status == from_status
    assert req.to_status == to_status


@pytest.mark.parametrize(
    "from_status, to_status",
    [
        (ContentStatus.RAW, ContentStatus.APPROVED),
        (ContentStatus.ANALYZED, ContentStatus.APPROVED),
        (ContentStatus.RAW, ContentStatus.USED),
        (ContentStatus.PENDING, ContentStatus.USED),
        (ContentStatus.APPROVED, ContentStatus.USED),
        (ContentStatus.REJECTED, ContentStatus.USED),
    ],
)
def test_invalid_transitions_raise(
    from_status: ContentStatus, to_status: ContentStatus
) -> None:
    with pytest.raises(ValueError):
        make_req(from_status, to_status)
