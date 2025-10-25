# I2P Feedback System

A comprehensive feedback and feature request system designed for I2P, Tor, and clearnet deployment. Includes document feedback (thumbs up/down), feature requests with voting, polls, and email notifications.

## Features

### 📝 Document Feedback
- Thumbs up/down voting on documentation pages
- Optional email and detailed message collection on negative feedback
- Email notifications for thumbs down
- Automatic stats tracking per document
- Cloudflare Turnstile CAPTCHA integration

### 🎯 Feature Requests
- User-submitted feature requests
- Upvoting system with vote tracking
- Feature status management (pending, under review, planned, in progress, completed, rejected)
- Email subscription for feature status updates
- Admin editing capabilities
- **Comments on features** - Users can discuss feature requests
- Spam protection with rate limiting
- Admin comment moderation and deletion

### 📊 Polls & Voting
- Create custom polls with multiple options
- Real-time vote counting
- Optional multiple votes per user
- Results visualization
- Poll management (activate/deactivate/delete)

### 📧 Email System
- SMTP email notifications
- Email logging and statistics
- Track sent/failed emails
- Admin dashboard for email analytics

### 🛠️ Admin Panel
- **Document Feedback Stats**: View all feedback with satisfaction rates
- **Feature Management**: Edit, update status, delete feature requests
- **Comments Management**: View and moderate all comments, delete spam
- **Poll Management**: Create, edit, delete polls
- **Email Statistics**: Monitor all emails sent (success/failed rates)
- **Settings Editor**: Edit .env configuration directly from the admin panel
- **Widget Embed Codes**: Copy-paste embeddable widget code

### 🔌 Embeddable Widgets
Four easy-to-embed JavaScript widgets:
1. **feedback.js** - Document thumbs up/down
2. **features.js** - Feature request submission and voting
3. **voting.js** - Poll voting
4. **docs-feedback.js** - Integrated docs feedback with form

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd feedback-system

# Install dependencies
cd backend
pip3 install -r requirements.txt

# Initialize database
cd ../database
sqlite3 feedback.db < schema.sql

# Configure environment
cd ..
cp .env.example .env
nano .env

# Run application
cd backend
python3 app.py
```

## Production Deployment

See **[deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md)** for complete production deployment guide.

For full documentation, API reference, and usage examples, see the complete README above.

## Support

- Deployment guide: `deployment/DEPLOYMENT.md`
- Check application logs
- Visit admin panel: `http://localhost:5000/admin/`
