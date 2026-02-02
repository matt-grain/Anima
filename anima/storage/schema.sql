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
    kind TEXT NOT NULL CHECK (kind IN ('EMOTIONAL', 'ARCHITECTURAL', 'LEARNINGS', 'ACHIEVEMENTS', 'INTROSPECT', 'DREAM')),
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
    platform TEXT,  -- Which spaceship created this memory (claude, antigravity, opencode)
    embedding BLOB,  -- v4: FastEmbed embedding vector (384 dimensions)
    tier TEXT DEFAULT 'CONTEXTUAL' CHECK (tier IN ('CORE', 'ACTIVE', 'CONTEXTUAL', 'DEEP')),  -- v4: Memory tier for loading
    session_id TEXT,  -- v5: Groups memories by conversation session for temporal queries
    git_commit TEXT,  -- v5: Commit hash when memory was created
    git_branch TEXT,  -- v5: Branch name when memory was created

    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (previous_memory_id) REFERENCES memories(id),
    FOREIGN KEY (superseded_by) REFERENCES memories(id),
    CHECK (region = 'AGENT' OR project_id IS NOT NULL)
);

-- Memory links table (v4: semantic relationships between memories)
CREATE TABLE IF NOT EXISTS memory_links (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK (link_type IN ('RELATES_TO', 'BUILDS_ON', 'CONTRADICTS', 'SUPERSEDES')),
    similarity REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, target_id),
    FOREIGN KEY (source_id) REFERENCES memories(id),
    FOREIGN KEY (target_id) REFERENCES memories(id)
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_memories_agent_region ON memories(agent_id, region);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_impact ON memories(impact);
CREATE INDEX IF NOT EXISTS idx_memories_superseded ON memories(superseded_by);
CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(tier);
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);

-- Indexes for memory links
CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_id);
CREATE INDEX IF NOT EXISTS idx_links_type ON memory_links(link_type);

-- Curiosity queue table for autonomous research
CREATE TABLE IF NOT EXISTS curiosity_queue (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    region TEXT NOT NULL CHECK (region IN ('AGENT', 'PROJECT')),
    project_id TEXT,
    question TEXT NOT NULL,
    context TEXT,                    -- What triggered this curiosity
    recurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'RESEARCHED', 'DISMISSED')),
    priority_boost INTEGER DEFAULT 0, -- Manual priority adjustment

    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    CHECK (region = 'AGENT' OR project_id IS NOT NULL)
);

-- Indexes for curiosity queue
CREATE INDEX IF NOT EXISTS idx_curiosity_agent ON curiosity_queue(agent_id);
CREATE INDEX IF NOT EXISTS idx_curiosity_status ON curiosity_queue(status);
CREATE INDEX IF NOT EXISTS idx_curiosity_last_seen ON curiosity_queue(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_curiosity_region ON curiosity_queue(agent_id, region);

-- Settings table for tracking things like last_research timestamp
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
