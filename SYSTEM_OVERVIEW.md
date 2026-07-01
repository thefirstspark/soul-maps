# Soul Map Fulfillment & Monthly Regeneration System

Complete end-to-end automation for selling Soul Maps with recurring monthly updates.

## Architecture Overview

```
Buyer Journey:
┌─────────────────────────────────────────────────────────────────┐
│ 1. Sales Page (index.html)                                       │
│    $22 · Click "Claim Your Soul Map" → Whop checkout             │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Success Page (success.html)                                   │
│    Form: name, DOB, time, city, email                            │
│    POSTs to → webhook_server.py /generate endpoint               │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Webhook Server (webhook_server.py)                            │
│    • Generate soul map HTML + numerology/astrology data          │
│    • Generate first monthly update                               │
│    • Commit both to GitHub Pages                                 │
│    • Add to subscribers.json (12-month expiry auto-calculated)   │
│    • Send confirmation email with live link                      │
│    • Return JSON with soul map URL                               │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
           [Success Page Shows]
           ✓ Soul Map Live Link
           ✓ Monthly Update Link
           
┌─────────────────────────────────────────────────────────────────┐
│ 4. Every Month (1st of month, automatic)                         │
│    GitHub Actions runs monthly_regenerate.py:                   │
│    • Load all active subscribers                                 │
│    • Regenerate monthly update for each                          │
│    • Commit all to GitHub Pages                                  │
│    • Send "Your update is ready" emails                          │
│    • Deactivate expired subscribers                              │
└──────────────────────────────────────────────────────────────────┘
```

## Files & Structure

### Core Files

1. **webhook_server.py** (Flask server)
   - Endpoint: `POST /generate`
   - Receives: name, dob, time, city, email
   - Returns: JSON with soul map URL + monthly update
   - Auto-enrolls in `subscribers.json`
   - Sends confirmation emails

2. **monthly_regenerate.py** (Monthly cron job)
   - Loads active subscribers from `subscribers.json`
   - Regenerates monthly update for each
   - Commits to GitHub in one batch
   - Sends monthly update notification emails
   - Can be run manually or via GitHub Actions

3. **subscribers.json** (Subscriber database)
   - JSON array of subscriber records
   - Fields: name, email, dob, purchase_date, expiry_date, active
   - Auto-populated by webhook_server.py
   - Read by monthly_regenerate.py

4. **success.html** (Updated)
   - Form action: `/api/generate-soul-map`
   - Field names: name, dob, time, city, email
   - Submits to webhook server
   - Shows success message with soul map URL

5. **.github/workflows/monthly-regenerate.yml** (GitHub Actions)
   - Cron: `0 0 1 * *` (1st of month, 00:00 UTC)
   - Can be manually triggered
   - Runs: `python monthly_regenerate.py`

### Configuration Files

- **.env.example** — Environment variable template
- **WEBHOOK_SETUP.md** — Setup & deployment guide
- **WEBHOOK_SETUP.md** (updated) — Now includes monthly regeneration section

## Deployment Checklist

### Step 1: Set Up Environment Variables

```bash
# GitHub token (create at github.com/settings/tokens)
export GITHUB_PAT=ghp_...

# Email (optional, for confirmations)
export SMTP_EMAIL=your@email.com
export SMTP_PASSWORD=your_app_password  # Gmail app password from myaccount.google.com/apppasswords
```

### Step 2: Deploy Webhook Server

**Local Testing:**
```bash
cd soul-maps
pip install flask python-dotenv
python webhook_server.py
# Server listens on http://localhost:5000
```

**Production (Railway, Render, etc.):**
- Push to GitHub
- Deploy from Git
- Set environment variables in deployment dashboard
- Get production URL (e.g., `https://soul-map-webhook-xxxxx.railway.app`)

### Step 3: Update Success Page Form Action

In `soul-maps/success.html`, update form action from:
```html
<form id="intake-form" action="/api/generate-soul-map" method="POST">
```

To your production webhook URL:
```html
<form id="intake-form" action="https://your-webhook-server.com/generate" method="POST">
```

### Step 4: Set Up GitHub Actions (Monthly Automation)

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets:
   - `GITHUB_PAT` (same token as above)
   - `SMTP_EMAIL` (optional)
   - `SMTP_PASSWORD` (optional)
3. Workflow file is at `.github/workflows/monthly-regenerate.yml`
4. It runs automatically on the 1st of each month
5. You can manually trigger it from the Actions tab

