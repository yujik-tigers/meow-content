import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.tracers.context import register_configure_hook

from app.exceptions import ContentNotFoundError, NoApprovedContentError
from app.repository.mysql.engine import create_tables
from app.router.admin import router as admin_router
from app.router.content import router as contents_router
from app.scheduler import create_scheduler
from app.usage.usage_tracking import TokenUsageCallbackHandler, token_usage_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

usage_handler_var: ContextVar[TokenUsageCallbackHandler | None] = ContextVar(
    "token_usage_handler", default=None
)
register_configure_hook(usage_handler_var, inheritable=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def set_usage_handler(
    request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
) -> JSONResponse:
    usage_handler_var.set(token_usage_handler)
    return await call_next(request)


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
