# Feedback, Voting & Feature Request System

A lightweight, self-hosted feedback and voting system designed for multi-network accessibility (clearnet, i2p, tor).

## Features

### 1. Document Feedback
- Simple thumbs up/down buttons for pages
- Real-time statistics
- Email notifications for negative feedback
- IP-based rate limiting to prevent spam

### 2. Voting System (Polls)
- Create custom polls with multiple options
- Real-time vote counting
- Session-based vote tracking to prevent vote bombing
- Optional multiple votes per user
- Beautiful embedded widgets

### 3. Feature Requests
- Users can submit feature requests
- Upvoting system with duplicate prevention
- Status tracking (pending, under review, planned, in progress, completed, rejected)
- Admin management interface

### 4. Admin Panel
- Localhost-only access (configurable)
- Create and manage polls
- Update feature request statuses
- Delete items
- View statistics

## Architecture

```
feedback-system/
├── backend/          # Flask API server
│   ├── app.py        # Main application
│   ├── config.py     # Configuration
│   ├── models.py     # Database models
│   └── utils/        # Email & rate limiting
├── widgets/          # Embeddable JavaScript widgets
│   ├── feedback.js   # Document feedback widget
│   ├── voting.js     # Poll widget
│   ├── features.js   # Feature request widget
│   └── styles.css    # Widget styles
├── admin/            # Admin panel
│   ├── index.html    # Admin interface
│   ├── admin.js      # Admin functionality
│   └── admin.css     # Admin styles
├── database/         # SQLite database & schema
│   ├── schema.sql    # Database schema
│   └── feedback.db   # Database file (auto-created)
└── .env              # Configuration file
```

## Installation

### Requirements
- Python 3.7+
- pip

### Step 1: Install Dependencies

```bash
cd feedback-system/backend
pip install -r requirements.txt
```

### Step 2: Configure

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
```

Key settings:
- `HOST=0.0.0.0` - Listen on all interfaces (for i2p/tor)
- `SMTP_*` - Configure email for thumbs down notifications
- `CORS_ORIGINS` - Set your website domains
- `RATE_LIMIT_*` - Adjust rate limits

### Step 3: Initialize Database

The database is automatically created when you first run the application.

### Step 4: Run the Server

```bash
cd backend
python app.py
```

The server will start on `http://0.0.0.0:5000`

## Multi-Network Setup

### Clearnet Access

Run normally. Use a reverse proxy (nginx) for HTTPS:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### I2P Setup

1. Configure I2P HTTP tunnel:
   - Tunnels > Server Tunnels > New HTTP Tunnel
   - Target host: 127.0.0.1
   - Target port: 5000
   - Enable tunnel

2. Update `.env`:
   ```
   I2P_URL=http://your-address.i2p:5000
   ```

### Tor Setup

1. Add to `/etc/tor/torrc`:
   ```
   HiddenServiceDir /var/lib/tor/feedback-service/
   HiddenServicePort 80 127.0.0.1:5000
   ```

2. Restart Tor: `sudo systemctl restart tor`

3. Get your .onion address:
   ```bash
   sudo cat /var/lib/tor/feedback-service/hostname
   ```

4. Update `.env`:
   ```
   TOR_URL=http://your-address.onion
   ```

## Usage

### Widget Embedding

All widgets are standalone JavaScript files that can be embedded on any page.

#### 1. Document Feedback Widget

Add thumbs up/down to any page:

```html
<!-- Add container -->
<div id="feedback-widget"
     data-document-id="page-about"
     data-api-url="http://your-server.com:5000">
</div>

<!-- Load widget script -->
<script src="http://your-server.com:5000/widgets/feedback.js"></script>

<!-- Optional: Load styles -->
<link rel="stylesheet" href="http://your-server.com:5000/widgets/styles.css">
```

**Attributes:**
- `data-document-id`: Unique ID for the page/document (required)
- `data-api-url`: Your API server URL (required)

#### 2. Poll Widget

Embed a poll on any page:

```html
<div id="poll-widget"
     data-poll-id="1"
     data-api-url="http://your-server.com:5000"
     data-show-results="false">
</div>

<script src="http://your-server.com:5000/widgets/voting.js"></script>
<link rel="stylesheet" href="http://your-server.com:5000/widgets/styles.css">
```

**Attributes:**
- `data-poll-id`: Poll ID from admin panel (required)
- `data-api-url`: Your API server URL (required)
- `data-show-results`: Show results without voting (optional, default: false)

#### 3. Feature Request Widget

Add feature submission and voting:

