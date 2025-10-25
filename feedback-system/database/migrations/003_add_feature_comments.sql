-- Migration: Add feature comments table
-- Date: 2025-10-24
-- Description: Adds commenting functionality to feature requests

-- Feature Request Comments
CREATE TABLE IF NOT EXISTS feature_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL,
    author_name VARCHAR(100),
    author_email VARCHAR(255),
    comment_text TEXT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_deleted BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comment_feature ON feature_comments(feature_id, created_at);
CREATE INDEX IF NOT EXISTS idx_comment_deleted ON feature_comments(is_deleted);
