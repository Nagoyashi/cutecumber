-- cutecumber.cc schema (v0).
-- Idempotent: safe to run via `flask --app wsgi init-db` on an existing DB.
--
-- links exists from day one even though link CRUD ships in a later session:
-- the table costs nothing empty and saves a migration mid-v0 (DECISIONS.md #6).

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    username      TEXT    UNIQUE,                    -- NULL until claimed; lowercase only
    display_name  TEXT,
    bio           TEXT,
    pronouns      TEXT,
    avatar_kind   TEXT    NOT NULL DEFAULT 'emoji',  -- 'emoji' | 'gradient' (uploads: later, maybe)
    avatar_value  TEXT    NOT NULL DEFAULT '🥒',     -- emoji char OR gradient name; allowlists in constants.py
    theme_json    TEXT    NOT NULL,                  -- versioned JSON, see app/theme.py
    theme_version INTEGER NOT NULL DEFAULT 1,
    reset_token_hash TEXT,                            -- sha256 of the emailed token; NULL when none active
    reset_expires INTEGER,                            -- unix epoch; token dead after this
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS links (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title    TEXT    NOT NULL,
    url      TEXT    NOT NULL,                       -- http(s) only, validated at save AND render
    emoji    TEXT,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_links_user_position ON links (user_id, position);
