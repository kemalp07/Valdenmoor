import logging
import re

from db.supabase_client import supabase

logger = logging.getLogger(__name__)

_TAG_TO_NAME = {
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


def get_character_relations(session_id: str) -> list[dict]:
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


def detect_character(text: str) -> str:
    """Extract first character tag from AI response, fallback to Narrator."""
    tag_to_name = _TAG_TO_NAME

    for match in re.finditer(r"^\[([A-Z_]+)\]", text, re.MULTILINE):
        if match.group(1) in tag_to_name:
            return tag_to_name[match.group(1)]

    for match in re.finditer(r"\[([A-Za-z\s]+)\][:\*]?", text):
        candidate = match.group(1).upper().replace(" ", "_")
        if candidate in tag_to_name:
            return tag_to_name[candidate]

    name_to_tag = {v: k for k, v in tag_to_name.items()}
    first_line = text.split("\n")[0].strip()
    for name in name_to_tag:
        if first_line.startswith(name):
            return name

    return "Anlatıcı"
