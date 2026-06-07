import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import os
import uuid
import json
from services.prompt_builder import build_prompt
from services.memory_service import generate_summary, get_memories, maybe_summarize_and_compress, save_memory
from services.vertex_ai import stream_vertex_ai
from services.world_simulation import (
    run_point_simulation,
    check_world_events,
)
from services.relationship_service import analyze_relationship_changes
from services.stats_service import ensure_game_stats, apply_stats_delta
from services.session_service import (
    ensure_game_session,
    init_game_for_new_session,
    normalize_origin,
    normalize_ruling_style,
)
from services.character_service import get_character_relations, detect_character
from db.supabase_client import insert_message, supabase
import traceback
from pathlib import Path
from datetime import datetime

router = APIRouter()

_CHARACTER_ID_MAP = {
    "valdenmoor-narrator": "00000000-0000-0000-0000-000000000001",
    "hogwarts-narrator": "00000000-0000-0000-0000-000000000002",
}
logger = logging.getLogger(__name__)
_DEBUG_CHAT = os.getenv("DEBUG_CHAT", "").lower() in ("1", "true", "yes")

MAX_HISTORY_MESSAGES = 14


def _parse_stats_tag(text: str) -> dict:
    """AI yanıtındaki [STATS: treasury:-120, army_morale:+20] tag'ini parse et."""
    match = re.search(r"\[STATS:([^\]]+)\]", text)
    if not match:
        return {}
    delta = {}
    for part in match.group(1).split(","):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            key = key.strip()
            val = val.strip().replace("+", "")
            valid_keys = {"treasury", "army_morale", "public_support", "prestige", "dravkor_threat"}
            if key in valid_keys:
                try:
                    delta[key] = int(val)
                except ValueError:
                    pass
    return delta


def _strip_stats_tag(text: str) -> str:
    """[STATS:...] tag'ini yanıttan temizle — kullanıcı görmesin."""
    return re.sub(r"\s*\[STATS:[^\]]+\]", "", text).strip()


def _normalize_history_role(role: str) -> Optional[str]:
    if role in ("assistant", "ai"):
        return "assistant"
    if role == "user":
        return "user"
    return None


def _merge_history_and_current(history: list, current_user_content: str) -> list[dict]:
    """Merge client history with the current user turn; dedupe trailing user message."""
    merged: list[dict] = []

    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = _normalize_history_role(str(item.get("role", "")))
        if role is None:
            continue
        content = (item.get("content") or item.get("text") or "").strip()
        if not content:
            continue
        merged.append({"role": role, "content": content})

    current = (current_user_content or "").strip()
    if current:
        if not (
            merged
            and merged[-1]["role"] == "user"
            and merged[-1]["content"] == current
        ):
            merged.append({"role": "user", "content": current})

    return merged[-MAX_HISTORY_MESSAGES:]


def _user_message_count(conversation: list) -> int:
    return len([m for m in conversation if m.get("role") == "user"])


