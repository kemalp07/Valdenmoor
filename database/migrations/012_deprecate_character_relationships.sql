-- Migration 012: character_relationships tablosunu deprecated olarak işaretle
-- Bu tablo Hogwarts döneminden kalma, Valdenmoor'da kullanılmıyor.
-- Önce boş olduğunu doğrula: SELECT COUNT(*) FROM character_relationships;
-- Sonra: DROP TABLE IF EXISTS character_relationships;
COMMENT ON TABLE character_relationships IS 'DEPRECATED - use character_relations instead';
