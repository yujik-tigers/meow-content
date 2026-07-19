from abc import ABC, abstractmethod

from app.schema.content import Content


class ContentAnalyzer(ABC):

    @abstractmethod
    async def analyze_raw_content(self, content: Content) -> Content: ...
