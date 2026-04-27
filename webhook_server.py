#!/usr/bin/env python3
"""
Soul Map Webhook Server
===================
Receives POST requests from the success page with intake data,
automatically generates soul maps, commits to GitHub, and sends confirmation emails.

Setup:
  pip install flask python-dotenv

Environment variables (set in .env or export):
  GITHUB_PAT=ghp_your_personal_access_token
  SMTP_EMAIL=your_gmail@gmail.com
  SMTP_PASSWORD=your_app_password (Gmail: create at myaccount.google.com/apppasswords)

Run:
  python webhook_server.py

The server listens on localhost:5000 by default.
POST http://localhost:5000/generate to trigger.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import generator functions from soul_map_generator.py
sys.path.insert(0, str(Path(__file__).parent))
from soul_map_generator import generate_soul_map, generate_monthly_update, deploy_to_github, get_base_filename

# Path to subscriber database
SUBSCRIBERS_FILE = Path(__file__).parent / 'subscribers.json'

app = Flask(__name__)

# ============================================================
# EMAIL CONFIGURATION
# ============================================================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# ============================================================
# SUBSCRIBER MANAGEMENT
# ============================================================

def load_subscribers():
    """Load subscriber database from JSON file."""
    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_subscribers(subscribers):
    """Save subscriber database to JSON file."""
    with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subscribers, f, indent=2, ensure_ascii=False)


def add_subscriber(name, dob, email):
    """
    Add a new subscriber to the database.
    Automatically calculates 12-month expiry.
    """
    subscribers = load_subscribers()

    # Check if subscriber already exists
    for sub in subscribers:
        if sub['email'] == email:
            print(f"[SUBSCRIBER] Already exists: {email}")
            return sub

    # Calculate expiry (12 months from today)
    today = datetime.now()
    expiry = today + timedelta(days=365)

    subscriber = {
        'name': name,
        'email': email,
        'dob': dob,
        'purchase_date': today.isoformat(),
        'expiry_date': expiry.isoformat(),
        'active': True
    }

    subscribers.append(subscriber)
    save_subscribers(subscribers)

    print(f"[SUBSCRIBER] Added: {name} ({email})")
    return subscriber


def get_active_subscribers(as_of=None):
    """Get all subscribers whose 12-month window hasn't expired."""
    if as_of is None:
        as_of = datetime.now()

    subscribers = load_subscribers()
    active = []

    for sub in subscribers:
        if not sub.get('active', True):
            continue

        expiry = datetime.fromisoformat(sub['expiry_date'])
        if as_of <= expiry:
            active.append(sub)

    return active


def deactivate_subscriber(email):
    """Mark a subscriber as inactive (monthly updates stopped)."""
    subscribers = load_subscribers()
    for sub in subscribers:
        if sub['email'] == email:
            sub['active'] = False
            save_subscribers(subscribers)
            print(f"[SUBSCRIBER] Deactivated: {email}")
            return True
    return False


def send_confirmation_email(recipient_email, recipient_name, soul_map_url):
    """Send confirmation email with soul map link."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"[WARN] Email not configured. Would send to: {recipient_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✨ Your Soul Map is Ready — {recipient_name}"
        msg["From"] = SMTP_EMAIL
        msg["To"] = recipient_email

        # Plain text version
        text = f"""\
Hello {recipient_name},

Your Soul Map has been generated and is ready to explore.

LIVE LINK:
{soul_map_url}

This link is your personal frequency map. It includes:
- Core Numerology Numbers (Life Path, Expression, Soul Urge, etc)
- Western Astrology (Sun, Moon, Rising, and planetary positions)
- Chinese Zodiac + Element
- Personal Year & Month cycles
- 12-month energy forecast
- Life Phase guidance (Pinnacles & Challenges)
- Debugging Notes for patterns to watch

You have access to 12 months of monthly updates. New monthly energy reports
will be generated and sent to you automatically.

Questions? Reply to this email.

The First Spark
thefirstspark.shop
"""

        # HTML version
        html = f"""\
