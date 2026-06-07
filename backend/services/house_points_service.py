"""Game state service — Valdenmoor session time/location stubs."""

_DEFAULT_GAME_STATE = {
    "current_week": 1,
    "current_day": 1,
    "current_hour": 8,
    "daily_message_count": 0,
    "last_activity_at": None,
    "current_location": "throne_room",
}


def get_house_points(session_id: str) -> dict:
    """Deprecated Hogwarts API — returns empty dict for backward compatibility."""
    return {}


def get_points_floor_info(session_id: str) -> dict:
    return {"minimum_floor": 0, "points_floor_started_at": None}


def get_game_state(session_id: str) -> dict:
    return dict(_DEFAULT_GAME_STATE)


def check_inactivity_advance(session_id: str, threshold_minutes: int = 30) -> bool:
    return False


def build_narrator_day_message(session_id: str) -> str:
    return ""


def advance_day(session_id: str) -> dict:
    return get_game_state(session_id)


def advance_hour(session_id: str, hours: int = 1) -> dict:
    return get_game_state(session_id)


def increment_message_count(session_id: str) -> int:
    return 0


def check_sleep_trigger(message: str) -> bool:
    return False


def get_message_count(session_id: str) -> int:
    return 0


def build_current_time_context(session_id: str, language: str = "tr") -> str:
    return ""


def get_todays_schedule(week: int, day: int) -> list:
    return []


def get_missed_classes_for_prompt(session_id: str) -> list:
    return []


def build_missed_class_context(missed: list, language: str = "tr") -> str:
    return ""


def get_location(session_id: str) -> str:
    return "throne_room"


def get_day_name(day: int, language: str = "tr") -> str:
    return "Day" if language == "en" else "Gün"


def localize_subject(subject: str, language: str = "tr") -> str:
    return subject
