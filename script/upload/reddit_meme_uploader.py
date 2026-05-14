from dataclasses import dataclass
from pathlib import Path
from typing import override

from dotenv import load_dotenv

from script.upload.base import RawDataUploader


@dataclass(frozen=True)
class RedditMeme:
    img_url: str
    author: str
    title: str


class RedditMemeUploader(RawDataUploader[RedditMeme]):

    @override
    async def upload(self, data: RedditMeme) -> bool:

