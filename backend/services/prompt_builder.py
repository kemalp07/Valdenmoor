import json
from pathlib import Path
from typing import List, Optional

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_NARRATOR_CACHE: Optional[str] = None
_WORLD_CACHE: Optional[str] = None
_CHARACTERS_CACHE: Optional[list] = None


def _read_text_cached(path: Path, cache_attr: str) -> str:
    global _NARRATOR_CACHE, _WORLD_CACHE
    cached = globals().get(cache_attr)
    if cached is not None:
        return cached

    try:
        content = path.read_text(encoding="utf-8").strip()
    except Exception:
        content = ""

    if cache_attr == "_NARRATOR_CACHE":
        _NARRATOR_CACHE = content
    else:
        _WORLD_CACHE = content
    return content


def _load_narrator() -> str:
    return _read_text_cached(_DATA_DIR / "narrator.md", "_NARRATOR_CACHE")


def _load_world() -> str:
    return _read_text_cached(_DATA_DIR / "world.md", "_WORLD_CACHE")


def _load_characters() -> list:
    global _CHARACTERS_CACHE
    if _CHARACTERS_CACHE is not None:
        return _CHARACTERS_CACHE

    try:
        _CHARACTERS_CACHE = json.loads((_DATA_DIR / "characters.json").read_text(encoding="utf-8"))
    except Exception:
        _CHARACTERS_CACHE = []

    if not isinstance(_CHARACTERS_CACHE, list):
        _CHARACTERS_CACHE = []
    return _CHARACTERS_CACHE


def _format_characters(characters: list) -> str:
    if not characters:
        return ""

    category_labels = {
        "court": "SARAY",
        "army": "ORDU",
        "civilian": "HALK",
        "foreign": "YABANCI",
    }
    by_category: dict[str, list] = {}
    for char in characters:
        if not isinstance(char, dict):
            continue
        cat = char.get("category", "other")
        by_category.setdefault(cat, []).append(char)

    lines = ["## KARAKTERLER"]
    for category, chars in by_category.items():
        label = category_labels.get(category, category.upper())
        lines.append(f"\n### {label}")
        for char in chars:
            block = [f"**{char.get('name', '')}** — {char.get('title', '')}"]
            if char.get("age"):
                block.append(f"Yaş: {char['age']}")
            if char.get("description"):
                block.append(char["description"])
            for field, label_text in [
                ("intent", "Niyet"),
                ("agenda", "Ajanda"),
                ("secret_agenda", "Gizli ajanda"),
                ("trigger", "Tetikleyici"),
                ("relationships", "İlişkiler"),
            ]:
                if char.get(field):
                    block.append(f"{label_text}: {char[field]}")
            if char.get("romantic_option"):
                block.append(f"Romantik seçenek #{char['romantic_option']}")
            if char.get("portrait"):
                block.append(f"Portre: {char['portrait']}")
            lines.append("\n".join(block))
            lines.append("")

    return "\n".join(lines).strip()


def _format_memories(memories: List[str]) -> str:
    if not memories:
        return ""
    parts = ["## HAFIZA — ÖNCEKİ OLAYLAR:"]
    for i, memory in enumerate(memories):
        if str(memory).strip():
            parts.append(f"\n### Bölüm {i + 1}:\n{memory}")
    return "\n".join(parts)


def _format_game_stats(stats: Optional[dict]) -> str:
    if not stats:
        return ""
    return "\n".join([
        "## OYUN DURUMU:",
        f"- Hazine (treasury): {stats.get('treasury', 450)}",
        f"- Ordu morali (army_morale): {stats.get('army_morale', 40)}",
        f"- Halk desteği (public_support): {stats.get('public_support', 45)}",
        f"- Prestij (prestige): {stats.get('prestige', 30)}",
        f"- Dravkor tehdidi (dravkor_threat): {stats.get('dravkor_threat', 60)}",
    ])


