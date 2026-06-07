"""
Valdenmoor veritabanını sıfırla — Hogwarts tablolarını sil, temiz şema kur.

DİKKAT: Tüm oyun verisi (mesajlar, oturumlar, hafıza) silinir.

Kullanım:
  python backend/scripts/reset_db.py
  python backend/scripts/reset_db.py --yes   # onay sormadan
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESET_SQL = ROOT / "database" / "reset_valdenmoor_db.sql"
SCHEMA_SQL = ROOT / "database" / "schema.sql"
MIGRATIONS_DIR = ROOT / "database" / "migrations"

# Mevcut incremental migration dosyaları — reset sonrası applied olarak işaretlenir
TRACKED_MIGRATIONS = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))


def _connect():
    scripts_dir = Path(__file__).resolve().parent
    backend_dir = scripts_dir.parent
    for p in (str(backend_dir), str(scripts_dir)):
        if p not in sys.path:
            sys.path.insert(0, p)
    from run_migrations import _connect as connect

    return connect()


def _run_sql(cur, sql: str, label: str) -> None:
    print(f">> {label}")
    cur.execute(sql)


def _seed_migrations(cur) -> None:
    for filename in TRACKED_MIGRATIONS:
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
            (filename,),
        )
    print(f"  {len(TRACKED_MIGRATIONS)} migration kaydı eklendi.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset Supabase DB to clean Valdenmoor schema")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.yes:
        print("UYARI: Tüm oyun verisi silinecek (mesajlar, oturumlar, hafıza, ilişkiler).")
        answer = input("Devam etmek için 'evet' yaz: ").strip().lower()
        if answer not in ("evet", "yes", "y"):
            print("İptal edildi.")
            return 1

    drop_sql = RESET_SQL.read_text(encoding="utf-8")
    schema_sql = SCHEMA_SQL.read_text(encoding="utf-8")

    conn = _connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            _run_sql(cur, drop_sql, "Eski tablolar siliniyor")
            print("  OK drop")
            _run_sql(cur, schema_sql, "Temiz şema kuruluyor")
            print("  OK schema")
            _seed_migrations(cur)
        print("Veritabanı sıfırlandı — Valdenmoor şeması hazır.")
        return 0
    except Exception as exc:
        print(f"HATA: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
