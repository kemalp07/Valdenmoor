-- Valdenmoor DB reset — tüm eski/Hogwarts tablolarını sil, temiz şema kur
-- DİKKAT: Tüm oyun verisi silinir.

-- Hogwarts / deprecated
DROP TABLE IF EXISTS missed_class_log CASCADE;
DROP TABLE IF EXISTS house_point_events CASCADE;
DROP TABLE IF EXISTS house_points CASCADE;
DROP TABLE IF EXISTS character_relationships CASCADE;

-- Valdenmoor (yeniden oluşturulacak)
DROP TABLE IF EXISTS user_memories CASCADE;
DROP TABLE IF EXISTS character_relations CASCADE;
DROP TABLE IF EXISTS game_stats CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS game_state CASCADE;
DROP TABLE IF EXISTS game_sessions CASCADE;
DROP TABLE IF EXISTS characters CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS lore_chunks CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;

-- Eski kolon kalıntıları için tablolar zaten drop edildi; schema.sql ile yeniden kurulur
