import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.engine import create_tables
from app.routers.contents import router as contents_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(contents_router, prefix="/api/v1")
