import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
import logging
import secrets

logger = logging.getLogger(__name__)

class Database:
    """Database manager for the feedback system"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Initialize the database with schema if it doesn't exist"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), '../database/schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()

            conn = sqlite3.connect(self.db_path)
            conn.executescript(schema)
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        else:
            logger.warning(f"Schema file not found at {schema_path}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()

    # Document Feedback Methods
    def add_feedback(self, document_id, feedback_type, email=None, message=None, ip_address=None, user_agent=None):
        """Add document feedback (thumbs up/down)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO document_feedback (document_id, feedback_type, email, message, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (document_id, feedback_type, email, message, ip_address, user_agent))
            return cursor.lastrowid

    def get_feedback_stats(self, document_id):
        """Get feedback statistics for a document"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    feedback_type,
                    COUNT(*) as count
                FROM document_feedback
                WHERE document_id = ?
                GROUP BY feedback_type
            """, (document_id,))
            results = cursor.fetchall()

            stats = {'up': 0, 'down': 0}
            for row in results:
                stats[row['feedback_type']] = row['count']

            return stats

    def get_all_feedback_stats(self):
        """Get aggregated feedback statistics for all documents"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    document_id,
                    feedback_type,
                    COUNT(*) as count,
                    MAX(created_at) as last_feedback
                FROM document_feedback
                GROUP BY document_id, feedback_type
                ORDER BY last_feedback DESC
            """)
            results = cursor.fetchall()

            # Organize by document
            docs = {}
            for row in results:
                doc_id = row['document_id']
                if doc_id not in docs:
                    docs[doc_id] = {
                        'document_id': doc_id,
                        'up': 0,
                        'down': 0,
                        'total': 0,
                        'last_feedback': row['last_feedback']
                    }
                docs[doc_id][row['feedback_type']] = row['count']
                docs[doc_id]['total'] += row['count']

            return list(docs.values())

    def get_recent_feedback(self, limit=50):
        """Get recent feedback entries with details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id,
                    document_id,
                    feedback_type,
                    email,
                    message,
                    created_at
                FROM document_feedback
                WHERE feedback_type = 'down' AND (message IS NOT NULL OR email IS NOT NULL)
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()

    # Poll Methods
    def create_poll(self, title, description='', allow_multiple_votes=False, ends_at=None):
        """Create a new poll"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO polls (title, description, allow_multiple_votes, ends_at)
                VALUES (?, ?, ?, ?)
            """, (title, description, allow_multiple_votes, ends_at))
            return cursor.lastrowid

    def add_poll_option(self, poll_id, option_text, display_order=0):
        """Add an option to a poll"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO poll_options (poll_id, option_text, display_order)
                VALUES (?, ?, ?)
            """, (poll_id, option_text, display_order))
            return cursor.lastrowid

    def get_poll(self, poll_id):
        """Get poll details with options"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get poll
            cursor.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
            poll = cursor.fetchone()

            if not poll:
                return None

            # Get options with vote counts
            cursor.execute("""
                SELECT
                    po.*,
                    COUNT(pv.id) as vote_count
                FROM poll_options po
                LEFT JOIN poll_votes pv ON po.id = pv.option_id
                WHERE po.poll_id = ?
                GROUP BY po.id
                ORDER BY po.display_order
            """, (poll_id,))
            options = cursor.fetchall()

            return {
                'poll': dict(poll),
                'options': [dict(opt) for opt in options]
            }

    def get_all_polls(self, active_only=True):
        """Get all polls"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM polls WHERE is_active = 1 ORDER BY created_at DESC")
            else:
                cursor.execute("SELECT * FROM polls ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def cast_vote(self, poll_id, option_id, ip_address=None, session_token=None, user_agent=None):
        """Cast a vote on a poll"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if already voted (if single vote poll)
            cursor.execute("SELECT allow_multiple_votes FROM polls WHERE id = ?", (poll_id,))
            poll = cursor.fetchone()

            if not poll:
                raise ValueError("Poll not found")

            if not poll['allow_multiple_votes']:
                # Check existing vote
                cursor.execute("""
                    SELECT id FROM poll_votes
                    WHERE poll_id = ? AND (ip_address = ? OR session_token = ?)
                """, (poll_id, ip_address, session_token))

                if cursor.fetchone():
                    raise ValueError("Already voted on this poll")

            cursor.execute("""
                INSERT INTO poll_votes (poll_id, option_id, ip_address, session_token, user_agent)
                VALUES (?, ?, ?, ?, ?)
            """, (poll_id, option_id, ip_address, session_token, user_agent))

            return cursor.lastrowid

    def update_poll_status(self, poll_id, is_active):
        """Update poll active status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE polls
                SET is_active = ?
                WHERE id = ?
            """, (is_active, poll_id))
            return cursor.rowcount > 0

    def delete_poll(self, poll_id):
        """Delete a poll"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM polls WHERE id = ?", (poll_id,))
            return cursor.rowcount > 0

    # Feature Request Methods
    def create_feature_request(self, title, description, submitter_name=None, submitter_email=None, ip_address=None):
        """Create a new feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feature_requests (title, description, submitter_name, submitter_email, ip_address)
                VALUES (?, ?, ?, ?, ?)
            """, (title, description, submitter_name, submitter_email, ip_address))
            return cursor.lastrowid

    def get_feature_request(self, feature_id):
        """Get a single feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feature_requests WHERE id = ?", (feature_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_all_feature_requests(self, status=None, sort_by='upvote_count'):
        """Get all feature requests"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM feature_requests"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status)

            if sort_by == 'upvote_count':
                query += " ORDER BY upvote_count DESC, created_at DESC"
            else:
                query += " ORDER BY created_at DESC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def upvote_feature(self, feature_id, ip_address=None, session_token=None):
        """Upvote a feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Add upvote (UNIQUE constraint prevents duplicates)
                cursor.execute("""
                    INSERT INTO feature_upvotes (feature_id, ip_address, session_token)
                    VALUES (?, ?, ?)
                """, (feature_id, ip_address, session_token))

                # Increment counter
                cursor.execute("""
                    UPDATE feature_requests
                    SET upvote_count = upvote_count + 1
                    WHERE id = ?
                """, (feature_id,))

                return True

            except sqlite3.IntegrityError:
                # Already upvoted
                return False

    def update_feature_status(self, feature_id, status):
        """Update feature request status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feature_requests
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, datetime.now(), feature_id))
            return cursor.rowcount > 0

    def delete_feature_request(self, feature_id):
        """Delete a feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM feature_requests WHERE id = ?", (feature_id,))
            return cursor.rowcount > 0

    def update_feature_request(self, feature_id, title=None, description=None):
        """Update feature request title and/or description (admin only)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if description is not None:
                updates.append("description = ?")
                params.append(description)

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(feature_id)

            query = f"UPDATE feature_requests SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            return cursor.rowcount > 0

    def subscribe_to_feature(self, feature_id, email):
        """Subscribe to feature request updates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO feature_subscriptions (feature_id, email)
                    VALUES (?, ?)
                """, (feature_id, email))
                return True
            except sqlite3.IntegrityError:
                # Already subscribed
                return False

    def get_feature_subscribers(self, feature_id):
        """Get all subscribers for a feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT email, subscribed_at
                FROM feature_subscriptions
                WHERE feature_id = ?
                ORDER BY subscribed_at DESC
            """, (feature_id,))
            return [dict(row) for row in cursor.fetchall()]

    def unsubscribe_from_feature(self, feature_id, email):
        """Unsubscribe an email from a feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM feature_subscriptions
                WHERE feature_id = ? AND email = ?
            """, (feature_id, email))
            return cursor.rowcount > 0

    def get_all_feature_subscriptions(self, feature_id):
        """Get all subscriptions for a feature (for admin view)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    fs.id,
                    fs.email,
                    fs.subscribed_at
                FROM feature_subscriptions fs
                WHERE fs.feature_id = ?
                ORDER BY fs.subscribed_at DESC
            """, (feature_id,))
            return [dict(row) for row in cursor.fetchall()]

    # Feature Comment Methods
    def add_feature_comment(self, feature_id, comment_text, author_name=None, author_email=None, ip_address=None, user_agent=None):
        """Add a comment to a feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feature_comments (feature_id, comment_text, author_name, author_email, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (feature_id, comment_text, author_name, author_email, ip_address, user_agent))
            return cursor.lastrowid

    def get_feature_comments(self, feature_id, include_deleted=False):
        """Get all comments for a feature request"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    id,
                    feature_id,
                    author_name,
                    author_email,
                    comment_text,
                    is_deleted,
                    created_at
                FROM feature_comments
                WHERE feature_id = ?
            """

            if not include_deleted:
                query += " AND is_deleted = 0"

            query += " ORDER BY created_at ASC"

            cursor.execute(query, (feature_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_comment_count(self, feature_id):
        """Get count of non-deleted comments for a feature"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM feature_comments
                WHERE feature_id = ? AND is_deleted = 0
            """, (feature_id,))
            result = cursor.fetchone()
            return result['count'] if result else 0

    def delete_comment(self, comment_id):
        """Soft delete a comment (admin only)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feature_comments
                SET is_deleted = 1
                WHERE id = ?
            """, (comment_id,))
            return cursor.rowcount > 0

    def get_recent_comments(self, limit=50, include_deleted=False):
        """Get recent comments across all features (admin view)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    fc.id,
                    fc.feature_id,
                    fc.author_name,
                    fc.author_email,
                    fc.comment_text,
                    fc.ip_address,
                    fc.is_deleted,
                    fc.created_at,
                    fr.title as feature_title
                FROM feature_comments fc
                JOIN feature_requests fr ON fc.feature_id = fr.id
            """

            if not include_deleted:
                query += " WHERE fc.is_deleted = 0"

            query += " ORDER BY fc.created_at DESC LIMIT ?"

            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def check_duplicate_comment(self, feature_id, comment_text, ip_address):
        """Check if the same comment was posted recently from this IP"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM feature_comments
                WHERE feature_id = ?
                AND comment_text = ?
                AND ip_address = ?
                AND created_at > datetime('now', '-24 hours')
            """, (feature_id, comment_text, ip_address))
            result = cursor.fetchone()
            return result['count'] > 0 if result else False

    # Email Logging Methods
    def log_email(self, email_type, recipient, subject, status, error_message=None, related_id=None, related_type=None):
        """Log an email send attempt"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_logs (email_type, recipient, subject, status, error_message, related_id, related_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (email_type, recipient, subject, status, error_message, related_id, related_type))
            return cursor.lastrowid

    def get_email_stats(self):
        """Get email statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get totals by status
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    MAX(created_at) as last_sent
                FROM email_logs
            """)
            stats = dict(cursor.fetchone())

            # Get counts by type
            cursor.execute("""
                SELECT email_type, COUNT(*) as count
                FROM email_logs
                GROUP BY email_type
                ORDER BY count DESC
            """)
            stats['by_type'] = [dict(row) for row in cursor.fetchall()]

            return stats

    def get_recent_emails(self, limit=50):
        """Get recent email logs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM email_logs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # Mailing List Methods
    @staticmethod
    def convert_i2p_email(email):
        """Convert @mail.i2p addresses to @i2pmail.org"""
        if email and email.endswith('@mail.i2p'):
            return email.replace('@mail.i2p', '@i2pmail.org')
        return email

    def subscribe_to_mailing_list(self, email, ip_address=None, user_agent=None):
        """Subscribe an email to the mailing list"""
        # Convert I2P mail addresses
        email = self.convert_i2p_email(email)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if email already exists
            cursor.execute("SELECT id, is_active FROM mailing_list WHERE email = ?", (email,))
            existing = cursor.fetchone()

            if existing:
                # If previously unsubscribed, reactivate
                if not existing['is_active']:
                    cursor.execute("""
                        UPDATE mailing_list
                        SET is_active = 1, unsubscribed_at = NULL, ip_address = ?, user_agent = ?
                        WHERE email = ?
                    """, (ip_address, user_agent, email))
                    logger.info(f"Reactivated mailing list subscription for {email}")
                    return existing['id']
                else:
                    # Already subscribed
                    return None

            # Generate unique unsubscribe token
            unsubscribe_token = secrets.token_urlsafe(32)

            cursor.execute("""
                INSERT INTO mailing_list (email, unsubscribe_token, ip_address, user_agent)
                VALUES (?, ?, ?, ?)
            """, (email, unsubscribe_token, ip_address, user_agent))

            logger.info(f"Added {email} to mailing list")
            return cursor.lastrowid

    def unsubscribe_from_mailing_list(self, token=None, email=None):
        """Unsubscribe from mailing list using token or email"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if token:
                cursor.execute("""
                    UPDATE mailing_list
                    SET is_active = 0, unsubscribed_at = ?
                    WHERE unsubscribe_token = ? AND is_active = 1
                """, (datetime.now(), token))
            elif email:
                # Convert I2P mail addresses
                email = self.convert_i2p_email(email)
                cursor.execute("""
                    UPDATE mailing_list
                    SET is_active = 0, unsubscribed_at = ?
                    WHERE email = ? AND is_active = 1
                """, (datetime.now(), email))
            else:
                return False

            return cursor.rowcount > 0

    def get_mailing_list_subscribers(self, active_only=True):
        """Get all mailing list subscribers"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                cursor.execute("""
                    SELECT * FROM mailing_list
                    WHERE is_active = 1
                    ORDER BY subscribed_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT * FROM mailing_list
                    ORDER BY subscribed_at DESC
                """)

            return [dict(row) for row in cursor.fetchall()]

    def remove_from_mailing_list(self, email):
        """Permanently remove an email from the mailing list (admin only)"""
        # Convert I2P mail addresses
        email = self.convert_i2p_email(email)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mailing_list WHERE email = ?", (email,))
            return cursor.rowcount > 0

    def get_mailing_list_stats(self):
        """Get mailing list statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as unsubscribed,
                    MAX(subscribed_at) as latest_subscription
                FROM mailing_list
            """)

            return dict(cursor.fetchone())
