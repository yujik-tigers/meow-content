from dataclasses import dataclass

import requests


@dataclass
class Quote:
    text: str
    speaker: str


async def create_daily_quote() -> Quote:
    response = requests.get("https://zenquotes.io/api/today")
    response.raise_for_status()
    response_json = response.json()
    return Quote(
        text=response_json[0]["q"],
        speaker=response_json[0]["a"],
    )
