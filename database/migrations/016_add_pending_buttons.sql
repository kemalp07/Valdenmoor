ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS pending_buttons TEXT DEFAULT NULL;

COMMENT ON COLUMN game_state.pending_buttons IS
'Suggested action buttons JSON — frontend bir sonraki mesajda okur';
