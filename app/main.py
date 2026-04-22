import logging

from fastapi import FastAPI

from app.routers.contents import router as contents_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.include_router(contents_router, prefix="/api/v1")
