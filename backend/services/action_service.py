"""
Valdenmoor Action Sistemi
- Sabit action→delta tablosu
- Action classifier (Gemini)
- Button suggester (Gemini)
"""

import logging
import os

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest

from services.stats_service import apply_stats_delta, ensure_game_stats
from services.vertex_ai import DEFAULT_LOCATION, DEFAULT_MODEL, _load_service_account

logger = logging.getLogger(__name__)

# ── Sabit action → delta tablosu ──────────────────────────────────────────

ACTION_EFFECTS: dict[str, dict[str, int]] = {
    "pay_army":              {"treasury": -120, "army_morale": +15},
    "skip_army_pay":         {"army_morale": -20, "public_support": -5},
    "collect_tax_hard":      {"treasury": +100, "public_support": -20, "prestige": -5},
    "collect_tax_fair":      {"treasury": +60,  "public_support": -5},
    "tax_relief":            {"treasury": -60,  "public_support": +20, "prestige": +10},
    "public_feast":          {"treasury": -80,  "public_support": +25, "prestige": +5},
    "recruit_soldiers":      {"treasury": -100, "army_morale": +10},
    "build_fort":            {"treasury": -150, "army_morale": +5,  "friendship_dravkor": +5},
    "spy_mission":           {"treasury": -40},
    "trade_selmara":         {"treasury": -30,  "friendship_selmara": +15, "prestige": +8},
    "trade_varethis":        {"treasury": -20,  "friendship_varethis": +12},
    "trade_kadir":           {"treasury": -20,  "friendship_kadir": +12,   "prestige": +5},
    "send_envoy_dravkor":    {"treasury": -20,  "friendship_dravkor": +10, "prestige": +5},
    "send_envoy_selmara":    {"treasury": -15,  "friendship_selmara": +8},
    "send_envoy_kadir":      {"treasury": -15,  "friendship_kadir": +8},
    "send_envoy_varethis":   {"treasury": -15,  "friendship_varethis": +8},
    "declare_war_dravkor":   {"treasury": -200, "army_morale": -10, "friendship_dravkor": -30},
    "alliance_selmara":      {"treasury": -50,  "friendship_selmara": +20, "prestige": +15},
    "wait":                  {},
}

ACTION_LABELS: dict[str, str] = {
    "pay_army":              "💰 Asker maaşını öde",
    "skip_army_pay":         "⏳ Maaşı ertele",
    "collect_tax_hard":      "⚡ Sert vergi topla",
    "collect_tax_fair":      "📜 Adil vergi topla",
    "tax_relief":            "🤝 Vergi affı ilan et",
    "public_feast":          "🍖 Halka şölen ver",
    "recruit_soldiers":      "⚔️ Asker topla",
    "build_fort":            "🏰 Kale/karakol inşa et",
    "spy_mission":           "🕵️ Casusluk görevi",
    "trade_selmara":         "🤝 Selmara ticaret anlaşması",
    "trade_varethis":        "⚓ Varethis ticaret anlaşması",
    "trade_kadir":           "🌙 Kadir ticaret anlaşması",
    "send_envoy_dravkor":    "📨 Dravkor'a elçi gönder",
    "send_envoy_selmara":    "📨 Selmara'ya elçi gönder",
    "send_envoy_kadir":      "📨 Kadir'e elçi gönder",
    "send_envoy_varethis":   "📨 Varethis'e elçi gönder",
    "declare_war_dravkor":   "⚔️ Dravkor'a savaş ilan et",
    "alliance_selmara":      "🛡️ Selmara ile ittifak kur",
    "wait":                  "⏳ Bekle, izle",
}


async def _call_gemini(prompt: str, max_tokens: int = 100) -> str:
    """Küçük Gemini çağrısı — sadece sınıflandırma için."""
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
            "temperature": 0.1,
            "maxOutputTokens": max_tokens,
            "candidateCount": 1,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                return ""
            data = resp.json()
            candidates = data.get("candidates", [{}])
            parts = candidates[0].get("content", {}).get("parts", [{}])
            return parts[0].get("text", "").strip()
    except Exception as e:
        logger.error(f"action _call_gemini error: {e}")
        return ""


