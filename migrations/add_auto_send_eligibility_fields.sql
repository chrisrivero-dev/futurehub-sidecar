-- migrations/add_auto_send_eligibility_fields.sql

-- Add auto-send eligibility tracking to tickets
ALTER TABLE tickets ADD COLUMN auto_send_eligible BOOLEAN DEFAULT 0 NOT NULL;
ALTER TABLE tickets ADD COLUMN auto_send_reason TEXT;
ALTER TABLE tickets ADD COLUMN auto_send_evaluated_at TIMESTAMP;

-- Index for querying eligible tickets
CREATE INDEX idx_tickets_auto_send_eligible ON tickets(auto_send_eligible);

-- Migration metadata
INSERT INTO schema_migrations (version) VALUES ('20250115_add_auto_send_eligibility');