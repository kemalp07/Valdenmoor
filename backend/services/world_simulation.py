"""
Valdenmoor Dünya Simülasyonu
- Her mesaj sonrası küçük stat erimesi
- Dravkor tehdit artışı
- Rastgele dünya olayları
"""

import logging
import random

from db.supabase_client import supabase

logger = logging.getLogger(__name__)


# ── Her mesajda uygulanan pasif stat değişimleri ──────────────────────────

_PASSIVE_DECAY = {
    # Hazine her turda biraz erir (ordu maaşı, saray giderleri)
    "treasury": -8,
    # Ordu morali maaş alamadığı için yavaş düşüyor
    "army_morale": -1,
    # Dravkor tehdit her turda biraz artıyor (sınır provokasyonları)
    "dravkor_threat": +1,
}

_STAT_BOUNDS = {
    "treasury": (0, 1000),
    "army_morale": (0, 100),
    "public_support": (0, 100),
    "prestige": (0, 100),
    "dravkor_threat": (0, 100),
}


def _clamp(value: int, key: str) -> int:
    lo, hi = _STAT_BOUNDS.get(key, (0, 100))
    return max(lo, min(hi, value))


def apply_passive_decay(session_id: str) -> dict:
    """Her mesaj sonrası pasif stat erimesini uygula. Değişen statları döner."""
    if not supabase:
        return {}
    try:
        resp = (
            supabase.table("game_stats")
            .select("treasury,army_morale,public_support,prestige,dravkor_threat")
            .eq("session_id", session_id)
            .execute()
        )
        if not resp.data:
            return {}

        current = resp.data[0]
        updates = {}

        for key, delta in _PASSIVE_DECAY.items():
            new_val = _clamp(current.get(key, 50) + delta, key)
            if new_val != current.get(key):
                updates[key] = new_val

        if updates:
            supabase.table("game_stats").update(updates).eq("session_id", session_id).execute()
            logger.info(f"[{session_id}] Passive decay applied: {updates}")

        return updates
    except Exception as e:
        logger.error(f"apply_passive_decay error: {e}")
        return {}


# ── Rastgele dünya olayları ────────────────────────────────────────────────

_WORLD_EVENTS = [
    {
        "id": "dravkor_scout",
        "condition": lambda s: s.get("dravkor_threat", 0) >= 65,
        "chance": 0.3,
        "narrator_injection": (
            "[NARRATOR]\nKuzeyden acil bir haberci geldi. "
            "Dawnhold yakınlarında Dravkor keşif birlikleri görüldü — "
            "sayıları normalin üçte biri. General Draven durum raporu istiyor."
        ),
        "stats_delta": {"dravkor_threat": +3},
    },
    {
        "id": "treasury_warning",
        "condition": lambda s: s.get("treasury", 500) < 150,
        "chance": 0.5,
        "narrator_injection": (
            "[NARRATOR]\nHazine Bakanı Sorn aceleyle kapıya dayandı. "
            "Kasada kalan altın bu ayın saray giderlerini zar zor karşılayacak. "
            "Ordu maaşları için ek kaynak bulunamazsa sorun büyüyecek."
        ),
        "stats_delta": {},
    },
    {
        "id": "army_morale_crisis",
        "condition": lambda s: s.get("army_morale", 50) < 25,
        "chance": 0.4,
        "narrator_injection": (
            "[NARRATOR]\nGeneral Caelan Voss'tan endişe verici haber: "
            "Ashenmoor garnizonunda üç asker firar etti. "
            "Diğerleri sessiz ama bakışları konuşuyor. "
            "Maaş meselesi artık acil."
        ),
        "stats_delta": {"army_morale": -3},
    },
    {
        "id": "public_unrest",
        "condition": lambda s: s.get("public_support", 50) < 30,
        "chance": 0.35,
        "narrator_injection": (
            "[NARRATOR]\nPazar meydanından sesler yükseliyor. "
            "Tomas, esnaf temsilcisi olarak sarayın kapısına geldi — "
            "vergi yükü dayanılmaz hale geldi, halk sabırsızlanıyor."
        ),
        "stats_delta": {},
    },
    {
        "id": "selmara_envoy",
        "condition": lambda s: s.get("prestige", 30) >= 40 and s.get("dravkor_threat", 0) >= 55,
        "chance": 0.2,
        "narrator_injection": (
            "[NARRATOR]\nSelmara'dan beklenmedik bir elçi geldi. "
            "Kral Edwyn'in mühürünü taşıyor — "
            "Dravkor hareketliliği doğuda da hissediliyormuş. "
            "İttifak görüşmesi teklif ediyor."
        ),
        "stats_delta": {},
    },
    {
        "id": "varethis_guild",
        "condition": lambda s: s.get("treasury", 500) < 300,
        "chance": 0.2,
        "narrator_injection": (
            "[NARRATOR]\nVarethis'ten lonca temsilcisi geldi. "
            "Liman vergileri üç aydır düzensiz toplanıyor — "
            "tüccarlar alternatif yollar aramaya başlamış. "
            "Hazineye katkı kaybolmadan önce bir karar gerekiyor."
        ),
        "stats_delta": {},
    },
]


def check_world_events(session_id: str) -> dict | None:
    """
    Mevcut stats'a bakarak tetiklenmesi gereken bir olay varsa döner.
    Her turda en fazla bir olay tetiklenir.
    """
    if not supabase:
        return None
    try:
        resp = (
            supabase.table("game_stats")
            .select("treasury,army_morale,public_support,prestige,dravkor_threat")
            .eq("session_id", session_id)
            .execute()
        )
        if not resp.data:
            return None

        stats = resp.data[0]
        eligible = [
            e for e in _WORLD_EVENTS
            if e["condition"](stats) and random.random() < e["chance"]
        ]

        if not eligible:
            return None

        # En kritik olayı seç (basit önceliklendirme: listede öne yakın)
        event = eligible[0]

        # Stats delta uygula
        if event.get("stats_delta"):
            updates = {}
            for key, delta in event["stats_delta"].items():
                current_val = stats.get(key, 50)
                updates[key] = _clamp(current_val + delta, key)
            if updates:
                supabase.table("game_stats").update(updates).eq("session_id", session_id).execute()

        logger.info(f"[{session_id}] World event triggered: {event['id']}")
        return event

    except Exception as e:
        logger.error(f"check_world_events error: {e}")
        return None


# ── Stub fonksiyonlar (chat.py uyumluluğu için) ───────────────────────────

async def run_point_simulation(
    session_id: str,
    conversation: list,
    player_house: str,
    week: int = 1,
    day: int = 1,
) -> dict:
    """Pasif decay uygula, dünya olaylarını kontrol et."""
    apply_passive_decay(session_id)
    event = check_world_events(session_id)
    narrator_injection = event["narrator_injection"] if event else None
    return {"missed": [], "surprise": None, "narrator_injection": narrator_injection}


async def extract_time_from_response(session_id: str, ai_response: str):
    pass


async def extract_inventory_and_location(session_id: str, ai_response: str):
    pass


def start_organic_scheduler():
    pass
