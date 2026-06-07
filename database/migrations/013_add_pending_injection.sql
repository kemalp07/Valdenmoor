-- Migration 013: game_state tablosuna pending_injection kolonu ekle
-- Ekonomik olayların bir sonraki mesajda enjekte edilmesi için kullanılır

ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS pending_injection TEXT DEFAULT NULL;

COMMENT ON COLUMN game_state.pending_injection IS
'Narrator ekonomik olay enjeksiyonu — bir sonraki chat mesajında kullanılır ve temizlenir';
