import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
import logging

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
    def add_feedback(self, document_id, feedback_type, ip_address=None, user_agent=None):
        """Add document feedback (thumbs up/down)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO document_feedback (document_id, feedback_type, ip_address, user_agent)
                VALUES (?, ?, ?, ?)
            """, (document_id, feedback_type, ip_address, user_agent))
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
