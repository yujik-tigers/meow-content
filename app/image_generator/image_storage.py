from abc import ABC, abstractmethod

from PIL.Image import Image


class ImageStorage(ABC):

    @abstractmethod
    async def upload_image(self, image: Image, image_name: str) -> str: ...

    @abstractmethod
    async def download_image(self, image_url: str) -> Image: ...
