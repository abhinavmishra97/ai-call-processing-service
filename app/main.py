from fastapi import FastAPI
from app.core.config import settings
from app.websocket import supervisor
from app.api import call_stream
from app.db.session import engine
from app.db.base import Base

async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.include_router(supervisor.router, prefix="/stream", tags=["websocket_stream"])
app.include_router(call_stream.router, prefix="/v1", tags=["call_stream"])

@app.get("/")
async def root():
    return {"message": "AI Call Processing Service is running"}
