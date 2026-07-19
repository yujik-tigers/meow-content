from abc import ABC, abstractmethod

from PIL.Image import Image


class ImageStorage(ABC):

    @abstractmethod
    async def upload_image(self, image: Image, image_name: str) -> str: ...
