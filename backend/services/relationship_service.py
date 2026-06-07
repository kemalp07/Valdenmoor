"""
Valdenmoor Karakter İlişki Servisi
- Sayısal loyalty yerine sözel durum sistemi
- Her konuşma sonrası Gemini durumu günceller
- System prompt'a enjekte edilir
"""

import json
import logging
import os
from datetime import datetime

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest

from db.supabase_client import supabase
from services.vertex_ai import DEFAULT_LOCATION, DEFAULT_MODEL, _load_service_account

logger = logging.getLogger(__name__)

CHARACTER_NAMES = {
    "lord_aldric_vane": "Lord Aldric Vane",
    "lord_harwin_sorn": "Lord Harwin Sorn",
    "lord_cerin_vane": "Lord Cerin Vane",
    "mira": "Mira",
    "lord_commander_draven": "Lord Komutan Draven",
    "commander_sera_ashford": "Komutan Sera Ashford",
    "general_caelan_voss": "General Caelan Voss",
    "priest_edran": "Rahip Edran",
    "tomas": "Tomas",
    "lena": "Lena",
    "duke_malachar": "Dük Malachar",
    "general_harkon": "General Harkon",
    "king_edwyn": "Kral Edwyn",
    "princess_elowen": "Prenses Elowen",
    "prince_aldric_selmara": "Prens Aldric",
    "sultan_rashid": "Sultan Rashid",
    "envoy_zara": "Elçi Zara",
}


async def _call_vertex(prompt: str, max_tokens: int = 400) -> str:
    credentials, project_id = _load_service_account()
    if not credentials or not project_id:
        return ""
    if not credentials.token:
        try:
            credentials.refresh(GoogleAuthRequest())
        except Exception:
            return ""

    location = os.getenv("VERTEX_AI_LOCATION", DEFAULT_LOCATION)
    model_name = os.getenv("VERTEX_AI_MODEL", DEFAULT_MODEL)
    api_host = (
        "https://aiplatform.googleapis.com"
        if location == "global"
        else f"https://{location}-aiplatform.googleapis.com"
    )
    url = (
        f"{api_host}/v1/projects/{project_id}/locations/{location}"
        f"/publishers/google/models/{model_name}:generateContent"
    )
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": max_tokens,
            "candidateCount": 1,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                return ""
            data = resp.json()
            candidates = data.get("candidates", [{}])
            parts = candidates[0].get("content", {}).get("parts", [{}])
            return parts[0].get("text", "").strip()
    except Exception as e:
        logger.error(f"relationship _call_vertex error: {e}")
        return ""


def get_character_statuses(session_id: str) -> dict[str, str]:
    """Tüm karakterlerin mevcut durum metinlerini döner."""
    if not supabase:
        return {}
    try:
        resp = (
            supabase.table("character_relations")
            .select("character_id,status")
            .eq("session_id", session_id)
            .execute()
        )
        return {
            row["character_id"]: row.get("status") or ""
            for row in (resp.data or [])
            if row.get("status")
        }
    except Exception as e:
        logger.error(f"get_character_statuses error: {e}")
        return {}


def update_character_status(session_id: str, character_id: str, status: str):
    """Karakterin durum metnini güncelle."""
    if not supabase:
        return
    try:
        supabase.table("character_relations").upsert(
            {
                "session_id": session_id,
                "character_id": character_id,
                "status": status,
                "status_updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="session_id,character_id",
        ).execute()
        logger.info(f"[{session_id}] {character_id} → {status}")
    except Exception as e:
        logger.error(f"update_character_status error: {e}")


async def analyze_relationship_changes(
    session_id: str,
    conversation: list,
    player_name: str,
    player_attraction: str = "Her ikisi",
):
    """
    Konuşmayı analiz et, etkilenen karakterlerin durumunu sözel olarak güncelle.
    Her 5 mesajda bir background'da çalışır.
    """
    if not conversation:
        return

    recent = conversation[-12:]
    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:400]}" for m in recent
    )

    current_statuses = get_character_statuses(session_id)
    status_context = ""
    if current_statuses:
        status_context = "\nMevcut durumlar:\n" + "\n".join(
            f"- {CHARACTER_NAMES.get(k, k)}: {v}"
            for k, v in current_statuses.items()
        )

    prompt = f"""Sen Valdenmoor krallığının gizli kayıt tutucususun.
Oyuncu: Kral/Kraliçe {player_name}
{status_context}

Aşağıdaki konuşmayı analiz et. Sadece bu konuşmada aktif olan veya doğrudan etkilenen karakterleri değerlendir.

Her etkilenen karakter için kısa bir durum metni yaz (maksimum 10 kelime, Türkçe):
- Karakterin oyuncuya karşı şu anki tutumunu yansıt
- Somut ol: "kızgın" değil "hazine kararından dolayı güvensiz"
- Önemli olayları dahil et: idam, terfi, hakaret, ödül

KONUŞMA:
{conv_text}

SADECE JSON döndür (snake_case character_id kullan):
[
  {{"character": "lord_aldric_vane", "status": "Hazine krizini yönetememeni sorguluyor"}},
  {{"character": "general_caelan_voss", "status": "İdam kararından sonra mesafe koyuyor"}}
]

Etkilenen karakter yoksa: []

Geçerli character_id'ler:
lord_aldric_vane, lord_harwin_sorn, lord_cerin_vane, mira,
lord_commander_draven, commander_sera_ashford, general_caelan_voss,
priest_edran, tomas, lena, duke_malachar, general_harkon,
king_edwyn, princess_elowen, prince_aldric_selmara, sultan_rashid, envoy_zara"""

    text = await _call_vertex(prompt, max_tokens=400)
    if not text:
        return

    try:
        clean = text.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        changes = json.loads(clean.strip())
        if not isinstance(changes, list):
            return

        for ch in changes:
            char = ch.get("character", "").strip()
            status = ch.get("status", "").strip()
            if char and status and char in CHARACTER_NAMES:
                update_character_status(session_id, char, status)

    except Exception as e:
        logger.error(f"analyze_relationship_changes parse error: {e}")


def build_relationship_context(session_id: str) -> str:
    """
    Karakter durumlarını system prompt için formatla.
    Narrator bu bilgiyi kullanarak karakterleri gerçekçi oynar.
    """
    statuses = get_character_statuses(session_id)
    if not statuses:
        return ""

    lines = []
    for char_id, status in statuses.items():
        name = CHARACTER_NAMES.get(char_id, char_id)
        lines.append(f"- {name}: {status}")

    if not lines:
        return ""

    return (
        "## KARAKTER DURUMLARI — ZORUNLU UYGULA\n"
        + "\n".join(lines)
        + "\n\n"
        "**KRİTİK:** Bu durumlar karakterlerin davranışını belirler. "
        "Karakterler bu durumlarıyla tutarlı davranır. "
        "Olumsuz durumu olan karakter oyuncuya eyvallah demez — "
        "direnir, bilgi saklar, fırsatı kollar. "
        "Hiçbir karakter aptal değildir, kendi çıkarını düşünür."
    )


def get_relationships(session_id: str) -> dict:
    """Eski API — geriye dönük uyumluluk için."""
    statuses = get_character_statuses(session_id)
    return {k: {"score": 50, "status": v} for k, v in statuses.items()}


def update_relationship(session_id: str, character_name: str, delta: int, reason: str):
    """Eski API — artık kullanılmıyor."""
    pass


def update_relationship_type(session_id: str, character_name: str, new_type: str):
    """Eski API — artık kullanılmıyor."""
    pass
