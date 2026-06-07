import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import os
import uuid
import json
from services.prompt_builder import build_prompt
from services.memory_service import generate_summary, get_memories, maybe_summarize_and_compress, save_memory
from services.vertex_ai import stream_vertex_ai
from services.house_points_service import (
    get_game_state,
    check_inactivity_advance,
    build_narrator_day_message,
    advance_day,
    advance_hour,
    increment_message_count,
    check_sleep_trigger,
    get_message_count,
    get_location,
)
from services.world_simulation import (
    run_point_simulation,
    extract_time_from_response,
    extract_inventory_and_location,
    apply_passive_decay,
    check_world_events,
)
from services.relationship_service import analyze_relationship_changes
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

_DEFAULT_GAME_STATS = {
    "treasury": 450,
    "army_morale": 40,
    "public_support": 45,
    "prestige": 30,
    "dravkor_threat": 60,
}

_STAT_KEYS = tuple(_DEFAULT_GAME_STATS.keys())
_STAT_MAX = {
    "treasury": 1000,
    "army_morale": 100,
    "public_support": 100,
    "prestige": 100,
    "dravkor_threat": 100,
}

_NPC_CHARACTER_IDS = [
    "duke_malachar",
    "general_harkon",
    "king_edwyn",
    "princess_elowen",
    "prince_aldric_selmara",
    "sultan_rashid",
    "envoy_zara",
    "lord_aldric_vane",
    "lord_harwin_sorn",
    "lord_cerin_vane",
    "priest_edran",
    "mira",
    "general_caelan_voss",
    "lord_commander_draven",
    "commander_sera_ashford",
    "tomas",
    "lena",
]


def _get_initial_loyalty(character_id: str, origin: str, ruling_style: str) -> int:
    """Her karakterin başlangıç loyalty'si kendi doğasına ve oyuncunun kökenine göre belirlenir."""

    base = {
        "lord_aldric_vane": 45,
        "lord_harwin_sorn": 40,
        "lord_cerin_vane": 35,
        "priest_edran": 55,
        "mira": 70,
        "general_caelan_voss": 60,
        "lord_commander_draven": 55,
        "commander_sera_ashford": 65,
        "tomas": 60,
        "lena": 65,
        "duke_malachar": 10,
        "general_harkon": 15,
        "king_edwyn": 50,
        "princess_elowen": 55,
        "prince_aldric_selmara": 30,
        "sultan_rashid": 40,
        "envoy_zara": 35,
    }

    loyalty = base.get(character_id, 50)

    if origin == "warrior":
        if character_id in ("general_caelan_voss", "lord_commander_draven", "commander_sera_ashford"):
            loyalty += 10
    elif origin == "merchant":
        if character_id in ("tomas", "sultan_rashid", "envoy_zara"):
            loyalty += 8
        if character_id in ("lord_harwin_sorn",):
            loyalty -= 5
    elif origin == "noble":
        if character_id in ("lord_aldric_vane", "lord_cerin_vane"):
            loyalty += 5
        if character_id in ("tomas", "lena"):
            loyalty -= 5

    if ruling_style == "harsh":
        if character_id in ("general_caelan_voss", "lord_commander_draven"):
            loyalty += 5
        if character_id in ("tomas", "lena", "priest_edran"):
            loyalty -= 8
    elif ruling_style == "diplomatic":
        if character_id in ("princess_elowen", "king_edwyn"):
            loyalty += 8
        if character_id in ("duke_malachar",):
            loyalty += 5
    elif ruling_style == "cunning":
        if character_id in ("mira", "envoy_zara"):
            loyalty += 5
        if character_id in ("lord_aldric_vane",):
            loyalty -= 8

    return max(5, min(95, loyalty))


def _normalize_gender(gender: str) -> str:
    return gender if gender in ("king", "queen") else "king"


def _normalize_ruling_style(style: str) -> str:
    return style if style in ("harsh", "diplomatic", "cunning") else "diplomatic"


