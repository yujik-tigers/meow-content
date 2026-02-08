from dataclasses import dataclass
from datetime import date


@dataclass
class CreateContentRequest:
    created_at: date
