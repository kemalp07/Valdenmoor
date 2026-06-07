-- Valdenmoor — temiz veritabanı şeması
-- Hogwarts kalıntıları yok. Sadece aktif kullanılan tablolar.

CREATE EXTENSION IF NOT EXISTS vector;

-- Kullanıcılar (hafıza sistemi session → user eşlemesi için)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'premium')),
  patreon_id TEXT,
  daily_message_count INTEGER DEFAULT 0,
  daily_reset_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Karakterler (oyuncu karakteri + NPC kayıtları)
CREATE TABLE characters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT,
  name TEXT NOT NULL,
  house TEXT,
  gender TEXT,
  traits TEXT[],
  origin TEXT,
  height TEXT,
  hair_color TEXT,
  fear TEXT,
  hobby TEXT,
  secret_trait TEXT,
  attraction TEXT,
  personality TEXT,
  speech_style TEXT NOT NULL DEFAULT 'neutral',
  likes TEXT,
  dislikes TEXT,
  base_prompt TEXT NOT NULL DEFAULT 'npc',
  image_url TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Mekanlar (lore / arka plan)
CREATE TABLE locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  background_url TEXT,
  lore_context TEXT,
  characters_present UUID[]
);

-- Kullanıcı hafızası
CREATE TABLE user_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  summary TEXT NOT NULL,
  summary_type TEXT DEFAULT 'episodic' CHECK (summary_type IN ('episodic', 'rolling')),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_memories_user_id ON user_memories(user_id);
CREATE INDEX idx_user_memories_user_type ON user_memories(user_id, summary_type);

-- Oyun oturumları
CREATE TABLE game_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_name TEXT,
  gender TEXT DEFAULT 'king' CHECK (gender IN ('king', 'queen')),
  ruling_style TEXT DEFAULT 'diplomatic' CHECK (ruling_style IN ('harsh', 'diplomatic', 'cunning')),
  origin TEXT DEFAULT 'noble' CHECK (origin IN ('warrior', 'merchant', 'noble')),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Oyun istatistikleri (action sistemi)
CREATE TABLE game_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  treasury INTEGER DEFAULT 450,
  army_morale INTEGER DEFAULT 40,
  public_support INTEGER DEFAULT 45,
  prestige INTEGER DEFAULT 30,
  friendship_dravkor INTEGER DEFAULT 35,
  friendship_selmara INTEGER DEFAULT 75,
  friendship_varethis INTEGER DEFAULT 70,
  friendship_kadir INTEGER DEFAULT 80,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(session_id)
);

CREATE INDEX idx_game_stats_session_id ON game_stats(session_id);

-- Karakter ilişkileri (sözel durum sistemi)
CREATE TABLE character_relations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  character_id TEXT NOT NULL,
  loyalty INTEGER DEFAULT 50,
  status TEXT DEFAULT NULL,
  status_updated_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(session_id, character_id)
);

CREATE INDEX idx_character_relations_session_id ON character_relations(session_id);

-- Mesaj geçmişi
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_session_id ON messages(session_id);

-- Oyun durumu (pending injection / action butonları)
CREATE TABLE game_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL UNIQUE,
  pending_injection TEXT DEFAULT NULL,
  pending_buttons TEXT DEFAULT NULL,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Lore parçaları (RAG)
CREATE TABLE lore_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  category TEXT,
  tags TEXT[]
);

-- Migration takibi
CREATE TABLE schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE character_relations IS 'Karakter ilişkileri — status sözel durum metni, loyalty legacy';
COMMENT ON COLUMN character_relations.status IS 'Karakterin mevcut durumu — Gemini tarafından güncellenir';
COMMENT ON COLUMN game_state.pending_injection IS 'Narrator olay enjeksiyonu — bir sonraki mesajda okunur';
COMMENT ON COLUMN game_state.pending_buttons IS 'Önerilen aksiyon butonları JSON — bir sonraki mesajda okunur';