def _normalize_origin(origin: str) -> str:
    return origin if origin in ("warrior", "merchant", "noble") else "noble"


def _stats_for_origin(origin: str) -> dict:
    stats = dict(_DEFAULT_GAME_STATS)
    if origin == "warrior":
        stats["army_morale"] = 55
        stats["treasury"] = 400
    elif origin == "merchant":
        stats["treasury"] = 550
        stats["army_morale"] = 35
    elif origin == "noble":
        stats["prestige"] = 45
    return stats


def _ensure_game_session(
    session_id: str,
    player_name: str,
    gender: str = "king",
    ruling_style: str = "diplomatic",
    origin: str = "noble",
) -> None:
    if not supabase:
        return
    try:
        supabase.table("game_sessions").upsert(
            {
                "id": session_id,
                "player_name": player_name,
                "gender": _normalize_gender(gender),
                "ruling_style": _normalize_ruling_style(ruling_style),
                "origin": _normalize_origin(origin),
            },
            on_conflict="id",
        ).execute()
    except Exception as e:
        logger.error(f"ensure_game_session error: {e}")


def _init_game_for_new_session(session_id: str, origin: str, ruling_style: str = "diplomatic") -> None:
    if not supabase:
        return
    origin = _normalize_origin(origin)
    ruling_style = _normalize_ruling_style(ruling_style)
    try:
        stats_resp = (
            supabase.table("game_stats")
            .select("session_id")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if not stats_resp.data:
            supabase.table("game_stats").insert(
                {"session_id": session_id, **_stats_for_origin(origin)}
            ).execute()

        relations_resp = (
            supabase.table("character_relations")
            .select("character_id")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if not relations_resp.data:
            rows = [
                {
                    "session_id": session_id,
                    "character_id": character_id,
                    "loyalty": _get_initial_loyalty(character_id, origin, ruling_style),
                }
                for character_id in _NPC_CHARACTER_IDS
            ]
            supabase.table("character_relations").insert(rows).execute()
    except Exception as e:
        logger.error(f"init_game_for_new_session error: {e}")


def _ensure_game_stats(session_id: str) -> dict:
    if not supabase:
        return dict(_DEFAULT_GAME_STATS)

    try:
        resp = (
            supabase.table("game_stats")
            .select("treasury,army_morale,public_support,prestige,dravkor_threat")
            .eq("session_id", session_id)
            .execute()
        )
        if resp.data:
            return resp.data[0]

        supabase.table("game_stats").insert(
            {"session_id": session_id, **_DEFAULT_GAME_STATS}
        ).execute()
        return dict(_DEFAULT_GAME_STATS)
    except Exception as e:
        logger.error(f"ensure_game_stats error: {e}")
        return dict(_DEFAULT_GAME_STATS)


def _apply_stats_delta(session_id: str, stats_delta: dict) -> dict:
    current = _ensure_game_stats(session_id)
    updated = dict(current)

    for key in _STAT_KEYS:
        if key not in stats_delta:
            continue
        try:
            delta = int(stats_delta[key])
        except (TypeError, ValueError):
            continue
        cap = _STAT_MAX.get(key, 100)
        updated[key] = max(0, min(cap, int(updated.get(key, 0)) + delta))

    if supabase:
        try:
            supabase.table("game_stats").upsert(
                {
                    "session_id": session_id,
                    **{key: updated[key] for key in _STAT_KEYS},
                },
                on_conflict="session_id",
            ).execute()
        except Exception as e:
            logger.error(f"apply_stats_delta error: {e}")

    return updated


def _get_character_relations(session_id: str) -> list[dict]:
    if not supabase:
        return []
    try:
        resp = (
            supabase.table("character_relations")
            .select("character_id,loyalty")
            .eq("session_id", session_id)
            .order("character_id")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.error(f"get_character_relations error: {e}")
        return []


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


def detect_character(text: str) -> str:
    """Extract first character tag from AI response, fallback to Narrator."""
    import re
    tag_to_name = {
        "LORD_ALDRIC_VANE": "Lord Aldric Vane",
        "LORD_HARWIN_SORN": "Lord Harwin Sorn",
        "LORD_CERIN_VANE": "Lord Cerin Vane",
        "MIRA": "Mira",
        "LORD_COMMANDER_DRAVEN": "Lord Commander Draven",
        "COMMANDER_SERA_ASHFORD": "Komutan Sera Ashford",
        "GENERAL_CAELAN_VOSS": "General Caelan Voss",
        "PRIEST_EDRAN": "Rahip Edran",
        "TOMAS": "Tomas",
        "LENA": "Lena",
        "DUKE_MALACHAR": "Dük Malachar",
        "GENERAL_HARKON": "General Harkon",
        "KING_EDWYN": "Kral Edwyn",
        "PRINCESS_ELOWEN": "Prenses Elowen",
        "PRINCE_ALDRIC_SELMARA": "Prens Aldric",
        "SULTAN_RASHID": "Sultan Rashid",
        "ENVOY_ZARA": "Elçi Zara",
    }
    for match in re.finditer(r'^\[([A-Z_]+)\]', text, re.MULTILINE):
        tag = match.group(1)
        if tag in tag_to_name:
            return tag_to_name[tag]
    return "Anlatıcı"


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

# Test endpoint for fast responses (dev/debugging)
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
    location_id = body.get("location_id") or "throne_room"
    user_name = body.get("user_name") or "Hükümdar"
    character_profile = body.get("character_profile")
    language = body.get("language", "tr")

    # Inactivity kontrolü → otomatik gün geçişi
    day_advanced = check_inactivity_advance(session_id, threshold_minutes=30)

    # last_activity_at güncelle — scheduler sadece aktif sessionlara drift uygulasın
    if supabase:
        try:
            supabase.table("game_state").upsert(
                {"session_id": session_id, "last_activity_at": datetime.utcnow().isoformat()},
                on_conflict="session_id"
            ).execute()
        except Exception as e:
            logger.error(f"last_activity_at update error: {e}")

    increment_message_count(session_id)

    sleep_triggered = check_sleep_trigger(message)
    if sleep_triggered:
        advance_hour(session_id, hours=14)

    game_state = get_game_state(session_id)

    narrator_injection = None
    if game_state.get("current_hour") == 8 or sleep_triggered or day_advanced:
        narrator_injection = build_narrator_day_message(session_id)

    # allow empty message for initial opening prompts; message may be empty string

    # Vertex AI does not like empty user turns, so we supply a short opening instruction when needed.
    user_message_for_model = message if message.strip() else (
        f"Kullanıcı henüz yazmadı. Valdenmoor açılış sahnesini başlat: "
        f"Vezir Aldric Vane {user_name} adlı hükümdara hazine raporu ve kuzey haberleriyle girsin. "
        f"world.md'deki ilk sahne kurallarına uy."
    )

    conversation_messages = _merge_history_and_current(history, user_message_for_model)
    conversation_for_memory = _merge_history_and_current(history, message)
    memories = await get_memories(session_id)

    profile = character_profile or {}
    _ensure_game_session(
        session_id,
        user_name,
        profile.get("gender", "king"),
        profile.get("rulingStyle", "diplomatic"),
        profile.get("origin", "noble"),
    )
    game_stats = _ensure_game_stats(session_id)
    character_relations = _get_character_relations(session_id)

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

        check_world_events(sid)

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
            "location": get_location(session_id),
            "narrator_injection": narrator_injection,
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

                # Vertex bazen küçük delta'lar döndürür; event sayısını azaltmak için birleştiriyoruz.
                if len(out_buf) >= FLUSH_CHARS or "\n" in out_buf:
                    payload = json.dumps({"type": "chunk", "text": out_buf})
                    yield f"data: {payload}\n\n"
                    out_buf = ""

            if out_buf:
                payload = json.dumps({"type": "chunk", "text": out_buf})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            # write full traceback to logs/chat_error.log for debugging
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

        memory_state["full_text"] = full_text
        if _DEBUG_CHAT:
            logger.debug("AI FULL RESPONSE (ilk 1000): %s", full_text[:1000])
        char_name = detect_character(full_text)
        await save_messages(session_id, message, full_text)

        apply_passive_decay(session_id)
        try:
            _final_stats = _ensure_game_stats(session_id)
        except Exception:
            _final_stats = {}

        done = json.dumps({
            "type": "done",
            "character_name": char_name,
            "location": get_location(session_id),
            "game_stats": _final_stats,
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
    ai_response = body.get("ai_response", "")

    if not session_id:
        return JSONResponse(content={"status": "error", "detail": "session_id required"})

    logger.info(f"[{session_id}] Starting world simulation w={week} d={day}")
    sim_result = {"missed": [], "surprise": None, "narrator_injection": None}
    try:
        sim_result = await run_point_simulation(session_id, conversation, "", week, day)
        logger.info(f"[{session_id}] Simulation complete")
    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)

    narrator_injection = sim_result.get("narrator_injection")
    if narrator_injection and ai_response:
        ai_response = ai_response + "\n\n" + narrator_injection

    if ai_response:
        try:
            last_user_content = next(
                (t.get("content", "") for t in reversed(conversation) if t.get("role") == "user"),
                "",
            )
            sleep_triggered = check_sleep_trigger(last_user_content)
            # Önce otomatik +1 saat ilerlet (uyku haricinde zaten advance_hour çağrılmadıysa)
            if not sleep_triggered:
                advance_hour(session_id, hours=1)
            # Sonra AI tag'i varsa override et (büyük atlamalar için)
            await extract_time_from_response(session_id, ai_response)
            try:
                await extract_inventory_and_location(session_id, ai_response)
            except Exception as e:
                logger.error(f"extract_inventory_and_location error: {e}")
            # Her 3 mesajda bir episodic memory kaydet
            msg_count = get_message_count(session_id)
            if msg_count > 0 and msg_count % 3 == 0:
                try:
                    recent_for_memory = conversation[-10:]
                    episodic_summary = await generate_summary(recent_for_memory)
                    if episodic_summary:
                        await save_memory(session_id, character_id, episodic_summary)
                except Exception as e:
                    logger.error(f"Episodic memory error: {e}")
        except Exception as e:
            logger.error(f"extract_time_from_response error: {e}")

    try:
        await analyze_relationship_changes(
            session_id,
            conversation,
            user_name,
            player_attraction,
        )
    except Exception as e:
        logger.error(f"Relationship analysis error: {e}")

    state = get_game_state(session_id)
    stats = _ensure_game_stats(session_id)

    return JSONResponse(content={
        "status": "ok",
        "location": get_location(session_id),
        "game_stats": stats,
        "game_state": {
            "week": state.get("current_week", 1),
            "day": state.get("current_day", 1),
            "current_hour": state.get("current_hour", 8),
        },
        "narrator_injection": sim_result.get("narrator_injection"),
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
            origin = _normalize_origin(character.get("origin", "noble") or "noble")
            ruling_style = _normalize_ruling_style(
                character.get("rulingStyle", "diplomatic") or "diplomatic"
            )
            _ensure_game_session(
                session_id,
                character.get("name", ""),
                character.get("gender", "king") or "king",
                ruling_style,
                origin,
            )
            _init_game_for_new_session(session_id, origin, ruling_style)
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

    updated = _apply_stats_delta(session_id, stats_delta)
    return JSONResponse(content={"status": "ok", "stats": updated})


@router.get("/game-stats")
async def get_game_stats_endpoint(session_id: str = Query(..., min_length=1)):
    """Mevcut oyun istatistiklerini döner."""
    stats = _ensure_game_stats(session_id)
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

