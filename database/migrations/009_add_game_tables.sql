-- Yeni oyun sistemi tabloları

CREATE TABLE IF NOT EXISTS game_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_name TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS game_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  treasury INTEGER DEFAULT 450,
  army_morale INTEGER DEFAULT 40,
  public_support INTEGER DEFAULT 45,
  prestige INTEGER DEFAULT 30,
  dravkor_threat INTEGER DEFAULT 60,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(session_id)
);

-- Eski user_id tabanlı character_relations varsa kaldır
DROP TABLE IF EXISTS character_relations;

CREATE TABLE character_relations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  character_id TEXT NOT NULL,
  loyalty INTEGER DEFAULT 50,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(session_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_game_stats_session_id ON game_stats(session_id);
CREATE INDEX IF NOT EXISTS idx_character_relations_session_id ON character_relations(session_id);
