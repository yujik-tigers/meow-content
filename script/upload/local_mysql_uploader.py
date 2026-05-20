import os
from collections.abc import Sequence
from typing import override

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repository.mysql.models import Content
from script.upload.base import RawDataUploader


class LocalMySQLUploader(RawDataUploader):

    def __init__(self) -> None:
        self._host = os.environ["HOST"]
        self._port = int(os.environ["REMOTE_BIND_PORT"])
        self._user = os.environ["REMOTE_MYSQL_USER"]
        self._password = os.environ["REMOTE_MYSQL_PASSWORD"]
        self._database = os.environ["REMOTE_MYSQL_DATABASE"]

    @override
    async def upload(self, data: Sequence[Content]) -> None:
        engine = create_async_engine(
            URL.create(
                "mysql+aiomysql",
                username=self._user,
                password=self._password,
                host=self._host,
                port=self._port,
                database=self._database,
            )
        )
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as session:
            session.add_all(data)
            await session.commit()
