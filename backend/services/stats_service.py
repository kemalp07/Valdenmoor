import logging

from db.supabase_client import supabase

logger = logging.getLogger(__name__)

DEFAULT_GAME_STATS = {
    "treasury": 450,
    "army_morale": 40,
    "public_support": 45,
    "prestige": 30,
    "friendship_dravkor": 35,
    "friendship_selmara": 75,
    "friendship_varethis": 70,
    "friendship_kadir": 80,
}

STAT_KEYS = tuple(DEFAULT_GAME_STATS.keys())

STAT_MAX = {
    "treasury": 1000,
    "army_morale": 100,
    "public_support": 100,
    "prestige": 100,
    "friendship_dravkor": 100,
    "friendship_selmara": 100,
    "friendship_varethis": 100,
    "friendship_kadir": 100,
}

STAT_SELECT = (
    "treasury,army_morale,public_support,prestige,"
    "friendship_dravkor,friendship_selmara,friendship_varethis,friendship_kadir"
)


def ensure_game_stats(session_id: str) -> dict:
    if not supabase:
        return dict(DEFAULT_GAME_STATS)

    try:
        resp = (
            supabase.table("game_stats")
            .select(STAT_SELECT)
            .eq("session_id", session_id)
            .execute()
        )
        if resp.data:
            return resp.data[0]

        supabase.table("game_stats").insert(
            {"session_id": session_id, **DEFAULT_GAME_STATS}
        ).execute()
        return dict(DEFAULT_GAME_STATS)
    except Exception as e:
        logger.error(f"ensure_game_stats error: {e}")
        return dict(DEFAULT_GAME_STATS)


def apply_stats_delta(session_id: str, stats_delta: dict) -> dict:
    current = ensure_game_stats(session_id)
    updated = dict(current)

    for key in STAT_KEYS:
        if key not in stats_delta:
            continue
        try:
            delta = int(stats_delta[key])
        except (TypeError, ValueError):
            continue
        cap = STAT_MAX.get(key, 100)
        updated[key] = max(0, min(cap, int(updated.get(key, 0)) + delta))

    if supabase:
        try:
            supabase.table("game_stats").upsert(
                {
                    "session_id": session_id,
                    **{key: updated[key] for key in STAT_KEYS},
                },
                on_conflict="session_id",
            ).execute()
        except Exception as e:
            logger.error(f"apply_stats_delta error: {e}")

    return updated
