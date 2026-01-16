-- migrations/add_ai_assistant_fields.sql

-- Add AI Assistant feature flag to tickets
ALTER TABLE tickets ADD COLUMN ai_assistant_enabled BOOLEAN DEFAULT 0 NOT NULL;

-- Add AI state tracking
ALTER TABLE tickets ADD COLUMN ai_conversation_id TEXT;
ALTER TABLE tickets ADD COLUMN ai_last_activity TIMESTAMP;

-- Add sidecar integration tracking
ALTER TABLE tickets ADD COLUMN sidecar_status TEXT CHECK(sidecar_status IN ('idle', 'processing', 'completed', 'failed', 'timeout'));
ALTER TABLE tickets ADD COLUMN sidecar_last_request TIMESTAMP;
ALTER TABLE tickets ADD COLUMN sidecar_error TEXT;

-- Index for performance
CREATE INDEX idx_tickets_ai_enabled ON tickets(ai_assistant_enabled);
CREATE INDEX idx_tickets_sidecar_status ON tickets(sidecar_status);

-- Migration metadata
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version) VALUES ('20250115_add_ai_assistant_fields');