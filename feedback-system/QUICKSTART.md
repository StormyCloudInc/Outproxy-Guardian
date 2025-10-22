# Quick Start Guide

Get your feedback system running in 5 minutes!

## Installation

### Option 1: Using the Start Script (Recommended)

```bash
cd feedback-system
./start.sh
```

The script will:
- Create a virtual environment
- Install dependencies
- Start the server

### Option 2: Manual Setup

```bash
cd feedback-system/backend

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp ../.env.example .env

# Edit configuration (optional for testing)
nano .env

# Start server
python app.py
```

## Accessing the System

Once running, open these URLs:

1. **Admin Panel:** http://localhost:5000/admin/index.html
2. **Widget Examples:** Open `feedback-system/example.html` in your browser
3. **API:** http://localhost:5000/api/health

## Quick Test

### 1. Test Document Feedback

Open `example.html` in your browser and click the thumbs up/down buttons.

### 2. Create a Poll

1. Go to http://localhost:5000/admin/index.html
2. Click "Create New Poll"
3. Fill in:
   - Title: "What's your favorite feature?"
   - Options: "Feedback", "Polls", "Feature Requests"
4. Click "Create Poll"
5. Refresh `example.html` to see the poll

### 3. Test Feature Requests

In `example.html`, scroll to the Feature Request widget and:
1. Submit a feature request
2. Upvote it
3. Check the admin panel to change its status

## Embed on Your Website

Copy this code to any page:

```html
<!-- Document Feedback -->
<div id="feedback-widget"
     data-document-id="your-page-id"
     data-api-url="http://localhost:5000">
</div>
<script src="http://localhost:5000/widgets/feedback.js"></script>
<link rel="stylesheet" href="http://localhost:5000/widgets/styles.css">
```

## Configuration

Edit `backend/.env` to configure:

- **Email notifications:** Set `SMTP_*` settings
- **Rate limits:** Adjust `RATE_LIMIT_*` values
- **CORS:** Add your website domains to `CORS_ORIGINS`
- **Network access:** Set `HOST=0.0.0.0` for i2p/tor

## Multi-Network Setup

### For Clearnet + I2P + Tor:

1. Set in `.env`:
   ```
   HOST=0.0.0.0
   PORT=5000
   ```

2. Configure I2P tunnel pointing to `127.0.0.1:5000`

3. Configure Tor hidden service:
   ```
   HiddenServiceDir /var/lib/tor/feedback/
   HiddenServicePort 80 127.0.0.1:5000
   ```

4. Update widget URLs for each network:
   ```html
   <!-- Clearnet -->
   data-api-url="http://your-domain.com:5000"

   <!-- I2P -->
   data-api-url="http://your-address.i2p:5000"

   <!-- Tor -->
   data-api-url="http://your-address.onion:5000"
   ```

## Troubleshooting

### Port already in use
Change `PORT` in `.env` to a different port (e.g., 5001)

### CORS errors
Add your website domain to `CORS_ORIGINS` in `.env`:
```
CORS_ORIGINS=http://localhost,http://your-site.com
```

### Database errors
Delete and recreate the database:
```bash
rm database/feedback.db
python backend/app.py
```

### Can't access admin panel remotely
Set in `.env`:
```
ADMIN_ONLY_LOCALHOST=False
```
⚠️ Not recommended for production without authentication

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Set up email notifications for thumbs down feedback
- Configure rate limits based on your traffic
- Set up HTTPS with nginx reverse proxy
- Configure I2P and Tor for anonymous access
- Customize widget styles to match your website

## Production Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Configure SMTP for email notifications
- [ ] Set proper `CORS_ORIGINS`
- [ ] Enable rate limiting
- [ ] Set up HTTPS/SSL
- [ ] Configure database backups
- [ ] Set `DEBUG=False`
- [ ] Use systemd or Docker for auto-restart
- [ ] Set up monitoring/logging

## Support

Check the logs if something goes wrong:

```bash
# View server output
python backend/app.py

# Check database
sqlite3 database/feedback.db "SELECT * FROM polls;"
```

For more help, see [README.md](README.md)
