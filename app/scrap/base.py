from abc import ABC, abstractmethod

from app.schema.content import NewContent


class Scraper(ABC):

    @abstractmethod
    async def scrape(self) -> list[NewContent]: ...
