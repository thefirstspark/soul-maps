# Soul Map Webhook Server Setup

The webhook server automates the entire fulfillment pipeline: receives payment confirmation → collects intake data → generates soul map → commits to GitHub → sends email.

## Quick Start (Local Testing)

### 1. Install Dependencies

```bash
cd soul-maps
pip install flask python-dotenv
```

### 2. Set Environment Variables

Create a `.env` file in the `soul-maps/` directory (or export in your shell):

```bash
# GitHub Personal Access Token (for auto-commit)
# Create at: https://github.com/settings/tokens
# Scopes needed: repo (all), read:user
export GITHUB_PAT=ghp_your_token_here

# Gmail SMTP (optional, for email confirmations)
# Use app password, not your regular password
# Create at: https://myaccount.google.com/apppasswords
export SMTP_EMAIL=your_email@gmail.com
export SMTP_PASSWORD=your_app_password
```

### 3. Start the Webhook Server

```bash
python webhook_server.py
```

You should see:
```
⚡ Soul Map Webhook Server starting...
  Listening on http://localhost:5000
  POST /generate to trigger soul map generation
```

### 4. Update the Success Page (Optional)

By default, the form action is `/api/generate-soul-map`, which works if:
- You're serving the success page from the same domain as the webhook (production)
- You're running both through a proxy (like Netlify)

For **local testing**, manually test the webhook:

```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "dob": "1990-05-15",
    "time": "14:30",
    "city": "New York",
    "email": "john@example.com"
  }'
```

## Production Deployment

### Option A: Heroku (Free tier discontinued, but low-cost paid option)

```bash
# Install Heroku CLI, then:
heroku login
heroku create your-app-name
heroku config:set GITHUB_PAT=ghp_... SMTP_EMAIL=... SMTP_PASSWORD=...
git push heroku main
```

### Option B: Railway or Render (Recommended)

- **Railway**: https://railway.app (easy GitHub integration, $5/month)
- **Render**: https://render.com (free tier available)
- **Replit**: https://replit.com (good for quick testing)

For any of these, push your code to GitHub and deploy the webhook server.

### Option C: Your Own Server

Run on a VPS, server, or cloud VM:

```bash
# Keep it running with supervisor or systemd
# Example systemd service:
[Unit]
Description=Soul Map Webhook Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/webhook_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## API Endpoint

### POST /generate

Receives intake data and generates soul map.

**Request:**
```json
{
  "name": "John Doe",
  "dob": "1990-05-15",
  "time": "14:30",
  "city": "New York",
  "country": "US",
  "email": "john@example.com"
}
```

**Response (Success):**
```json
{
  "success": true,
  "name": "John Doe",
  "url": "https://soul-maps.thefirstspark.shop/JD51990.html",
  "monthly_update": "JD51990-202604.html",
  "message": "Soul Map generated for John Doe · 12 monthly updates included",
  "summary": {
    "name": "John Doe",
    "life_path": 7,
    "expression": 3,
    "personal_year": 8,
    "sun_sign": "Taurus",
    ...
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Invalid DOB format. Use YYYY-MM-DD"
}
```

## What Happens Behind the Scenes

1. **Validation**: Check required fields (name, dob, email)
2. **Generation**: Call your existing `generate_soul_map()` with intake data
3. **Monthly Update**: Generate the first monthly update automatically
4. **GitHub Commit**: Push both files to the `soul-maps` repo
5. **Email**: Send confirmation email with the live link
6. **Response**: Return success JSON to the form

All of this takes 5-15 seconds depending on GitHub API latency.

## Monitoring

Check webhook logs:

```bash
# Watch server logs (if running locally)
# Watch GitHub commits: https://github.com/thefirstspark/soul-maps/commits/main
# Check email (Gmail inbox for delivery confirmations)
```

## Troubleshooting

### "GITHUB_PAT not set"
- Webhook still works, but soul maps won't be committed to GitHub
- Set the environment variable and restart the server

### "Email not configured"
- Webhook still works, but confirmation emails won't send
- Users can still access the live link in the response, they just won't get an email

### "kerykeion import failed" (Moon/Rising signs)
- Install: `pip install kerykeion`
- This is optional; soul maps will still generate without it

### "Deploy failed: git error"
- Check that `GITHUB_PAT` has `repo` scope
- Verify token hasn't expired
- Check network connectivity

## Testing Checklist

- [ ] Environment variables set (GITHUB_PAT at minimum)
- [ ] `pip install flask python-dotenv` completed
- [ ] `python webhook_server.py` starts without errors
- [ ] POST /generate with test data returns 200 + JSON
- [ ] Soul map HTML file appears in repo
- [ ] Monthly update file appears in repo
- [ ] Email received (if SMTP configured)
- [ ] Success page form submits correctly

## Monthly Regeneration (Automatic Updates)

The monthly regeneration system runs automatically on the 1st of each month to update all active subscribers.

### How It Works

1. **Subscriber Enrollment**: When a buyer completes checkout, they're automatically added to `subscribers.json` with:
   - Name, DOB, email
   - Purchase date
   - 12-month expiry date
   - Active status

2. **Monthly Regeneration**: On the 1st of each month, GitHub Actions automatically:
   - Loads all active subscribers (not yet expired)
   - Regenerates their monthly update HTML file
   - Commits all files to GitHub in one batch
   - Sends email notifications (optional)

3. **Expiry**: After 12 months, subscribers are no longer active and don't get monthly updates.

### Manual Testing

List all active subscribers:
```bash
cd soul-maps
python monthly_regenerate.py --list
```

Manually run regeneration (without emails):
```bash
export GITHUB_PAT=ghp_...
python monthly_regenerate.py --no-emails
```

Manually run with emails:
```bash
export GITHUB_PAT=ghp_...
export SMTP_EMAIL=your@email.com
export SMTP_PASSWORD=your_app_password
python monthly_regenerate.py
```

### GitHub Actions Setup

The workflow `.github/workflows/monthly-regenerate.yml`:
- Runs automatically at **00:00 UTC on the 1st of every month**
- Can be manually triggered from the GitHub Actions tab
- Requires these secrets to be set in your GitHub repo settings:
  - `GITHUB_PAT` (GitHub Personal Access Token)
  - `SMTP_EMAIL` (optional, for notifications)
  - `SMTP_PASSWORD` (optional, for notifications)

**To set up secrets:**
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add: `GITHUB_PAT`, `SMTP_EMAIL`, `SMTP_PASSWORD`

### Subscriber Data Format

`subscribers.json` stores subscriber records:
```json
[
  {
    "name": "John Doe",
    "email": "john@example.com",
    "dob": "1990-05-15",
    "purchase_date": "2026-04-26T10:30:00",
    "expiry_date": "2027-04-26T10:30:00",
    "active": true
  },
  ...
]
```

Subscribers are automatically marked `inactive` after their 12-month window expires.
