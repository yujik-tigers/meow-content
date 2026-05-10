import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repository.mysql.engine import create_tables
from app.exceptions import MemeNotFoundError, NoApprovedMemeError
from app.router.contents import router as contents_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(contents_router, prefix="/api/v1")


@app.exception_handler(MemeNotFoundError)
async def meme_not_found_handler(
    request: Request, exc: MemeNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(NoApprovedMemeError)
async def no_approved_meme_handler(
    request: Request, exc: NoApprovedMemeError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})