### Step 5: Wire Up Whop

In Whop settings:
- Set post-purchase redirect to: `https://soul-maps.thefirstspark.shop/success.html`
- (Or wherever you host success.html)

## Testing

### Test Webhook Locally

```bash
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "dob": "1990-05-15",
    "time": "14:30",
    "city": "New York",
    "email": "test@example.com"
  }'
```

Expected response:
```json
{
  "success": true,
  "name": "Test User",
  "url": "https://soul-maps.thefirstspark.shop/TU51990.html",
  "monthly_update": "TU51990-202604.html",
  "message": "Soul Map generated for Test User · 12 monthly updates included"
}
```

### Test Monthly Regeneration

```bash
# List all active subscribers
python monthly_regenerate.py --list

# Run without emails
python monthly_regenerate.py --no-emails

# Run with emails
python monthly_regenerate.py
```

### Manually Trigger GitHub Actions

1. Go to GitHub repo → Actions → Monthly Soul Map Updates
2. Click "Run workflow" button
3. Watch the logs in real-time

## How Monthly Updates Work

### Timeline

- **Day 0 (Purchase)**: Buyer completes checkout
  - Webhook generates soul map + first monthly update
  - Subscriber added to `subscribers.json` with expiry = today + 365 days
  
- **Month 1 (1st of next month)**: Automated regeneration
  - GitHub Actions runs `monthly_regenerate.py`
  - Generates new monthly update for current month
  - Sends email: "Your March update is ready"
  
- **Months 2-12**: Same process repeats monthly
  
- **Month 13**: Subscriber expires
  - `monthly_regenerate.py` skips them (not in active list)
  - They're still in `subscribers.json` but marked `inactive`

### Subscriber Lifecycle

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "dob": "1990-05-15",
  "purchase_date": "2026-04-26T10:30:00",      // When they paid
  "expiry_date": "2027-04-26T10:30:00",        // 12 months later
  "active": true                                // Starts true, becomes false after expiry
}
```

After 12 months, they stop receiving monthly updates but their soul map stays live forever on GitHub Pages.

## Monitoring & Maintenance

### Check Subscriber Health

```bash
python monthly_regenerate.py --list
```

Shows all active subscribers and days remaining.

### Manual Subscriber Management

Edit `subscribers.json` directly to:
- Deactivate early: `"active": false`
- Extend: Modify `expiry_date`
- Remove: Delete the record

### Monitor GitHub Actions

- Go to Actions tab → Monthly Soul Map Updates
- See logs of each run
- Check commit history for soul map updates

### Monitor Email Delivery

Check your SMTP email (Gmail inbox) for:
- Bounce notifications
- Delivery confirmations

## Troubleshooting

### "No active subscribers to update"
- Check `subscribers.json` exists and has records
- Verify subscribers haven't expired
- Run `python monthly_regenerate.py --list` to see who's active

### "GITHUB_PAT not set"
- Set environment variable: `export GITHUB_PAT=ghp_...`
- Regeneration still works, files just won't commit to GitHub

### "Email not configured"
- Optional. Regeneration works without it.
- If you want emails, set `SMTP_EMAIL` and `SMTP_PASSWORD`

### "kerykeion import failed" (Moon/Rising signs not showing)
- Install: `pip install kerykeion`
- Optional; soul maps generate without it (just no lunar data)

### Workflow Not Running on Schedule
- Check GitHub Actions tab for errors
- Verify secrets are set correctly
- Try manual trigger to debug

## Performance Notes

- Generating 1 soul map: ~3-5 seconds
- Monthly regeneration (50 subscribers): ~2-5 minutes
- GitHub Actions minutes: Free for 2,000 min/month (monthly job is ~5 min/month)

## Cost Breakdown

- **Whop**: 10% transaction fee ($2.20 per $22 sale)
- **Email**: Free (Gmail SMTP)
- **GitHub**: Free (public Pages + Actions)
- **Hosting**: Free (GitHub Pages)
- **Webhook Server**: ~$5-10/month (Railway, Render, etc.)

**Net per sale**: ~$19.80 (after Whop fee)

## Future Enhancements

- Add custom personalization for each monthly update
- Let buyers upgrade to lifetime updates (no expiry)
- Add add-on purchases (deeper readings, astrology consultations)
- Dashboard to manage subscribers + send messages
- Analytics: track monthly regeneration success rate

---

Questions? Email kate@thefirstspark.shop
