"""
Karakter İlişki Servisi
- Her karakterle ilişki skoru (-100 ile +100)
- Sohbet sonrası AI analizi ile güncellenir
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


async def _call_vertex(prompt: str, max_tokens: int = 300) -> str:
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
            "temperature": 0.2,
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


def get_relationships(session_id: str) -> dict:
    if not supabase:
        return {}
    try:
        resp = (
            supabase.table("character_relations")
            .select("character_id,loyalty")
            .eq("session_id", session_id)
            .execute()
        )
        return {
            row["character_id"]: {
                "score": row.get("loyalty", 50),
                "relationship_type": "neutral",
            }
            for row in (resp.data or [])
        }
    except Exception as e:
        logger.error(f"get_relationships error: {e}")
        return {}


def update_relationship_type(session_id: str, character_name: str, new_type: str):
    """Romantik ilişki bayrağı — Valdenmoor'da loyalty skoru üzerinden yönetilir."""
    logger.info(f"[{session_id}] {character_name} relationship_type → {new_type} (loyalty tabanlı)")


def update_relationship(session_id: str, character_name: str, delta: int, reason: str):
    if not supabase:
        return
    try:
        resp = (
            supabase.table("character_relations")
            .select("loyalty")
            .eq("session_id", session_id)
            .eq("character_id", character_name)
            .execute()
        )
        current = (resp.data or [{}])[0].get("loyalty", 50) if resp.data else 50
        new_loyalty = max(0, min(100, current + delta))

        supabase.table("character_relations").upsert(
            {
                "session_id": session_id,
                "character_id": character_name,
                "loyalty": new_loyalty,
                "updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="session_id,character_id",
        ).execute()

        logger.info(f"[{session_id}] {character_name}: {current} → {new_loyalty} ({delta:+}: {reason})")
    except Exception as e:
        logger.error(f"update_relationship error: {e}")


async def analyze_relationship_changes(
    session_id: str,
    conversation: list,
    player_name: str,
    player_attraction: str = "Her ikisi",
):
    """
    Sohbeti analiz et, karakter ilişkilerini güncelle.
    Her yanıt sonrası background'da çalışır.
    """
    if not conversation:
        return

    recent = conversation[-12:]
    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:400]}" for m in recent
    )

    prompt = f"""Sen Valdenmoor krallığının gizli kayıt tutucususun.
Oyuncu: Kral/Kraliçe {player_name}

Aşağıdaki konuşmayı analiz et. Oyuncunun NPC'lerle etkileşimini değerlendir.
Sadece bu konuşmada aktif olan karakterleri değerlendir. Adı geçmeyen karakterlere puan uygulama.

Her değişim -15 ile +15 arasında olsun:
- Oyuncu bir karaktere saygılı/adil/cömert davrandıysa → pozitif
- Oyuncu bir karakteri tehdit etti/küçümsedi/görmezden geldiyse → negatif  
- Oyuncu karakterin çıkarına hizmet eden bir karar aldıysa → pozitif
- Oyuncu karakterin çıkarına zarar veren bir karar aldıysa → negatif
- Küçük etkileşimlerde -3/+3, büyük olaylarda ±15

KONUŞMA:
{conv_text}

ÖNEMLİ: "character" alanında mutlaka snake_case ID kullan:
lord_aldric_vane, lord_harwin_sorn, lord_cerin_vane, mira,
lord_commander_draven, commander_sera_ashford, general_caelan_voss,
priest_edran, tomas, lena, duke_malachar, general_harkon,
king_edwyn, princess_elowen, prince_aldric_selmara, sultan_rashid, envoy_zara

SADECE JSON döndür:
[
  {{"character": "lord_aldric_vane", "delta": -8, "reason": "Vezirin tavsiyesini reddetti"}},
  {{"character": "lord_harwin_sorn", "delta": 5, "reason": "Hazine bakanına güven gösterdi"}}
]

Değişim yoksa: []"""

    text = await _call_vertex(prompt, max_tokens=300)
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
            delta = int(ch.get("delta", 0))
            reason = ch.get("reason", "")
            if char and delta != 0:
                update_relationship(session_id, char, delta, reason)

    except Exception as e:
        logger.error(f"analyze_relationship_changes parse error: {e}")

    await check_romance_trigger(session_id, conversation, player_name, player_attraction)


