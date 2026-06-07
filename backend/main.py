import logging
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routers.chat import router as chat_router
from routers.locations import router as locations_router

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("services.relationship_service").setLevel(logging.INFO)
logging.getLogger("services.world_simulation").setLevel(logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(locations_router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "valdenmoor backend ok"}


@app.get("/debug/env-status")
async def env_status():
    credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("VERTEX_AI_SERVICE_ACCOUNT_JSON") or os.getenv("VERTEX_AI_CREDENTIALS")
    return {
        "vertex_credential_set": bool(credential_path),
        "vertex_credential_value": credential_path or "",
        "vertex_location": os.getenv("VERTEX_AI_LOCATION", "us-central1"),
        "vertex_model": os.getenv("VERTEX_AI_MODEL", "gemini-2.0-flash-001"),
    }


@app.post("/debug/reset-cache")
async def reset_prompt_cache():
    """narrator.md ve world.md cache'ini temizle — deploy sonrası hot-reload için."""
    import backend.services.prompt_builder as pb
    pb._NARRATOR_CACHE = None
    pb._WORLD_CACHE = None
    pb._CHARACTERS_CACHE = None
    return {"status": "ok", "message": "Prompt cache sıfırlandı"}
