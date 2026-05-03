from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ApiResponse(Generic[T]):
    status_code: int
    status_message: str
    content: T