async def check_romance_trigger(
    session_id: str,
    conversation: list,
    player_name: str,
    player_attraction: str = "Her ikisi",
):
    """
    Romantik ilişki tetikleyici kontrolü.
    Koşullar: skor >= 60 VE oyuncu açıkça ilgi göstermiş.
    """
    relationships = get_relationships(session_id)

    candidates = [
        (name, data)
        for name, data in relationships.items()
        if data["score"] >= 60 and data.get("relationship_type", "neutral") != "romance"
    ]

    if not candidates:
        return

    recent = conversation[-6:]
    conv_text = "\n".join(f"{m['role'].upper()}: {m['content'][:300]}" for m in recent)

    candidate_names = [name for name, _ in candidates]

    prompt = f"""Aşağıdaki sohbette oyuncu ({player_name}) şu karakterlerden herhangi birine açıkça romantik ilgi gösterdi mi?
Karakterler: {', '.join(candidate_names)}

Romantik ilgi örnekleri: aşık olduğunu söylemek, öpmek istemek, el tutmak, flört etmek, sevdiğini belirtmek.

KONUŞMA:
{conv_text}

SADECE JSON döndür (snake_case character_id kullan):
{{"romance_triggered": "princess_elowen"}}
veya
{{"romance_triggered": null}}"""

    text = await _call_vertex(prompt, max_tokens=50)
    if not text:
        return

    try:
        clean = text.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean.strip())
        triggered = data.get("romance_triggered")

        if triggered and triggered in [name for name, _ in candidates]:
            female_indicators = [
                "Elowen", "Mira", "Zara", "Sera", "Lena",
            ]
            is_female = any(ind in triggered for ind in female_indicators)

            allowed = False
            if player_attraction == "Kadınlar" and is_female:
                allowed = True
            elif player_attraction == "Erkekler" and not is_female:
                allowed = True
            elif player_attraction == "Her ikisi":
                allowed = True

            if allowed:
                update_relationship_type(session_id, triggered, "romance")
                logger.info(f"[{session_id}] Romance triggered with {triggered}!")
    except Exception as e:
        logger.error(f"check_romance_trigger error: {e}")


def build_relationship_context(session_id: str) -> str:
    """Mevcut ilişki skorlarını system prompt için formatla — davranış kurallarıyla birlikte."""
    relationships = get_relationships(session_id)
    if not relationships:
        return ""

    lines = []
    for char, data in relationships.items():
        score = data["score"] if isinstance(data, dict) else data

        if score == 50:
            continue  # başlangıç değeri, henüz etkileşim yok

        if score >= 70:
            behavior = "koşulsuz sadık. Her emri yerine getirir, tehlikeye atlar, sırrını korur."
        elif score >= 40:
            behavior = "güveniyor. Yardımcı olur ama kendi çıkarını da gözetir."
        elif score >= 15:
            behavior = "tarafsız ama olumlu. Makul istekleri kabul eder."
        elif score >= -15:
            behavior = "nötr. Ne yardım eder ne engel olur, durumu kollar."
        elif score >= -40:
            behavior = "soğuk ve mesafeli. Emirlere yavaş uyar, bilgi saklar."
        elif score >= -70:
            behavior = "düşmanca. Açıkça direnir, fırsat bulunca baltalar."
        else:
            behavior = "açık düşman. İhanet planlar, rakiplerle ittifak arar."

        lines.append(f"- {char} (sadakat: {score}): {behavior}")

    if not lines:
        return ""

    return (
        "## KARAKTER SADAKAT DURUMU — ZORUNLU UYGULA\n"
        + "\n".join(lines)
        + "\n\n"
        "**KRİTİK:** Bu sadakat skorları karakterlerin nasıl davranacağını belirler. "
        "Düşük sadakatli karakterler oyuncuya eyvallah demez, direnir, geciktirir, "
        "bilgi saklar veya açıkça reddeder. Yüksek sadakatli karakterler bile kendi "
        "ajandaları doğrultusunda hareket eder. Sadakat skoru ne olursa olsun hiçbir "
        "karakter aptal değildir — kendi çıkarını düşünür."
    )
