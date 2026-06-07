"""
Supabase migration runner — doğrudan PostgreSQL bağlantısı gerektirir.

.env dosyasına ekle:
  SUPABASE_DB_PASSWORD=<Dashboard → Settings → Database → Database password>

Kullanım:
  python backend/scripts/run_migrations.py
  python backend/scripts/run_migrations.py --only 013
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "database" / "migrations"


def _project_ref(supabase_url: str) -> str:
    match = re.search(r"https://([^.]+)\.supabase\.co", supabase_url)
    if not match:
        raise ValueError(f"Geçersiz SUPABASE_URL: {supabase_url}")
    return match.group(1)


def _connect():
    load_dotenv(ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "").strip()
    password = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    if not url:
        raise SystemExit("SUPABASE_URL .env dosyasında tanımlı değil.")
    if not password:
        raise SystemExit(
            "SUPABASE_DB_PASSWORD .env dosyasında tanımlı değil.\n"
            "Supabase Dashboard → Project Settings → Database → Database password"
        )

    ref = _project_ref(url)
    host = os.getenv("SUPABASE_DB_HOST", "").strip()
    port = int(os.getenv("SUPABASE_DB_PORT", "6543"))
    user = os.getenv("SUPABASE_DB_USER", f"postgres.{ref}").strip()

    if not host:
        regions = [
            "ap-southeast-1",
            "eu-central-1",
            "eu-west-1",
            "eu-west-2",
            "us-east-1",
            "us-west-1",
        ]
        last_err: Exception | None = None
        for aws in ("aws-1", "aws-0"):
            for region in regions:
                candidate = f"{aws}-{region}.pooler.supabase.com"
                try:
                    conn = psycopg2.connect(
                        host=candidate,
                        port=port,
                        dbname="postgres",
                        user=user,
                        password=password,
                        sslmode="require",
                        connect_timeout=8,
                    )
                    return conn
                except Exception as exc:
                    last_err = exc
        raise SystemExit(f"Supabase Postgres bağlantısı kurulamadı: {last_err}")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname="postgres",
        user=user,
        password=password,
        sslmode="require",
    )


def _migration_files(only: str | None) -> list[Path]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if only:
        files = [f for f in files if only in f.stem]
    return files


def _ensure_migrations_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)


def _is_applied(cur, filename: str) -> bool:
    cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
    return cur.fetchone() is not None


def _mark_applied(cur, filename: str) -> None:
    cur.execute(
        "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
        (filename,),
    )


def _run_file(cur, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    print(f">> {path.name}")
    cur.execute(sql)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SQL migrations against Supabase Postgres")
    parser.add_argument("--only", help="Run migrations matching this id (e.g. 013)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if already recorded in schema_migrations",
    )
    args = parser.parse_args()

    files = _migration_files(args.only)
    if not files:
        print("Çalıştırılacak migration bulunamadı.")
        return 1

    conn = _connect()
    failed = 0
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            _ensure_migrations_table(cur)
            for path in files:
                if not args.force and _is_applied(cur, path.name):
                    print(f"  SKIP {path.name}")
                    continue
                try:
                    _run_file(cur, path)
                    _mark_applied(cur, path.name)
                    print(f"  OK {path.name}")
                except Exception as exc:
                    failed += 1
                    print(f"  FAIL {path.name}: {exc}")
        if failed:
            print(f"Migration tamamlandı — {failed} hata.")
            return 1
        print("Migration tamamlandı.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
