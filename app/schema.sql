-- cutecumber.cc schema (v0).
-- Idempotent: safe to run via `flask --app wsgi init-db` on an existing DB.
--
-- links exists from day one even though link CRUD ships in a later session:
-- the table costs nothing empty and saves a migration mid-v0 (DECISIONS.md #5).

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    username      TEXT    UNIQUE,                    -- NULL until claimed; lowercase only
    display_name  TEXT,
    bio           TEXT,
    pronouns      TEXT,
    avatar_kind   TEXT    NOT NULL DEFAULT 'set',     -- 'set' | 'image' | 'gradient' | 'emoji' (last two: legacy, render-only)
    avatar_value  TEXT    NOT NULL DEFAULT 'sprout',  -- set slug | uploaded filename | gradient name | emoji char; validated in constants.py (signup sets the default explicitly)
    theme_json    TEXT    NOT NULL,                  -- versioned JSON, see app/theme.py
    theme_version INTEGER NOT NULL DEFAULT 1,
    reset_token_hash TEXT,                            -- sha256 of the emailed token; NULL when none active
    reset_expires INTEGER,                            -- unix epoch; token dead after this
    -- Page builder (STAGING, behind BUILDER_ENABLED). Both NULL for every
    -- existing user => the legacy links page renders untouched. draft = editor
    -- working copy; live = what the public page renders when non-NULL. plan
    -- gates premium sections/themes (DECISIONS.md — builder cycle).
    sections_draft_json TEXT,                         -- versioned JSON, see app/sections.py; NULL until first builder save
    sections_live_json  TEXT,                         -- published copy; NULL => render legacy links path
    plan          TEXT    NOT NULL DEFAULT 'free',    -- 'free' | 'sprout'
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

-- Multi-page sites (Phase B). The HOME page stays in users.sections_*_json (no
-- live-data migration); this table holds a creator's SUBPAGES only, each a
-- titled, slugged container of the same section model (app/sections.py). URL is
-- /<username>/<slug>. Additive: a DB with no pages renders exactly as before.
CREATE TABLE IF NOT EXISTS pages (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slug     TEXT    NOT NULL,                       -- URL segment, validated in constants.py
    title    TEXT    NOT NULL,                       -- nav label
    sections_draft_json TEXT,                        -- editor working copy; NULL until first save
    sections_live_json  TEXT,                        -- published copy; NULL => not shown to visitors
    position INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_pages_user_position ON pages (user_id, position);

-- Freed usernames rest for TOMBSTONE_DAYS before anyone can re-claim them
-- (DECISIONS.md #29). Rows are purged opportunistically during claims.
CREATE TABLE IF NOT EXISTS username_tombstones (
    username TEXT PRIMARY KEY,
    freed_at INTEGER NOT NULL
) STRICT;
