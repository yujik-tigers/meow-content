import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ContentNotFoundError, NoApprovedContentError
from app.repository.mysql.engine import create_tables
from app.router.admin import router as admin_router
from app.router.content import router as contents_router
from app.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(contents_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.exception_handler(ContentNotFoundError)
async def meme_not_found_handler(
    request: Request, exc: ContentNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(NoApprovedContentError)
async def no_approved_meme_handler(
    request: Request, exc: NoApprovedContentError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})
