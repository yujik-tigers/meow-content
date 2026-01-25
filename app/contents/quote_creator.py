import requests


class QuoteCreator:

    async def create_daily_quote(self) -> str:
        response = requests.get("https://zenquotes.io/api/today")
        response.raise_for_status()
        return response.json()[0]["q"]


quote_creator = QuoteCreator()
