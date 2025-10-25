-- Migration: Add email_logs table
-- Date: 2025-10-23

CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_type VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject TEXT,
    status VARCHAR(20) NOT NULL CHECK(status IN ('success', 'failed')),
    error_message TEXT,
    related_id INTEGER,
    related_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_created ON email_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_status ON email_logs(status);
