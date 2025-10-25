from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
from datetime import datetime

from config import config
from models import Database
from utils.email import EmailService
from utils.rate_limit import RateLimiter
from utils.spam_filter import validate_comment_content, sanitize_comment, validate_author_info

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)

# Setup CORS
CORS(app, origins=config.CORS_ORIGINS)

# Setup logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
db = Database(config.DATABASE_PATH)
email_service = EmailService(config, db)
rate_limiter = RateLimiter(config.DATABASE_PATH)

# Helper functions
def get_client_ip():
    """Get client IP address, accounting for proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr

def get_user_agent():
    """Get client user agent"""
    return request.headers.get('User-Agent', '')

def check_rate_limit(action_type, action_key=''):
    """Check rate limit and return response if exceeded"""
    if not config.RATE_LIMIT_ENABLED:
        return None

    ip = get_client_ip()
    limit = config.RATE_LIMITS.get(action_type, 10)

    is_allowed, remaining, reset_time = rate_limiter.check_rate_limit(
        ip, action_type, action_key, limit
    )

    if not is_allowed:
        return jsonify({
            'error': 'Rate limit exceeded',
            'retry_after': reset_time.isoformat()
        }), 429

    # Record the action if allowed
    rate_limiter.record_action(ip, action_type, action_key)

    return None

def check_admin_access():
    """Check if request is from localhost (for admin endpoints)"""
    if config.ADMIN_ONLY_LOCALHOST:
        client_ip = get_client_ip()
        if client_ip not in ['127.0.0.1', 'localhost', '::1']:
            return jsonify({'error': 'Admin access restricted to localhost'}), 403
    return None

# ==================== Document Feedback Endpoints ====================

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit document feedback (thumbs up/down)"""
    rate_limit_response = check_rate_limit('feedback')
    if rate_limit_response:
        return rate_limit_response

    data = request.get_json()

    if not data or 'document_id' not in data or 'type' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    document_id = data['document_id']
    feedback_type = data['type']

    if feedback_type not in ['up', 'down']:
        return jsonify({'error': 'Invalid feedback type'}), 400

    # Optional fields
    email = data.get('email')
    message = data.get('message')

    try:
        # Save feedback
        feedback_id = db.add_feedback(
            document_id=document_id,
            feedback_type=feedback_type,
            email=email,
            message=message,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )

        # Send email for thumbs down
        if feedback_type == 'down':
            email_service.send_thumbs_down_notification(
                document_id=document_id,
                user_email=email,
                user_message=message,
                ip_address=get_client_ip(),
                user_agent=get_user_agent()
            )

        # Get updated stats
        stats = db.get_feedback_stats(document_id)

        return jsonify({
            'success': True,
            'feedback_id': feedback_id,
            'stats': stats
        }), 201

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@app.route('/api/feedback/<document_id>/stats', methods=['GET'])
def get_feedback_stats(document_id):
    """Get feedback statistics for a document"""
    try:
        stats = db.get_feedback_stats(document_id)
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}")
        return jsonify({'error': 'Failed to get stats'}), 500

@app.route('/api/admin/feedback/stats', methods=['GET'])
def get_all_feedback_stats():
    """Get feedback statistics for all documents (admin only)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        stats = db.get_all_feedback_stats()
        return jsonify({'documents': stats}), 200
    except Exception as e:
        logger.error(f"Error getting all feedback stats: {str(e)}")
        return jsonify({'error': 'Failed to get stats'}), 500

@app.route('/api/admin/feedback/recent', methods=['GET'])
def get_recent_feedback():
    """Get recent feedback with messages (admin only)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        limit = int(request.args.get('limit', 50))
        feedback = db.get_recent_feedback(limit=limit)
        return jsonify({'feedback': feedback}), 200
    except Exception as e:
        logger.error(f"Error getting recent feedback: {str(e)}")
        return jsonify({'error': 'Failed to get feedback'}), 500

# ==================== Voting/Polls Endpoints ====================

