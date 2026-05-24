from abc import ABC, abstractmethod

from app.schema.content import Content, ReanalyzeContentField


class ContentAnalyzer(ABC):

    @abstractmethod
    async def analyze_raw_content(self, content: Content) -> Content: ...

    @abstractmethod
    async def reanalyze_content_field(
        self,
        current_content: Content,
        fields: list[ReanalyzeContentField],
    ) -> Content: ...
