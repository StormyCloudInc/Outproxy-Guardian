-- Feedback System Database Schema

-- Document Feedback (thumbs up/down)
CREATE TABLE IF NOT EXISTS document_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(10) NOT NULL CHECK(feedback_type IN ('up', 'down')),
    email VARCHAR(255),
    message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_document_id ON document_feedback(document_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON document_feedback(created_at);

-- Voting Polls
CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    allow_multiple_votes BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ends_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_active ON polls(is_active);

-- Poll Options
CREATE TABLE IF NOT EXISTS poll_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL,
    option_text VARCHAR(255) NOT NULL,
    display_order INTEGER DEFAULT 0,
    FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
);

-- Poll Votes
CREATE TABLE IF NOT EXISTS poll_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL,
    option_id INTEGER NOT NULL,
    ip_address VARCHAR(45),
    session_token VARCHAR(64),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE,
    FOREIGN KEY (option_id) REFERENCES poll_options(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_poll_session ON poll_votes(poll_id, session_token);
CREATE INDEX IF NOT EXISTS idx_poll_ip ON poll_votes(poll_id, ip_address);

-- Feature Requests
CREATE TABLE IF NOT EXISTS feature_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK(status IN ('pending', 'under_review', 'planned', 'in_progress', 'completed', 'rejected')),
    submitter_name VARCHAR(100),
    submitter_email VARCHAR(255),
    ip_address VARCHAR(45),
    upvote_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_status ON feature_requests(status);
CREATE INDEX IF NOT EXISTS idx_upvote_count ON feature_requests(upvote_count DESC);

-- Feature Request Upvotes
CREATE TABLE IF NOT EXISTS feature_upvotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL,
    ip_address VARCHAR(45),
    session_token VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
    UNIQUE(feature_id, ip_address)
);

CREATE INDEX IF NOT EXISTS idx_feature_session ON feature_upvotes(feature_id, session_token);

-- Feature Request Subscriptions
CREATE TABLE IF NOT EXISTS feature_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
    UNIQUE(feature_id, email)
);

CREATE INDEX IF NOT EXISTS idx_feature_email ON feature_subscriptions(feature_id, email);

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

-- Rate Limiting
CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address VARCHAR(45) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rate_limit ON rate_limits(ip_address, action_type, action_key, created_at);

-- Admin Users (simple auth for admin panel)
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email Logs (track sent emails)
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

-- Mailing List (newsletter/updates subscriptions)
CREATE TABLE IF NOT EXISTS mailing_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1,
    unsubscribe_token VARCHAR(64) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    unsubscribed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mailing_active ON mailing_list(is_active);
CREATE INDEX IF NOT EXISTS idx_mailing_email ON mailing_list(email);
CREATE INDEX IF NOT EXISTS idx_mailing_token ON mailing_list(unsubscribe_token);
