import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pipeline.poller import polling_worker
from api.routes import router
from core.logging import logger
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт
    logger.info("Инициализация адаптера...")
    await init_db()
    logger.info("БД готова.")

    task = asyncio.create_task(polling_worker())

    yield

    # Остановка
    logger.info("Остановка адаптера...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Фоновый поллинг остановлен.")


app = FastAPI(
    title="Competency Adapter",
    description="Polls LMS progress and forwards to Competency System webhook",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)