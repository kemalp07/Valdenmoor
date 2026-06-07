"""
Valdenmoor Dünya Simülasyonu
- Karar bazlı ekonomi (AI STATS tag)
- Rastgele dünya olayları
"""

import logging
import random

from db.supabase_client import supabase

logger = logging.getLogger(__name__)

_STAT_BOUNDS = {
    "treasury": (0, 1000),
    "army_morale": (0, 100),
    "public_support": (0, 100),
    "prestige": (0, 100),
    "rel_dravkor": (0, 100),
    "rel_selmara": (0, 100),
    "rel_varethis": (0, 100),
    "rel_kadir": (0, 100),
}

_STAT_SELECT = (
    "treasury,army_morale,public_support,prestige,"
    "rel_dravkor,rel_selmara,rel_varethis,rel_kadir"
)


def _clamp(value: int, key: str) -> int:
    lo, hi = _STAT_BOUNDS.get(key, (0, 100))
    return max(lo, min(hi, value))


# ── Rastgele dünya olayları ────────────────────────────────────────────────

_WORLD_EVENTS = [
    {
        "id": "dravkor_scout",
        "condition": lambda s: s.get("rel_dravkor", 0) >= 65,
        "chance": 0.3,
        "narrator_injection": (
            "[NARRATOR]\nKuzeyden acil bir haberci geldi. "
            "Dawnhold yakınlarında Dravkor keşif birlikleri görüldü — "
            "sayıları normalin üçte biri. General Draven durum raporu istiyor."
        ),
        "stats_delta": {"rel_dravkor": +3},
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
        "condition": lambda s: s.get("prestige", 30) >= 40 and s.get("rel_dravkor", 0) >= 55,
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
    {
        "id": "tax_collection_due",
        "condition": lambda s: s.get("treasury", 500) < 400,
        "chance": 0.4,
        "narrator_injection": (
            "[NARRATOR]\n"
            "Hazine Bakanı Sorn sabah divanına belgelerle geldi. "
            "Bu çeyreğin vergi tahsilatı için köy muhtarlarından haberler var — "
            "bazı bölgeler ödemeyi geciktiriyor, bazıları erken göndermiş. "
            "Tahsilat kararını {player_name} verecek.\n\n"
            "**Seçenekler:** Sert tahsilat emri ver, adil ama kararlı ol, ya da bu dönem ertele."
        ),
    },
    {
        "id": "merchant_guild_offer",
        "condition": lambda s: s.get("treasury", 500) < 300,
        "chance": 0.3,
        "narrator_injection": (
            "[NARRATOR]\n"
            "Varethis'ten Lonca Başkanı Doran, sarayın önünde bekliyor. "
            "Hazine sıkıntısı kulağına gitmiş — elinde bir kredi teklifi var. "
            "Ama Doran'ın teklifleri her zaman bir bedelle gelir.\n\n"
            "[LORD_ALDRIC_VANE]\n"
            "\"Majeste, lonca adamlarına borçlanmak tehlikeli. "
            "Ama seçeneklerimiz azalıyor — karar sizin.\""
        ),
    },
    {
        "id": "army_pay_overdue",
        "condition": lambda s: s.get("army_morale", 50) < 30 and s.get("treasury", 500) > 100,
        "chance": 0.5,
        "narrator_injection": (
            "[NARRATOR]\n"
            "General Caelan Voss'tan acil mesaj: Ashenmoor garnizonundaki askerler "
            "iki haftadır maaş almadı. Voss, durumun kontrolden çıkmadan önce "
            "hazineden ödeme yapılmasını talep ediyor. Tam ödeme yaklaşık 120-150 altın tutacak.\n\n"
            "[GENERAL_CAELAN_VOSS]\n"
            "\"Majeste, adamlarım sizin için savaşıyor. "
            "Ailelerine ekmek götüremezlerse bu sadakat ne kadar sürer?\""
        ),
    },
    {
        "id": "northern_mine_report",
        "condition": lambda s: s.get("rel_dravkor", 0) < 50,
        "chance": 0.25,
        "narrator_injection": (
            "[NARRATOR]\n"
            "Kuzey maden ocaklarından Usta Brennan rapor gönderdi: "
            "Son iki ayda çıkarılan maden normalin üstünde. "
            "Fazla üretimi krallık adına işletebilir ya da özel tüccarlara satabilirsiniz. "
            "Her iki seçeneğin de hazine ve halk üzerinde farklı etkileri olacak."
        ),
    },
    {
        "id": "selmara_trade_disruption",
        "condition": lambda s: s.get("prestige", 30) < 35,
        "chance": 0.3,
        "narrator_injection": (
            "[NARRATOR]\n"
            "Selmara ticaret yolunda bir sorun var: Elçi Zara, "
            "Kral Edwyn'in bu yıl ticaret vergisini artırdığını bildirdi. "
            "Valdenmoor ya bu artışı kabul edecek ya da alternatif yol arayacak. "
            "Her iki seçenek de hazineyi farklı etkiler.\n\n"
            "[ENVOY_ZARA]\n"
            "\"Kral Edwyn müzakereye açık — ama zamanımız kısıtlı.\""
        ),
    },
    {
        "id": "harvest_surplus",
        "condition": lambda s: s.get("public_support", 50) > 55 and s.get("treasury", 500) < 500,
        "chance": 0.2,
        "narrator_injection": (
            "[NARRATOR]\n"
            "Bu yıl hasat beklenenden iyi geçti. "
            "Köy temsilcileri fazla ürünü sarayın ambarlarına bağışlamak istiyor — "
            "karşılığında küçük bir vergi indirimi talep ediyorlar. "
            "Anlaşırsanız hazineye dolaylı katkı sağlar, halk desteği artar."
        ),
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
            .select(_STAT_SELECT)
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

        event = random.choice(eligible)

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
    player_house: str = "",
    week: int = 1,
    day: int = 1,
) -> dict:
    """Dünya olaylarını kontrol et."""
    event = check_world_events(session_id)
    narrator_injection = event["narrator_injection"] if event else None
    return {"missed": [], "surprise": None, "narrator_injection": narrator_injection}