@router.get("/history")
async def history_endpoint(session_id: str = Query(..., min_length=1)):
    """Return message history for a session, ordered by created_at ascending."""
    if not supabase:
        return JSONResponse(content={"messages": []})

    try:
        resp = (
            supabase
            .table("messages")
            .select("role,content,created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        messages = getattr(resp, "data", None) or []
    except Exception:
        raise HTTPException(status_code=500, detail="Mesaj gecmisi okunamadi")

    return JSONResponse(content={"messages": messages})


@router.post("/chat-test")
async def chat_test(request: Request):
    """Quick test endpoint returning mock response."""
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id") or str(uuid.uuid4())
    user_name = body.get("user_name") or "Hükümdar"

    if message == "":
        mock_response = (
            f"Merhaba {user_name}! Valdenmoor krallığına hoş geldin. "
            "Taht odasında vezir Aldric Vane seni bekliyor."
        )
    else:
        mock_response = f"Yaptığın harita çok ilginç. Hemen yanıt verebileceğim: '{message}' - ancak şu anda Vertex AI bağlantıda sorun yaşanıyor. Lütfen servis hesabı JSON ve proje ayarlarını kontrol et. :)"

    return JSONResponse(content={"response": mock_response, "model": "test", "session_id": session_id})


@router.post("/chat")
async def chat_endpoint(request: Request):
    """Receives a simple chat request and forwards to the model.

    Request body accepted fields (defaults applied):
    - message: str (required)
    - session_id: str (optional)
    - character_id: str (default: "valdenmoor-narrator")
    - location_id: str (default: "throne_room")
    - user_name: str (default: "Hükümdar")
    - history: list[dict] (optional) prior turns [{"role": "user"|"assistant", "content": "..."}]
    """
    body = await request.json()
    message = body.get("message", "")
    history = body.get("history") or []
    session_id = body.get("session_id") or str(uuid.uuid4())
    _raw_cid = body.get("character_id") or "valdenmoor-narrator"
    character_id = _CHARACTER_ID_MAP.get(_raw_cid, _raw_cid)
    user_name = body.get("user_name") or "Hükümdar"
    character_profile = body.get("character_profile")
    language = body.get("language", "tr")

    pending_injection = None
    if supabase:
        try:
            inj_resp = (
                supabase.table("game_state")
                .select("pending_injection")
                .eq("session_id", session_id)
                .execute()
            )
            if inj_resp.data and inj_resp.data[0].get("pending_injection"):
                pending_injection = inj_resp.data[0]["pending_injection"]
                supabase.table("game_state").update(
                    {"pending_injection": None}
                ).eq("session_id", session_id).execute()
        except Exception as e:
            logger.error(f"pending_injection read error: {e}")

    user_message_for_model = message if message.strip() else (
        f"Kullanıcı henüz yazmadı. Valdenmoor açılış sahnesini başlat: "
        f"Vezir Aldric Vane {user_name} adlı hükümdara hazine raporu ve kuzey haberleriyle girsin. "
        f"world.md'deki ilk sahne kurallarına uy."
    )

    if pending_injection:
        user_message_for_model = (
            f"{pending_injection}\n\n"
            f"[Oyuncunun yanıtı]: {user_message_for_model}"
        )

    conversation_messages = _merge_history_and_current(history, user_message_for_model)
    conversation_for_memory = _merge_history_and_current(history, message)
    memories = await get_memories(session_id)

    profile = character_profile or {}
    ensure_game_session(
        session_id,
        user_name,
        profile.get("gender", "king"),
        profile.get("rulingStyle", "diplomatic"),
        profile.get("origin", "noble"),
    )
    game_stats = ensure_game_stats(session_id)
    character_relations = get_character_relations(session_id)

    messages_for_model = await build_prompt(
        user_name=user_name,
        messages=conversation_messages,
        memories=memories,
        game_stats=game_stats,
        character_relations=character_relations,
        character_profile=character_profile,
        language=language,
    )

    model = body.get("model") or os.getenv("VERTEX_AI_MODEL", "gemini-2.0-flash-001")
    memory_state = {
        "full_text": "",
        "conversation": conversation_for_memory,
    }

    player_attraction = (profile.get("attraction") or "Her ikisi")

    async def after_chat_response(sid: str, char_id: str, state: dict, ruler_name: str, attraction: str):
        full_text = str(state.get("full_text") or "").strip()
        conversation = list(state.get("conversation") or [])
        if full_text:
            conversation.append({"role": "assistant", "content": full_text})

        if len(full_text) > 200:
            summary = await generate_summary(conversation)
            if summary.strip():
                await save_memory(sid, char_id, summary.strip())
            await maybe_summarize_and_compress(sid, char_id, conversation)

        conv_len = _user_message_count(conversation)
        if conv_len % 5 == 0:
            event = check_world_events(sid)
            if event and event.get("narrator_injection"):
                try:
                    if supabase:
                        injection = event["narrator_injection"]
                        if "{player_name}" in injection:
                            injection = injection.format(player_name=ruler_name)
                        supabase.table("game_state").upsert({
                            "session_id": sid,
                            "pending_injection": injection,
                        }, on_conflict="session_id").execute()
                except Exception as e:
                    logger.error(f"pending_injection save error: {e}")

            try:
                await analyze_relationship_changes(sid, conversation, ruler_name, attraction)
            except Exception as e:
                logger.error(f"Relationship analysis error: {e}")

    async def save_messages(sid: str, user_text: str, assistant_text: str):
        try:
            insert_message(session_id=sid, character_id=character_id, role="user", content=user_text)
        except Exception:
            pass
        try:
            insert_message(session_id=sid, character_id=character_id, role="assistant", content=assistant_text)
        except Exception:
            pass

    full_text = ""

    async def generate():
        nonlocal full_text
        out_buf = ""
        FLUSH_CHARS = 24

        meta = json.dumps({
            "type": "meta",
            "session_id": session_id,
        })
        yield f"data: {meta}\n\n"

        try:
            system_prompt = ""
            if messages_for_model and messages_for_model[0].get("role") == "system":
                system_prompt = messages_for_model[0].get("content", "")
            if _DEBUG_CHAT:
                logger.debug("SYSTEM PROMPT (ilk 2000): %s", system_prompt[:2000])
            async for chunk in stream_vertex_ai(messages_for_model, model=model):
                full_text += chunk
                out_buf += chunk

                if len(out_buf) >= FLUSH_CHARS or "\n" in out_buf:
                    payload = json.dumps({"type": "chunk", "text": out_buf})
                    yield f"data: {payload}\n\n"
                    out_buf = ""

            if out_buf:
                payload = json.dumps({"type": "chunk", "text": out_buf})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            try:
                logs_dir = Path(__file__).resolve().parents[2] / "logs"
                logs_dir.mkdir(parents=True, exist_ok=True)
                log_path = logs_dir / "chat_error.log"
                ts = datetime.utcnow().isoformat() + "Z"
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write(f"[{ts}] Exception in generate(): {exc}\n")
                    traceback.print_exc(file=fh)
                    fh.write("\n")
            except Exception:
                pass

            stub = f"Vertex AI yanıt üretirken hata oluştu: {exc}"
            full_text += stub
            payload = json.dumps({"type": "chunk", "text": stub})
            yield f"data: {payload}\n\n"

        if _DEBUG_CHAT:
            logger.debug("AI FULL RESPONSE (ilk 1000): %s", full_text[:1000])
        char_name = detect_character(full_text)

        stats_delta = _parse_stats_tag(full_text)
        if stats_delta:
            _final_stats = apply_stats_delta(session_id, stats_delta)
        else:
            try:
                _final_stats = ensure_game_stats(session_id)
            except Exception:
                _final_stats = {}

        full_text = _strip_stats_tag(full_text)
        memory_state["full_text"] = full_text
        await save_messages(session_id, message, full_text)

        done = json.dumps({
            "type": "done",
            "character_name": char_name,
            "game_stats": _final_stats,
            "stats_changed": bool(stats_delta),
        })
        yield f"data: {done}\n\n"

    background_tasks = BackgroundTasks()
    background_tasks.add_task(
        after_chat_response,
        session_id,
        character_id,
        memory_state,
        user_name,
        player_attraction,
    )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        background=background_tasks,
    )


@router.post("/run-simulation")
async def run_simulation_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    _raw_cid = body.get("character_id") or "valdenmoor-narrator"
    character_id = _CHARACTER_ID_MAP.get(_raw_cid, _raw_cid)
    week = int(body.get("week", 1))
    day = int(body.get("day", 1))
    conversation = body.get("conversation", [])
    user_name = body.get("user_name", "Hükümdar")
    player_attraction = body.get("player_attraction", "Her ikisi")

    if not session_id:
        return JSONResponse(content={"status": "error", "detail": "session_id required"})

    logger.info(f"[{session_id}] Starting world simulation w={week} d={day}")
    try:
        await run_point_simulation(session_id, conversation, "", week, day)
        logger.info(f"[{session_id}] Simulation complete")
    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)

    if _user_message_count(conversation) % 5 == 0:
        try:
            await analyze_relationship_changes(
                session_id,
                conversation,
                user_name,
                player_attraction,
            )
        except Exception as e:
            logger.error(f"Relationship analysis error: {e}")

    stats = ensure_game_stats(session_id)

    return JSONResponse(content={
        "status": "ok",
        "game_stats": stats,
    })