<html>
  <body style="font-family: 'Cormorant Garamond', Georgia, serif; background: #0B0B0C; color: #e0e7ff; padding: 40px 20px;">
    <div style="max-width: 700px; margin: 0 auto; border: 1px solid #6B4DF2; border-radius: 8px; padding: 40px; background: #0d0d14;">
      <h1 style="color: #F3B23A; text-align: center; margin-bottom: 10px;">✨ Soul Map Ready</h1>
      <p style="text-align: center; color: #26E4D8; font-size: 14px; margin-bottom: 40px;">Your frequency coordinates are waiting</p>

      <p style="font-size: 16px; line-height: 1.6;">Hello <strong>{recipient_name}</strong>,</p>

      <p style="font-size: 16px; line-height: 1.6;">
        Your Soul Map has been generated. Access it here:
      </p>

      <div style="text-align: center; margin: 40px 0;">
        <a href="{soul_map_url}" style="background: linear-gradient(135deg, #F3B23A, #FF6A3D); color: #0B0B0C; padding: 16px 32px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block; font-family: 'Space Mono', monospace;">
          VIEW YOUR SOUL MAP
        </a>
      </div>

      <h3 style="color: #26E4D8; margin: 30px 0 15px; font-size: 14px; text-transform: uppercase; letter-spacing: 2px;">What's Inside:</h3>
      <ul style="font-size: 14px; line-height: 2; color: #e0e7ff;">
        <li><strong>Core Numbers:</strong> Life Path, Expression, Soul Urge, Personality, Maturity</li>
        <li><strong>Astrology:</strong> Sun, Moon, Rising, and planetary placements</li>
        <li><strong>Cycles:</strong> Personal Year & Month energy (your 12-month forecast)</li>
        <li><strong>Life Phases:</strong> Pinnacles & Challenges for your four major life periods</li>
        <li><strong>Debugging Notes:</strong> Patterns to watch and optimize</li>
      </ul>

      <p style="font-size: 14px; line-height: 1.6; margin-top: 30px; color: #a8a8a8;">
        You have access to 12 months of monthly updates. New energy reports are generated automatically each month.
      </p>

      <p style="font-size: 14px; line-height: 1.6; margin-top: 20px;">
        <strong>Questions?</strong> Reply to this email.
      </p>

      <div style="margin-top: 50px; padding-top: 30px; border-top: 1px solid #6B4DF2; text-align: center; font-size: 12px; color: #6b7280;">
        <p><strong style="color: #F3B23A;">The First Spark</strong></p>
        <p><a href="https://thefirstspark.shop" style="color: #26E4D8; text-decoration: none;">thefirstspark.shop</a></p>
        <p style="margin-top: 10px; font-style: italic;">Reality is programmable. Consciousness is the code.</p>
      </div>
    </div>
  </body>
