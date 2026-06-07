ALTER TABLE character_relations
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS status_updated_at TIMESTAMP DEFAULT NOW();

COMMENT ON COLUMN character_relations.status IS
'Karakterin mevcut durumu — sözel, Gemini tarafından güncellenir';
