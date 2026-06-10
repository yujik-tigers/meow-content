from abc import ABC, abstractmethod

from app.schema.content import Content


class ImageGenerator(ABC):

    @abstractmethod
    async def generate(self, content: Content) -> Content: ...

    @abstractmethod
    async def regenerate(
        self,
        content: Content,
        prompt: str,
    ) -> Content: ...
