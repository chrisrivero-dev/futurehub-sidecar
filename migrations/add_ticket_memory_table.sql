CREATE TABLE IF NOT EXISTS ticket_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticket_id TEXT NOT NULL,
    ticket_subject TEXT,
    customer_name TEXT,

    intent_primary TEXT,
    risk_level TEXT,
    draft_outcome TEXT,
    recommended_action TEXT,

    summary_short TEXT,
    summary_detailed TEXT,

    auto_send_eligible BOOLEAN DEFAULT 0,
    auto_send_used BOOLEAN DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ticket_memory_ticket_id
ON ticket_memory(ticket_id);

CREATE INDEX IF NOT EXISTS idx_ticket_memory_created_at
ON ticket_memory(created_at);