```html
<div id="features-widget"
     data-api-url="http://your-server.com:5000"
     data-mode="both"
     data-status=""
     data-max-items="10">
</div>

<script src="http://your-server.com:5000/widgets/features.js"></script>
<link rel="stylesheet" href="http://your-server.com:5000/widgets/styles.css">
```

**Attributes:**
- `data-api-url`: Your API server URL (required)
- `data-mode`: Display mode - "list", "submit", or "both" (optional, default: "both")
- `data-status`: Filter by status (optional, e.g., "pending")
- `data-max-items`: Maximum features to display (optional, default: 10)

### Admin Panel

Access the admin panel:

```
http://localhost:5000/admin/index.html
```

**Note:** By default, admin panel is only accessible from localhost. Set `ADMIN_ONLY_LOCALHOST=False` in `.env` to allow remote access.

**Admin Functions:**
- Create and manage polls
- Update feature request statuses
- Delete polls and features
- View statistics

## API Endpoints

### Feedback

```
POST   /api/feedback                    # Submit feedback
GET    /api/feedback/:document_id/stats # Get stats
```

### Polls

```
GET    /api/polls                       # List all polls
GET    /api/polls/:id                   # Get poll details
POST   /api/polls/:id/vote              # Cast vote
```

### Features

```
GET    /api/features                    # List features
GET    /api/features/:id                # Get feature
POST   /api/features                    # Submit feature
POST   /api/features/:id/upvote         # Upvote feature
```

### Admin (localhost only)

```
POST   /api/admin/polls                 # Create poll
DELETE /api/admin/polls/:id             # Delete poll
PATCH  /api/admin/features/:id          # Update feature status
DELETE /api/admin/features/:id          # Delete feature
```

## Security Features

### Rate Limiting
- IP-based rate limiting on all endpoints
- Configurable limits per action type
- Automatic cleanup of old rate limit records

### Vote Bombing Prevention
- Session tokens generated from IP + User Agent + Date
- Database-level unique constraints
- localStorage tracking on client side
- IP address logging

### Admin Protection
- Localhost-only access by default
- CORS configuration
- Session security settings

## Customization

### Widget Styling

Widgets use minimal, clean styles that can be easily customized. Override the CSS classes:

```css
/* Custom feedback widget */
.feedback-widget {
    background: your-color !important;
}

.feedback-btn:hover {
    border-color: your-accent-color !important;
}
```

### Email Templates

Edit `backend/utils/email.py` to customize email notifications:

```python
def send_thumbs_down_notification(self, document_id, ...):
    subject = "Custom Subject"
    body = """Custom email body"""
    ...
```

## Production Deployment

### Using systemd

Create `/etc/systemd/system/feedback-system.service`:

```ini
[Unit]
Description=Feedback System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/feedback-system/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable feedback-system
sudo systemctl start feedback-system
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

WORKDIR /app/backend

CMD ["python", "app.py"]
```

Build and run:

```bash
docker build -t feedback-system .
docker run -d -p 5000:5000 \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/.env:/app/backend/.env \
  feedback-system
```

### Backup

Backup the database regularly:

```bash
# Simple backup
cp feedback-system/database/feedback.db feedback.db.backup

# Automated backup (crontab)
0 2 * * * cp /path/to/feedback.db /backups/feedback-$(date +\%Y\%m\%d).db
```

## Troubleshooting

### Database Issues

```bash
# Reset database
rm database/feedback.db
python app.py  # Will recreate
```

### CORS Errors

Update `CORS_ORIGINS` in `.env`:

```
CORS_ORIGINS=http://your-site.com,http://your-site.i2p,http://your-site.onion
```

### Rate Limit Issues

Adjust limits in `.env`:

```
RATE_LIMIT_FEEDBACK=20
RATE_LIMIT_VOTE=50
```

Or disable temporarily:

```
RATE_LIMIT_ENABLED=False
```

### Email Not Sending

1. Check SMTP settings in `.env`
2. Test SMTP connection:

```python
python -c "
from config import config
from utils.email import EmailService
email = EmailService(config)
email.send_email('test@example.com', 'Test', 'Test body')
"
```

## Performance

- **Database:** SQLite handles 100k+ records efficiently
- **Lightweight:** ~20MB RAM usage
- **Fast:** <50ms response times
- **Scalable:** Use PostgreSQL for larger deployments

## License

This project is designed for self-hosting. Feel free to modify and use as needed.

## Support

For issues or questions, check the logs:

```bash
# View logs (systemd)
sudo journalctl -u feedback-system -f

# View logs (direct)
python app.py
```

## Future Enhancements

Potential additions:
- Analytics dashboard
- Export data (CSV/JSON)
- Authentication for admin panel
- Webhook notifications
- GraphQL API
- React/Vue widget versions
