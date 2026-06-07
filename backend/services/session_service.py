import logging

from db.supabase_client import supabase
from services.stats_service import DEFAULT_GAME_STATS

logger = logging.getLogger(__name__)

NPC_CHARACTER_IDS = [
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


def get_initial_loyalty(character_id: str, origin: str, ruling_style: str) -> int:
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


def normalize_gender(gender: str) -> str:
    return gender if gender in ("king", "queen") else "king"


def normalize_ruling_style(style: str) -> str:
    return style if style in ("harsh", "diplomatic", "cunning") else "diplomatic"


def normalize_origin(origin: str) -> str:
    return origin if origin in ("warrior", "merchant", "noble") else "noble"


def stats_for_origin(origin: str) -> dict:
    stats = dict(DEFAULT_GAME_STATS)
    if origin == "warrior":
        stats["army_morale"] = 55
        stats["treasury"] = 400
    elif origin == "merchant":
        stats["treasury"] = 550
        stats["army_morale"] = 35
    elif origin == "noble":
        stats["prestige"] = 45
    return stats


def ensure_game_session(
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
                "gender": normalize_gender(gender),
                "ruling_style": normalize_ruling_style(ruling_style),
                "origin": normalize_origin(origin),
            },
            on_conflict="id",
        ).execute()
    except Exception as e:
        logger.error(f"ensure_game_session error: {e}")


def init_game_for_new_session(session_id: str, origin: str, ruling_style: str = "diplomatic") -> None:
    if not supabase:
        return
    origin = normalize_origin(origin)
    ruling_style = normalize_ruling_style(ruling_style)
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
                {"session_id": session_id, **stats_for_origin(origin)}
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
                    "loyalty": get_initial_loyalty(character_id, origin, ruling_style),
                }
                for character_id in NPC_CHARACTER_IDS
            ]
            supabase.table("character_relations").insert(rows).execute()
    except Exception as e:
        logger.error(f"init_game_for_new_session error: {e}")