def _format_character_relations(relations: Optional[list]) -> str:
    if not relations:
        return ""

    lines = ["## KARAKTER SADAKAT DURUMU — ZORUNLU UYGULA"]
    for rel in relations:
        if not isinstance(rel, dict):
            continue
        char_id = rel.get("character_id", "unknown")
        loyalty = rel.get("loyalty", 50)

        if loyalty >= 80:
            behavior = "koşulsuz sadık. Her emri yerine getirir, tehlikeye atlar, sırları korur."
        elif loyalty >= 65:
            behavior = "güveniyor. Yardımcı olur ama kendi çıkarını da gözetir."
        elif loyalty >= 51:
            behavior = "olumlu ama temkinli. Makul istekleri kabul eder, şüpheyle izler."
        elif loyalty == 50:
            continue  # başlangıç değeri, henüz etkileşim yok
        elif loyalty >= 35:
            behavior = "soğuk ve mesafeli. Emirlere yavaş uyar, bilgi saklar, fırsatı kollar."
        elif loyalty >= 20:
            behavior = "açıkça karşı. Direnir, rakiplerle ittifak arayışında."
        else:
            behavior = "düşman. İhanet planlar, her fırsatta baltalamaya çalışır."

        lines.append(f"- {char_id} (sadakat {loyalty}): {behavior}")

    if len(lines) == 1:
        return ""

    return (
        "\n".join(lines)
        + "\n\n**KRİTİK:** Bu sadakat seviyeleri karakterlerin davranışını belirler. "
        "Düşük sadakatli karakterler oyuncuya eyvallah demez — direnir, geciktirir, "
        "bilgi saklar veya reddeder. Yüksek sadakat bile karakterin kendi ajandası "
        "olduğunu değiştirmez. Hiçbir karakter aptal değildir."
    )


def _format_character_profile(user_name: str, character_profile: dict) -> str:
    lines = [
        "## OYUNCU KARAKTERİ:",
        f"- İsim: {user_name}",
        f"- Cinsiyet: {character_profile.get('gender', '')}",
        f"- Yönetim tarzı: {character_profile.get('rulingStyle', '')}",
        f"- Boy: {character_profile.get('height', '')}",
        f"- Saç rengi: {character_profile.get('hairColor', '')}",
        f"- Kişilik: {', '.join(character_profile.get('traits', []))}",
        f"- Köken: {character_profile.get('origin', '')}",
        f"- Korkusu: {character_profile.get('fear', '')}",
        f"- Hobisi: {character_profile.get('hobby', '')}",
        f"- Gizli özellik: {character_profile.get('secretTrait', '')}",
    ]
    return "\n".join(lines)


async def build_prompt(
    user_name: str,
    messages: List[dict],
    memories: List[str],
    game_stats: Optional[dict] = None,
    character_relations: Optional[list] = None,
    character_profile: Optional[dict] = None,
    language: str = "tr",
) -> list:
    """Builds the system prompt from narrator.md, world.md, characters.json, and live game state."""
    player = user_name or "Oyuncu"
    narrator = _load_narrator().replace("{{user}}", player)
    world = _load_world().replace("{{user}}", player)
    characters = _format_characters(_load_characters())

    system_parts = [
        narrator,
        world,
        characters,
        _format_character_profile(player, character_profile) if character_profile else "",
        _format_memories(memories),
        _format_game_stats(game_stats),
        _format_character_relations(character_relations),
    ]

    system_content = "\n\n".join(part for part in system_parts if part)

    if language == "en":
        system_content += (
            "\n\n## LANGUAGE\n"
            "You MUST respond entirely in English. "
            "All narration, dialogue, and character speech must be in English."
        )
    else:
        system_content += (
            "\n\n## DİL\n"
            "Tüm yanıtlarını Türkçe yaz. "
            "Anlatı, diyalog ve karakter konuşmalarının tamamı Türkçe olacak."
        )

    out = [{"role": "system", "content": system_content}]
    out.extend(messages or [])
    return out
