"""World simulation — cleared for new game system."""


async def run_point_simulation(
    session_id: str,
    conversation: list,
    player_house: str,
    week: int = 1,
    day: int = 1,
) -> dict:
    return {"missed": [], "surprise": None}


async def extract_time_from_response(session_id: str, ai_response: str):
    pass


async def extract_inventory_and_location(session_id: str, ai_response: str):
    pass


def start_organic_scheduler():
    pass
