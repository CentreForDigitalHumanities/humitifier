from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .views import router


def create_base_app() -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(router)
    return app
