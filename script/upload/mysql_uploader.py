import os
from collections.abc import Sequence
from typing import override

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sshtunnel import SSHTunnelForwarder

from app.repository.mysql.models import Content
from script.upload.base import RawDataUploader


class MySQLUploader(RawDataUploader):

    def __init__(self) -> None:
        self._host = os.environ["HOST"]
        self._hostname = os.environ["HOSTNAME"]
        self._ssh_pkey = os.environ["SSH_PKEY"]
        self._remote_bind_port = int(os.environ["REMOTE_BIND_PORT"])
        self._remote_mysql_user = os.environ["REMOTE_MYSQL_USER"]
        self._remote_mysql_password = os.environ["REMOTE_MYSQL_PASSWORD"]
        self._remote_mysql_database = os.environ["REMOTE_MYSQL_DATABASE"]
        self._local_bind_port = int(os.environ["LOCAL_BIND_PORT"])

    @override
    async def upload(self, data: Sequence[Content]) -> None:
        with SSHTunnelForwarder(
            self._host,
            ssh_username=self._hostname,
            ssh_pkey=self._ssh_pkey,
            remote_bind_address=("localhost", self._remote_bind_port),
            local_bind_address=("localhost", self._local_bind_port),
        ) as tunnel:
            engine = create_async_engine(
                URL.create(
                    "mysql+aiomysql",
                    username=self._remote_mysql_user,
                    password=self._remote_mysql_password,
                    host="localhost",
                    port=self._local_bind_port,
                    database=self._remote_mysql_database,
                )
            )
            session_maker = async_sessionmaker(engine, expire_on_commit=False)
            async with session_maker() as session:
                session.add_all(data)
                await session.commit()
