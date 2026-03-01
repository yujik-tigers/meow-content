from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class Quote:
    text: str
    speaker: str


class QuoteCreator:

    async def create_daily_quote(self) -> Quote:
        response = requests.get("https://zenquotes.io/api/today")
        response.raise_for_status()
        response_json = response.json()
        return Quote(
            text=response_json[0]["q"],
            speaker=response_json[0]["a"],
        )


quote_creator = QuoteCreator()
