-- Migration 014: dravkor_threat → 4 devlet ilişki sistemi (idempotent)

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'game_stats' AND column_name = 'dravkor_threat'
  ) THEN
    ALTER TABLE game_stats RENAME COLUMN dravkor_threat TO rel_dravkor;
  END IF;
END $$;

ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS rel_dravkor INTEGER DEFAULT 65;
ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS rel_selmara INTEGER DEFAULT 25;
ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS rel_varethis INTEGER DEFAULT 30;
ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS rel_kadir INTEGER DEFAULT 20;

COMMENT ON COLUMN game_stats.rel_dravkor IS 'Dravkor Dükalığı gerilim seviyesi (0=barış, 100=savaş)';
COMMENT ON COLUMN game_stats.rel_selmara IS 'Selmara Krallığı gerilim seviyesi (0=müttefik, 100=düşman)';
COMMENT ON COLUMN game_stats.rel_varethis IS 'Varethis liman şehri gerilim seviyesi';
COMMENT ON COLUMN game_stats.rel_kadir IS 'Kadir Sultanlığı gerilim seviyesi';
