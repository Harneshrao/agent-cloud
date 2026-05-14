import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.agents import router as agents_router
from app.core.database import create_tables
from app.utils.error_handler import unhandled_exception_handler
import app.models.task  # noqa: F401 – registers ORM model with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Solana Agent MVP",
    description="Execution + Payment Infrastructure for AI Agents on Solana",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(agents_router)
app.add_exception_handler(Exception, unhandled_exception_handler)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
