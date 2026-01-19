-- LTM Database Schema
-- SQLite database for persistent memory storage

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    definition_path TEXT,
    signing_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memories table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    region TEXT NOT NULL CHECK (region IN ('AGENT', 'PROJECT')),
    project_id TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('EMOTIONAL', 'ARCHITECTURAL', 'LEARNINGS', 'ACHIEVEMENTS')),
    content TEXT NOT NULL,
    original_content TEXT NOT NULL,
    impact TEXT NOT NULL CHECK (impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP NOT NULL,
    last_accessed TIMESTAMP NOT NULL,
    previous_memory_id TEXT,
    version INTEGER DEFAULT 1,
    superseded_by TEXT,
    signature TEXT,
    token_count INTEGER,

    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (previous_memory_id) REFERENCES memories(id),
    FOREIGN KEY (superseded_by) REFERENCES memories(id),
    CHECK (region = 'AGENT' OR project_id IS NOT NULL)
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_memories_agent_region ON memories(agent_id, region);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_impact ON memories(impact);
CREATE INDEX IF NOT EXISTS idx_memories_superseded ON memories(superseded_by);
