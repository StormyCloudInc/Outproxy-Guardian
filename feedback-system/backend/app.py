from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
from datetime import datetime

from config import config
from models import Database
from utils.email import EmailService
from utils.rate_limit import RateLimiter

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
email_service = EmailService(config)
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

    try:
        # Save feedback
        feedback_id = db.add_feedback(
            document_id=document_id,
            feedback_type=feedback_type,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )

        # Send email for thumbs down
        if feedback_type == 'down':
            email_service.send_thumbs_down_notification(
                document_id=document_id,
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
    """Admin: Update feature request status"""
    admin_check = check_admin_access()
    if admin_check:
        return admin_check

    data = request.get_json()

    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status field'}), 400

    try:
        success = db.update_feature_status(feature_id, data['status'])
        if not success:
            return jsonify({'error': 'Feature not found'}), 404

        feature = db.get_feature_request(feature_id)

        return jsonify({
            'success': True,
            'feature': feature
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

# ==================== Widget Serving ====================

@app.route('/widgets/<path:filename>')
def serve_widget(filename):
    """Serve widget files for embedding"""
    widgets_dir = os.path.join(os.path.dirname(__file__), '../widgets')
    return send_from_directory(widgets_dir, filename)

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