async def classify_action(
    session_id: str,
    user_message: str,
    ai_response: str,
) -> str | None:
    """
    Oyuncunun mesajını ve AI yanıtını okuyarak hangi action uygulandığını belirle.
    Hiçbir action yoksa None döner.
    """
    action_list = "\n".join(f"- {k}: {v}" for k, v in ACTION_LABELS.items())

    prompt = f"""Sen Valdenmoor krallık yönetim oyununun karar analizörüsün.

Oyuncunun mesajı: "{user_message}"
AI'ın yanıtı (özet): "{ai_response[:500]}"

Mevcut action listesi:
{action_list}

Oyuncu bu konuşmada aşağıdakilerden birini açıkça yaptı mı?
- Net bir karar verdi (emir, onay, red)
- Bir aksiyonu gerçekleştirdi

Eğer evet ise sadece action adını yaz (örnek: pay_army).
Eğer hayır ise (soru sordu, konuştu, belirsiz) sadece şunu yaz: none

Sadece tek kelime yaz, başka hiçbir şey yazma."""

    result = await _call_gemini(prompt, max_tokens=20)
    result = result.strip().lower().split()[0] if result else "none"

    if result == "none" or result not in ACTION_EFFECTS:
        return None

    return result


async def suggest_buttons(
    ai_response: str,
    current_stats: dict,
) -> list[dict]:
    """
    AI yanıtında karar soruluyor mu? Evet ise 2-3 mantıklı buton öner.
    """
    decision_keywords = [
        "ne yaparsınız", "emriniz", "onaylıyor musunuz", "ne emredersiniz",
        "karar sizin", "nasıl ilerleyelim", "ne dersiniz", "buyurun",
        "what would you", "your orders", "majeste",
    ]
    ai_lower = ai_response.lower()
    has_decision = any(kw in ai_lower for kw in decision_keywords)

    if not has_decision:
        return []

    treasury = current_stats.get("treasury", 450)
    army_morale = current_stats.get("army_morale", 40)

    affordable_actions = [
        k for k, v in ACTION_EFFECTS.items()
        if abs(v.get("treasury", 0)) <= treasury or v.get("treasury", 0) >= 0
    ]

    action_list = "\n".join(
        f"- {k}: {ACTION_LABELS[k]}"
        for k in affordable_actions
        if k in ACTION_LABELS
    )

    prompt = f"""Sen Valdenmoor krallık yönetim oyununun danışmanısın.

AI'ın son yanıtı: "{ai_response[:400]}"

Mevcut durum:
- Hazine: {treasury}
- Ordu morali: {army_morale}%

Mevcut action listesi:
{action_list}

Bu durumda oyuncuya sunulacak en mantıklı 2-3 action hangisi?
Sadece action isimlerini virgülle ayırarak yaz (örnek: pay_army,collect_tax_fair,wait)
Başka hiçbir şey yazma."""

    result = await _call_gemini(prompt, max_tokens=50)
    if not result:
        return []

    buttons = []
    for action_key in result.strip().split(","):
        action_key = action_key.strip().lower()
        if action_key in ACTION_LABELS and action_key in ACTION_EFFECTS:
            buttons.append({
                "action": action_key,
                "label": ACTION_LABELS[action_key],
            })

    return buttons[:3]


async def apply_action(session_id: str, action: str) -> dict:
    """Action'ı uygula, güncel stats'ı döndür."""
    if action not in ACTION_EFFECTS:
        return ensure_game_stats(session_id)

    delta = ACTION_EFFECTS[action]
    if not delta:
        return ensure_game_stats(session_id)

    return apply_stats_delta(session_id, delta)