</html>
"""

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, recipient_email, msg.as_string())

        print(f"[EMAIL] Sent confirmation to {recipient_email}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}", file=sys.stderr)
        return False


# ============================================================
# WEBHOOK ENDPOINT
# ============================================================

@app.route('/generate', methods=['POST'])
def generate_soul_map_webhook():
    """
    POST endpoint that receives intake form data and generates soul map.

    Expected JSON:
    {
      "name": "John Doe",
      "dob": "1990-05-15",
      "time": "14:30",  # optional, HH:MM format
      "city": "New York",  # optional
      "country": "US",  # optional, default: US
      "email": "john@example.com"  # for confirmation
    }

    Returns:
    {
      "success": true,
      "name": "John Doe",
      "url": "https://soul-maps.thefirstspark.shop/JD51990.html",
      "message": "Soul Map generated and committed to GitHub"
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name') or not data.get('dob'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, dob'
            }), 400

        name = data['name'].strip()
        dob_str = data['dob'].strip()  # YYYY-MM-DD
        email = data.get('email', '').strip()
        time_str = data.get('time', '').strip() or None  # HH:MM
        city = data.get('city', '').strip() or None
        country = data.get('country', 'US').strip()

        print(f"\n[WEBHOOK] Generating soul map for {name}...")

        # Parse DOB
        try:
            from datetime import datetime as dt
            birth_date = dt.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid DOB format. Use YYYY-MM-DD'
            }), 400

        # Parse time (optional)
        birth_time = None
        if time_str:
            try:
                t = dt.strptime(time_str, '%H:%M')
                birth_time = (t.hour, t.minute)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid time format. Use HH:MM (24-hour)'
                }), 400

        # Generate soul map
        print(f"  [GEN] Numerology + Astrology...")
        html_soul_map, summary = generate_soul_map(
            name, birth_date,
            birth_time=birth_time,
            birth_city=city,
            birth_country=country
        )

        # Generate filename
        base_filename = get_base_filename(name, birth_date)
        filename = f"{base_filename}.html"

        # Deploy to GitHub
        print(f"  [GIT] Committing to GitHub...")
        github_token = os.getenv('GITHUB_PAT')
        if not github_token:
            # Fall back to local-only
            print(f"  [WARN] GITHUB_PAT not set. Saving locally only.")
            local_path = Path(filename)
            local_path.write_text(html_soul_map, encoding='utf-8')
            live_url = f"file://{local_path.absolute()}"
        else:
            os.environ['GITHUB_PAT'] = github_token
            success, result = deploy_to_github(html_soul_map, filename)
            if success:
                live_url = result
                print(f"  [GIT] ✓ Committed: {live_url}")
            else:
                print(f"  [WARN] GitHub deploy failed: {result}. Saving locally.")
                local_path = Path(filename)
                local_path.write_text(html_soul_map, encoding='utf-8')
                live_url = f"file://{local_path.absolute()}"

        # Generate monthly update (optional)
        print(f"  [MONTHLY] Generating first monthly update...")
        html_monthly, filename_monthly, _ = generate_monthly_update(name, birth_date)
        success_monthly, _ = deploy_to_github(html_monthly, filename_monthly)
        if success_monthly:
            print(f"  [MONTHLY] ✓ Committed")

        # Add to subscriber database (for monthly regeneration)
        print(f"  [SUBSCRIBER] Enrolling in monthly updates...")
        add_subscriber(name, dob_str, email)

        # Send confirmation email
        if email:
            print(f"  [EMAIL] Sending confirmation to {email}...")
            send_confirmation_email(email, name, live_url)

        print(f"  [DONE] Soul map ready for {name}")

        return jsonify({
            'success': True,
            'name': name,
            'url': live_url,
            'monthly_update': filename_monthly,
            'message': f'Soul Map generated for {name} · 12 monthly updates included',
            'summary': summary
        }), 200

    except Exception as e:
        print(f"[ERROR] {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200


# ============================================================
# ROOT
# ============================================================

@app.route('/', methods=['GET'])
def index():
    """Info page."""
    return jsonify({
        'service': 'Soul Map Webhook Server',
        'endpoints': {
            'POST /generate': 'Generate a soul map from intake data',
            'GET /health': 'Health check'
        },
        'docs': 'See webhook_server.py for request format'
    }), 200


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    # Check env vars
    if not os.getenv('GITHUB_PAT'):
        print("\n[WARN] GITHUB_PAT not set. Local generation only (no GitHub commits).")
        print("  To enable GitHub deployment, set: export GITHUB_PAT=ghp_...")

    if not os.getenv('SMTP_EMAIL') or not os.getenv('SMTP_PASSWORD'):
        print("\n[WARN] Email not configured (SMTP_EMAIL / SMTP_PASSWORD).")
        print("  Webhook will still work, but confirmation emails won't send.")
        print("  To enable: export SMTP_EMAIL=... SMTP_PASSWORD=...")

    # Get port from environment (Railway sets this), default to 5000 for local
    port = int(os.getenv('PORT', 5000))
    is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'

    print("\n⚡ Soul Map Webhook Server starting...")
    print(f"  Listening on port {port}")
    print(f"  POST /generate to trigger soul map generation")
    print(f"  GET /health to check status\n")

    app.run(host='0.0.0.0', port=port, debug=not is_production)
