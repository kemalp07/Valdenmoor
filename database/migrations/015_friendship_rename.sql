-- Migration 015: rel_* → friendship_* (0=düşman, 100=müttefik) — idempotent

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'game_stats' AND column_name = 'rel_dravkor'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'game_stats' AND column_name = 'friendship_dravkor'
  ) THEN
    ALTER TABLE game_stats RENAME COLUMN rel_dravkor TO friendship_dravkor;
    ALTER TABLE game_stats RENAME COLUMN rel_selmara TO friendship_selmara;
    ALTER TABLE game_stats RENAME COLUMN rel_varethis TO friendship_varethis;
    ALTER TABLE game_stats RENAME COLUMN rel_kadir TO friendship_kadir;

    UPDATE game_stats SET
      friendship_dravkor = 100 - friendship_dravkor,
      friendship_selmara = 100 - friendship_selmara,
      friendship_varethis = 100 - friendship_varethis,
      friendship_kadir = 100 - friendship_kadir;
  END IF;
END $$;

ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS friendship_dravkor INTEGER DEFAULT 35;
ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS friendship_selmara INTEGER DEFAULT 75;
ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS friendship_varethis INTEGER DEFAULT 70;
ALTER TABLE game_stats ADD COLUMN IF NOT EXISTS friendship_kadir INTEGER DEFAULT 80;

COMMENT ON COLUMN game_stats.friendship_dravkor IS 'Dravkor dostluğu (0=düşman, 100=müttefik)';
COMMENT ON COLUMN game_stats.friendship_selmara IS 'Selmara dostluğu (0=düşman, 100=müttefik)';
COMMENT ON COLUMN game_stats.friendship_varethis IS 'Varethis dostluğu (0=düşman, 100=müttefik)';
COMMENT ON COLUMN game_stats.friendship_kadir IS 'Kadir dostluğu (0=düşman, 100=müttefik)';