@router.post("/delete-message")
async def delete_message_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    content = body.get("content", "")
    role = body.get("role", "user")

    if not session_id or not content:
        raise HTTPException(status_code=400, detail="session_id ve content gerekli")

    if supabase:
        supabase.table("messages").delete().eq("session_id", session_id).eq("content", content).eq("role", role).execute()

    return {"status": "ok"}


@router.post("/edit-message")
async def edit_message_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    old_content = body.get("old_content", "")
    new_content = body.get("new_content", "")
    role = body.get("role", "user")

    if not session_id or not old_content or not new_content:
        raise HTTPException(status_code=400, detail="session_id, old_content ve new_content gerekli")

    if old_content == new_content:
        return {"status": "ok"}

    if supabase:
        supabase.table("messages").update({"content": new_content}).eq(
            "session_id", session_id
        ).eq("content", old_content).eq("role", role).execute()

    return {"status": "ok"}


@router.delete("/api/messages")
async def delete_messages(session_id: str = Query(..., min_length=1)):
    """Delete all messages and memories for a given session_id."""
    if supabase:
        supabase.table("messages").delete().eq("session_id", session_id).execute()
        supabase.table("user_memories").delete().eq("session_id", session_id).execute()
    return {"status": "ok"}


@router.post("/save-character")
async def save_character(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    character = body.get("character", {})
    if not session_id or not character:
        raise HTTPException(status_code=400, detail="session_id ve character gerekli")

    if supabase:
        try:
            origin = normalize_origin(character.get("origin", "noble") or "noble")
            ruling_style = normalize_ruling_style(
                character.get("rulingStyle", "diplomatic") or "diplomatic"
            )
            ensure_game_session(
                session_id,
                character.get("name", ""),
                character.get("gender", "king") or "king",
                ruling_style,
                origin,
            )
            init_game_for_new_session(session_id, origin, ruling_style)
            supabase.table("characters").upsert({
                "id": character.get("id"),
                "session_id": session_id,
                "name": character.get("name", ""),
                "gender": character.get("gender", ""),
                "traits": character.get("traits", []),
                "origin": origin,
                "height": character.get("height", ""),
                "hair_color": character.get("hairColor", ""),
                "fear": character.get("fear", ""),
                "hobby": character.get("hobby", ""),
                "secret_trait": character.get("secretTrait", ""),
                "attraction": character.get("attraction", ""),
                "personality": character.get("traits", [" "])[0],
                "speech_style": "player",
                "base_prompt": "player_character",
                "is_active": True,
            }, on_conflict="id").execute()
        except Exception as e:
            logger.error(f"save_character error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"status": "ok"})


@router.post("/update-stats")
async def update_stats(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "")
    stats_delta = body.get("stats_delta") or {}

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id gerekli")
    if not isinstance(stats_delta, dict) or not stats_delta:
        raise HTTPException(status_code=400, detail="stats_delta gerekli")

    updated = apply_stats_delta(session_id, stats_delta)
    return JSONResponse(content={"status": "ok", "stats": updated})


@router.get("/game-stats")
async def get_game_stats_endpoint(session_id: str = Query(..., min_length=1)):
    """Mevcut oyun istatistiklerini döner."""
    stats = ensure_game_stats(session_id)
    return JSONResponse(content={"status": "ok", "stats": stats})


@router.get("/load-characters")
async def load_characters(session_id: str = Query(...)):
    if not supabase:
        return JSONResponse(content={"characters": []})
    try:
        resp = supabase.table("characters").select("*").eq("session_id", session_id).eq("base_prompt", "player_character").execute()
        return JSONResponse(content={"characters": resp.data or []})
    except Exception as e:
        logger.error(f"load_characters error: {e}")
        return JSONResponse(content={"characters": []})
