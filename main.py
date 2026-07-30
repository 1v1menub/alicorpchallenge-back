from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.tracing import langfuse
from app.db.init_db import init_db
from app.routes import ads, auth, manuals


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enable pgvector, create tables, and seed roles/modules/users on startup.
    await init_db()
    yield
    langfuse.flush()  # flush any buffered Langfuse traces on shutdown


app = FastAPI(title="Content Suite API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(manuals.router)
app.include_router(ads.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
