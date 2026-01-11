from fastapi import FastAPI

from app.routers.contents import router as contents_router

app = FastAPI()

app.include_router(contents_router, prefix="/api/v1")
