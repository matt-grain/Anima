-- Subconscious Database Schema
-- FTS5 full-text search for raw dialogue indexing

-- Sessions table (metadata)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,           -- 'claude', 'antigravity', 'opencode', 'gemini'
    project TEXT,                   -- Project path (can be null for agent-wide)
    file_path TEXT NOT NULL,        -- Path to source JSONL
    timestamp INTEGER,              -- Earliest message timestamp (ms)
    mtime REAL NOT NULL,            -- File modification time for incremental indexing
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS messages USING fts5(
    session_id UNINDEXED,           -- Don't index session_id, just store it
    role,                           -- 'user' or 'assistant'
    text,                           -- The actual message content
    tokenize='porter unicode61'     -- Porter stemming + unicode support
);

-- Index for recency filtering
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
