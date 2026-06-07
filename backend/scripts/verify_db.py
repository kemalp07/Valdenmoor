import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_migrations import _connect

conn = _connect()
cur = conn.cursor()
cur.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name"
)
print("Tables:", [r[0] for r in cur.fetchall()])
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = 'game_stats' ORDER BY ordinal_position"
)
print("game_stats:", [r[0] for r in cur.fetchall()])
conn.close()