@app.route('/api/polls', methods=['GET'])
def get_polls():
    """Get all active polls"""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        polls = db.get_all_polls(active_only=active_only)
        return jsonify(polls), 200
    except Exception as e:
        logger.error(f"Error getting polls: {str(e)}")
        return jsonify({'error': 'Failed to get polls'}), 500

@app.route('/api/polls/<int:poll_id>', methods=['GET'])
def get_poll(poll_id):
    """Get poll details with results"""
    try:
        poll_data = db.get_poll(poll_id)
        if not poll_data:
            return jsonify({'error': 'Poll not found'}), 404

        return jsonify(poll_data), 200
    except Exception as e:
        logger.error(f"Error getting poll: {str(e)}")
        return jsonify({'error': 'Failed to get poll'}), 500

@app.route('/api/polls/<int:poll_id>/vote', methods=['POST'])
def vote_on_poll(poll_id):
    """Cast a vote on a poll"""
    rate_limit_response = check_rate_limit('vote', str(poll_id))
    if rate_limit_response:
        return rate_limit_response

    data = request.get_json()

    if not data or 'option_id' not in data:
        return jsonify({'error': 'Missing option_id'}), 400

    try:
        ip = get_client_ip()
        session_token = rate_limiter.generate_session_token(ip, get_user_agent())

        vote_id = db.cast_vote(
            poll_id=poll_id,
            option_id=data['option_id'],
            ip_address=ip,
            session_token=session_token,
            user_agent=get_user_agent()
        )

        # Get updated results
        poll_data = db.get_poll(poll_id)

        return jsonify({
            'success': True,
            'vote_id': vote_id,
            'poll': poll_data
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error casting vote: {str(e)}")
        return jsonify({'error': 'Failed to cast vote'}), 500

# ==================== Feature Request Endpoints ====================

@app.route('/api/features', methods=['GET'])
def get_features():
    """Get all feature requests"""
    try:
        status = request.args.get('status')
        sort_by = request.args.get('sort_by', 'upvote_count')

        features = db.get_all_feature_requests(status=status, sort_by=sort_by)
        return jsonify(features), 200
    except Exception as e:
        logger.error(f"Error getting features: {str(e)}")
        return jsonify({'error': 'Failed to get features'}), 500

@app.route('/api/features/<int:feature_id>', methods=['GET'])
def get_feature(feature_id):
    """Get a single feature request"""
    try:
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        return jsonify(feature), 200
    except Exception as e:
        logger.error(f"Error getting feature: {str(e)}")
        return jsonify({'error': 'Failed to get feature'}), 500

@app.route('/api/features', methods=['POST'])
def submit_feature():
    """Submit a new feature request"""
    rate_limit_response = check_rate_limit('feature_submit')
    if rate_limit_response:
        return rate_limit_response

    data = request.get_json()

    if not data or 'title' not in data or 'description' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        feature_id = db.create_feature_request(
            title=data['title'],
            description=data['description'],
            submitter_name=data.get('name'),
            submitter_email=data.get('email'),
            ip_address=get_client_ip()
        )

        feature = db.get_feature_request(feature_id)

        return jsonify({
            'success': True,
            'feature': feature
        }), 201

    except Exception as e:
        logger.error(f"Error submitting feature: {str(e)}")
        return jsonify({'error': 'Failed to submit feature'}), 500

@app.route('/api/features/<int:feature_id>/upvote', methods=['POST'])
def upvote_feature(feature_id):
    """Upvote a feature request"""
    rate_limit_response = check_rate_limit('feature_upvote', str(feature_id))
    if rate_limit_response:
        return rate_limit_response

    try:
        ip = get_client_ip()
        session_token = rate_limiter.generate_session_token(ip, get_user_agent())

        success = db.upvote_feature(
            feature_id=feature_id,
            ip_address=ip,
            session_token=session_token
        )

        if not success:
            return jsonify({'error': 'Already upvoted this feature'}), 400

        feature = db.get_feature_request(feature_id)

        return jsonify({
            'success': True,
            'feature': feature
        }), 200

    except Exception as e:
        logger.error(f"Error upvoting feature: {str(e)}")
        return jsonify({'error': 'Failed to upvote feature'}), 500

@app.route('/api/features/<int:feature_id>/subscribe', methods=['POST'])
def subscribe_to_feature(feature_id):
    """Subscribe to feature request updates"""
    rate_limit_response = check_rate_limit('feature_subscribe', str(feature_id))
    if rate_limit_response:
        return rate_limit_response

    data = request.get_json()

    if not data or 'email' not in data:
        return jsonify({'error': 'Missing email field'}), 400

    email = data['email'].strip()
    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    try:
        # Check if feature exists
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        success = db.subscribe_to_feature(feature_id, email)

        if not success:
            return jsonify({'error': 'Already subscribed'}), 400

        return jsonify({
            'success': True,
            'message': 'Successfully subscribed to feature updates'
        }), 201

    except Exception as e:
        logger.error(f"Error subscribing to feature: {str(e)}")
        return jsonify({'error': 'Failed to subscribe'}), 500

@app.route('/api/features/<int:feature_id>/unsubscribe', methods=['POST', 'GET'])
def unsubscribe_from_feature(feature_id):
    """Unsubscribe from feature request updates (public endpoint for email links)"""
    # Support both GET (from email links) and POST (from API calls)
    if request.method == 'GET':
        email = request.args.get('email', '').strip()
    else:
        data = request.get_json()
        email = data.get('email', '').strip() if data else ''

    if not email or '@' not in email:
        return jsonify({'error': 'Invalid or missing email address'}), 400

    try:
        # Check if feature exists
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        success = db.unsubscribe_from_feature(feature_id, email)

        if not success:
            return jsonify({'error': 'Subscription not found or already unsubscribed'}), 400

        logger.info(f"Unsubscribed {email} from feature {feature_id}")

        # Return HTML for GET requests (from email links)
        if request.method == 'GET':
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Unsubscribed Successfully</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 20px;
                        text-align: center;
                    }}
                    .success-box {{
                        background: #d4edda;
                        border: 1px solid #c3e6cb;
                        color: #155724;
                        padding: 30px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }}
                    h1 {{ color: #155724; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                </style>
            </head>
            <body>
                <h1>✓ Unsubscribed Successfully</h1>
                <div class="success-box">
                    <p>You have been unsubscribed from updates for:</p>
                    <p><strong>{feature['title']}</strong></p>
                    <p>You will no longer receive email notifications when the status of this feature changes.</p>
                </div>
            </body>
            </html>
            '''
            return html, 200

        # JSON response for API calls
        return jsonify({
            'success': True,
            'message': 'Successfully unsubscribed from feature updates'
        }), 200

    except Exception as e:
        logger.error(f"Error unsubscribing from feature: {str(e)}")
        return jsonify({'error': 'Failed to unsubscribe'}), 500

# ==================== Feature Comment Endpoints ====================

@app.route('/api/features/<int:feature_id>/comments', methods=['GET'])
def get_feature_comments(feature_id):
    """Get all comments for a feature request"""
    try:
        # Check if feature exists
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        comments = db.get_feature_comments(feature_id)

        return jsonify({
            'feature_id': feature_id,
            'comments': comments,
            'total': len(comments)
        }), 200

    except Exception as e:
        logger.error(f"Error getting comments: {str(e)}")
        return jsonify({'error': 'Failed to get comments'}), 500

@app.route('/api/features/<int:feature_id>/comments', methods=['POST'])
def add_feature_comment(feature_id):
    """Add a comment to a feature request"""
    rate_limit_response = check_rate_limit('comment', str(feature_id))
    if rate_limit_response:
        return rate_limit_response

    data = request.get_json()

    if not data or 'comment' not in data:
        return jsonify({'error': 'Missing comment field'}), 400

    try:
        # Check if feature exists
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        # Extract and sanitize data
        comment_text = sanitize_comment(data['comment'])
        author_name = data.get('name', '').strip() if data.get('name') else None
        author_email = data.get('email', '').strip() if data.get('email') else None

        # Validate comment content
        is_valid, error_msg = validate_comment_content(comment_text)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        # Validate author info
        is_valid, error_msg = validate_author_info(author_name, author_email)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        # Check for duplicate comment
        ip = get_client_ip()
        if db.check_duplicate_comment(feature_id, comment_text, ip):
            return jsonify({'error': 'Duplicate comment detected'}), 400

        # Add comment
        comment_id = db.add_feature_comment(
            feature_id=feature_id,
            comment_text=comment_text,
            author_name=author_name,
            author_email=author_email,
            ip_address=ip,
            user_agent=get_user_agent()
        )

        # Get the newly created comment
        comments = db.get_feature_comments(feature_id)
        new_comment = next((c for c in comments if c['id'] == comment_id), None)

        return jsonify({
            'success': True,
            'comment': new_comment
        }), 201

    except Exception as e:
        logger.error(f"Error adding comment: {str(e)}")
        return jsonify({'error': 'Failed to add comment'}), 500

# ==================== Admin Endpoints ====================

@app.route('/api/admin/polls', methods=['POST'])
def admin_create_poll():
    """Admin: Create a new poll"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    data = request.get_json()

    if not data or 'title' not in data or 'options' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        poll_id = db.create_poll(
            title=data['title'],
            description=data.get('description', ''),
            allow_multiple_votes=data.get('allow_multiple_votes', False),
            ends_at=data.get('ends_at')
        )

        # Add options
        for i, option_text in enumerate(data['options']):
            db.add_poll_option(poll_id, option_text, i)

        poll_data = db.get_poll(poll_id)

        return jsonify({
            'success': True,
            'poll': poll_data
        }), 201

    except Exception as e:
        logger.error(f"Error creating poll: {str(e)}")
        return jsonify({'error': 'Failed to create poll'}), 500

@app.route('/api/admin/polls/<int:poll_id>', methods=['PATCH'])
def admin_update_poll(poll_id):
    """Admin: Update a poll (toggle active status)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    data = request.get_json()

    if not data or 'is_active' not in data:
        return jsonify({'error': 'Missing is_active field'}), 400

    try:
        success = db.update_poll_status(poll_id, data['is_active'])
        if not success:
            return jsonify({'error': 'Poll not found'}), 404

        poll = db.get_poll(poll_id)

        return jsonify({
            'success': True,
            'poll': poll
        }), 200

    except Exception as e:
        logger.error(f"Error updating poll: {str(e)}")
        return jsonify({'error': 'Failed to update poll'}), 500

@app.route('/api/admin/polls/<int:poll_id>', methods=['DELETE'])
def admin_delete_poll(poll_id):
    """Admin: Delete a poll"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        success = db.delete_poll(poll_id)
        if not success:
            return jsonify({'error': 'Poll not found'}), 404

        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Error deleting poll: {str(e)}")
        return jsonify({'error': 'Failed to delete poll'}), 500

@app.route('/api/admin/features/<int:feature_id>', methods=['PATCH'])
def admin_update_feature(feature_id):
    """Admin: Update feature request (status, title, description)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        updated = False
        status_changed = False
        old_status = None
        new_status = None
        admin_message = data.get('admin_message')  # Optional admin message for status changes

        # Get old feature data before updating (needed for email notification)
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        # Update status if provided
        if 'status' in data:
            old_status = feature['status']
            new_status = data['status']

            if old_status != new_status:
                success = db.update_feature_status(feature_id, new_status)
                if not success:
                    return jsonify({'error': 'Feature not found'}), 404
                status_changed = True
                updated = True

        # Update title and/or description if provided
        if 'title' in data or 'description' in data:
            success = db.update_feature_request(
                feature_id,
                title=data.get('title'),
                description=data.get('description')
            )
            if not success and not updated:
                return jsonify({'error': 'Feature not found'}), 404
            updated = True

        if not updated:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Get updated feature
        feature = db.get_feature_request(feature_id)

        # Send email notifications if status changed
        if status_changed:
            sent_count = email_service.send_feature_status_change(
                feature_id=feature_id,
                feature_title=feature['title'],
                old_status=old_status,
                new_status=new_status,
                admin_message=admin_message
            )
            logger.info(f"Sent {sent_count} status change notifications for feature {feature_id}")

        return jsonify({
            'success': True,
            'feature': feature,
            'emails_sent': sent_count if status_changed else 0
        }), 200

    except Exception as e:
        logger.error(f"Error updating feature: {str(e)}")
        return jsonify({'error': 'Failed to update feature'}), 500

@app.route('/api/admin/features/<int:feature_id>', methods=['DELETE'])
def admin_delete_feature(feature_id):
    """Admin: Delete a feature request"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        success = db.delete_feature_request(feature_id)
        if not success:
            return jsonify({'error': 'Feature not found'}), 404

        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Error deleting feature: {str(e)}")
        return jsonify({'error': 'Failed to delete feature'}), 500

@app.route('/api/admin/features/<int:feature_id>/subscribers', methods=['GET'])
def admin_get_feature_subscribers(feature_id):
    """Admin: Get all subscribers for a feature request"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        # Check if feature exists
        feature = db.get_feature_request(feature_id)
        if not feature:
            return jsonify({'error': 'Feature not found'}), 404

        subscribers = db.get_all_feature_subscriptions(feature_id)

        return jsonify({
            'feature_id': feature_id,
            'feature_title': feature['title'],
            'subscribers': subscribers,
            'total': len(subscribers)
        }), 200

    except Exception as e:
        logger.error(f"Error getting feature subscribers: {str(e)}")
        return jsonify({'error': 'Failed to get subscribers'}), 500

@app.route('/api/admin/features/<int:feature_id>/subscribers/<path:email>', methods=['DELETE'])
def admin_remove_feature_subscriber(feature_id, email):
    """Admin: Remove a subscriber from a feature request"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        success = db.unsubscribe_from_feature(feature_id, email)

        if not success:
            return jsonify({'error': 'Subscriber not found'}), 404

        logger.info(f"Admin removed subscriber {email} from feature {feature_id}")

        return jsonify({
            'success': True,
            'message': 'Subscriber removed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error removing subscriber: {str(e)}")
        return jsonify({'error': 'Failed to remove subscriber'}), 500

# ==================== Admin - Comment Management ====================

@app.route('/api/admin/comments/recent', methods=['GET'])
def admin_get_recent_comments():
    """Admin: Get recent comments across all features"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        limit = int(request.args.get('limit', 50))
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'

        comments = db.get_recent_comments(limit=limit, include_deleted=include_deleted)

        return jsonify({
            'comments': comments,
            'total': len(comments)
        }), 200

    except Exception as e:
        logger.error(f"Error getting recent comments: {str(e)}")
        return jsonify({'error': 'Failed to get comments'}), 500

@app.route('/api/admin/comments/<int:comment_id>', methods=['DELETE'])
def admin_delete_comment(comment_id):
    """Admin: Delete (soft delete) a comment"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        success = db.delete_comment(comment_id)

        if not success:
            return jsonify({'error': 'Comment not found'}), 404

        logger.info(f"Admin deleted comment {comment_id}")

        return jsonify({
            'success': True,
            'message': 'Comment deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        return jsonify({'error': 'Failed to delete comment'}), 500

# ==================== Admin - Email Stats ====================

@app.route('/api/admin/email/stats', methods=['GET'])
def get_email_stats():
    """Get email statistics (admin only)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        stats = db.get_email_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting email stats: {str(e)}")
        return jsonify({'error': 'Failed to get email stats'}), 500

@app.route('/api/admin/email/recent', methods=['GET'])
def get_recent_email_logs():
    """Get recent email logs (admin only)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        limit = int(request.args.get('limit', 50))
        emails = db.get_recent_emails(limit=limit)
        return jsonify({'emails': emails}), 200
    except Exception as e:
        logger.error(f"Error getting recent emails: {str(e)}")
        return jsonify({'error': 'Failed to get email logs'}), 500

# ==================== Admin - Configuration ====================

@app.route('/api/admin/config', methods=['GET'])
def get_config():
    """Get current configuration (admin only, sensitive values masked)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        # Read .env file
        env_path = os.path.join(os.path.dirname(__file__), '../.env')
        env_vars = {}

        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Mask sensitive values
                        if any(sensitive in key.upper() for sensitive in ['PASSWORD', 'SECRET', 'KEY']):
                            env_vars[key] = '********' if value else ''
                        else:
                            env_vars[key] = value

        return jsonify({'config': env_vars}), 200
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({'error': 'Failed to get configuration'}), 500

@app.route('/api/admin/config', methods=['POST'])
def update_config():
    """Update configuration (admin only)"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        data = request.get_json()
        if not data or 'config' not in data:
            return jsonify({'error': 'Missing configuration data'}), 400

        env_path = os.path.join(os.path.dirname(__file__), '../.env')

        # Write new .env file
        with open(env_path, 'w') as f:
            f.write('# Feedback System Configuration\n')
            f.write('# Updated via Admin Panel\n\n')
            for key, value in data['config'].items():
                # Skip masked passwords unless they're being changed
                if value != '********':
                    f.write(f'{key}={value}\n')
                else:
                    # Keep existing value for masked fields
                    if os.path.exists(env_path):
                        with open(env_path, 'r') as old_f:
                            for line in old_f:
                                if line.strip().startswith(key + '='):
                                    f.write(line)
                                    break

        return jsonify({'success': True, 'message': 'Configuration updated. Restart required.'}), 200
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return jsonify({'error': 'Failed to update configuration'}), 500

# ==================== Widget Serving ====================

@app.route('/widgets/<path:filename>')
def serve_widget(filename):
    """Serve widget files for embedding"""
    widgets_dir = os.path.join(os.path.dirname(__file__), '../widgets')
    return send_from_directory(widgets_dir, filename)

@app.route('/admin/<path:filename>')
def serve_admin(filename):
    """Serve admin panel files"""
    admin_dir = os.path.join(os.path.dirname(__file__), '../admin')
    return send_from_directory(admin_dir, filename)

@app.route('/admin')
@app.route('/admin/')
def admin_redirect():
    """Redirect to admin panel"""
    from flask import redirect
    return redirect('/admin/index.html')

@app.route('/')
def index():
    """Root page with system information"""
    return jsonify({
        'name': 'I2P Feedback System',
        'version': '1.0.0',
        'endpoints': {
            'admin_panel': '/admin/',
            'health_check': '/api/health',
            'documentation': {
                'feedback': 'POST /api/feedback - Submit document feedback',
                'polls': 'GET /api/polls - List all polls',
                'features': 'GET /api/features - List feature requests',
                'widgets': '/widgets/ - Widget files for embedding'
            }
        }
    }), 200

# ==================== Mailing List Endpoints ====================

@app.route('/api/mailing-list/subscribe', methods=['POST'])
def subscribe_to_mailing_list():
    """Subscribe to the mailing list"""
    rate_limit_response = check_rate_limit('mailing_list_subscribe')
    if rate_limit_response:
        return rate_limit_response

    data = request.get_json()

    if not data or 'email' not in data:
        return jsonify({'error': 'Missing email field'}), 400

    email = data['email'].strip()
    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    try:
        subscriber_id = db.subscribe_to_mailing_list(
            email=email,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )

        if subscriber_id is None:
            return jsonify({'error': 'Already subscribed to the mailing list'}), 400

        return jsonify({
            'success': True,
            'message': 'Successfully subscribed to the mailing list'
        }), 201

    except Exception as e:
        logger.error(f"Error subscribing to mailing list: {str(e)}")
        return jsonify({'error': 'Failed to subscribe'}), 500

@app.route('/api/mailing-list/unsubscribe', methods=['GET', 'POST'])
def unsubscribe_from_mailing_list_route():
    """Unsubscribe from the mailing list"""
    # Support both GET (from email links) and POST (from forms)
    if request.method == 'GET':
        token = request.args.get('token', '').strip()
    else:
        data = request.get_json()
        token = data.get('token', '').strip() if data else ''

    if not token:
        return jsonify({'error': 'Missing unsubscribe token'}), 400

    try:
        success = db.unsubscribe_from_mailing_list(token=token)

        if not success:
            return jsonify({'error': 'Invalid token or already unsubscribed'}), 400

        # Return HTML for GET requests (from email links)
        if request.method == 'GET':
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Unsubscribed Successfully</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 20px;
                        text-align: center;
                    }
                    .success-box {
                        background: #d4edda;
                        border: 1px solid #c3e6cb;
                        color: #155724;
                        padding: 30px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }
                    h1 { color: #155724; }
                </style>
            </head>
            <body>
                <h1>✓ Unsubscribed Successfully</h1>
                <div class="success-box">
                    <p>You have been unsubscribed from the mailing list.</p>
                    <p>You will no longer receive email updates from us.</p>
                </div>
            </body>
            </html>
            '''
            return html, 200

        # JSON response for API calls
        return jsonify({
            'success': True,
            'message': 'Successfully unsubscribed from mailing list'
        }), 200

    except Exception as e:
        logger.error(f"Error unsubscribing from mailing list: {str(e)}")
        return jsonify({'error': 'Failed to unsubscribe'}), 500

@app.route('/api/admin/mailing-list/subscribers', methods=['GET'])
def admin_get_mailing_list_subscribers():
    """Admin: Get all mailing list subscribers"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        subscribers = db.get_mailing_list_subscribers(active_only=active_only)

        return jsonify({
            'subscribers': subscribers,
            'total': len(subscribers)
        }), 200

    except Exception as e:
        logger.error(f"Error getting mailing list subscribers: {str(e)}")
        return jsonify({'error': 'Failed to get subscribers'}), 500

@app.route('/api/admin/mailing-list/subscribers/<path:email>', methods=['DELETE'])
def admin_remove_mailing_list_subscriber(email):
    """Admin: Remove a subscriber from the mailing list"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        success = db.remove_from_mailing_list(email)

        if not success:
            return jsonify({'error': 'Subscriber not found'}), 404

        logger.info(f"Admin removed {email} from mailing list")

        return jsonify({
            'success': True,
            'message': 'Subscriber removed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error removing mailing list subscriber: {str(e)}")
        return jsonify({'error': 'Failed to remove subscriber'}), 500

@app.route('/api/admin/mailing-list/stats', methods=['GET'])
def admin_get_mailing_list_stats():
    """Admin: Get mailing list statistics"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    try:
        stats = db.get_mailing_list_stats()
        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting mailing list stats: {str(e)}")
        return jsonify({'error': 'Failed to get stats'}), 500

@app.route('/api/admin/mailing-list/send', methods=['POST'])
def admin_send_mailing_list_broadcast():
    """Admin: Send email to all mailing list subscribers"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    data = request.get_json()

    if not data or 'subject' not in data or 'message' not in data:
        return jsonify({'error': 'Missing subject or message'}), 400

    try:
        sent_count = email_service.send_mailing_list_broadcast(
            subject=data['subject'],
            message=data['message'],
            html_message=data.get('html_message')
        )

        return jsonify({
            'success': True,
            'sent_count': sent_count,
            'message': f'Email sent to {sent_count} subscribers'
        }), 200

    except Exception as e:
        logger.error(f"Error sending mailing list broadcast: {str(e)}")
        return jsonify({'error': 'Failed to send email'}), 500

# ==================== Health Check ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

# ==================== Main ====================

if __name__ == '__main__':
    logger.info(f"Starting feedback system on {config.HOST}:{config.PORT}")
    logger.info(f"CORS enabled for: {config.CORS_ORIGINS}")
    logger.info(f"Admin access: {'localhost only' if config.ADMIN_ONLY_LOCALHOST else 'open'}")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
