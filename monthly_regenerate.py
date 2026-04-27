#!/usr/bin/env python3
"""
Monthly Soul Map Update Regenerator
====================================
Runs monthly to regenerate all subscriber monthly update files.

This script:
1. Loads active subscribers
2. Regenerates their monthly update for the current month
3. Commits all updates to GitHub
4. Optionally sends email notifications

Setup:
  export GITHUB_PAT=ghp_your_token
  python monthly_regenerate.py

Or run via cron:
  0 0 1 * * cd /path/to/soul-maps && python monthly_regenerate.py >> regenerate.log 2>&1
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import generator functions
sys.path.insert(0, str(Path(__file__).parent))
from soul_map_generator import generate_monthly_update, deploy_to_github

# ============================================================
# CONFIGURATION
# ============================================================

SUBSCRIBERS_FILE = Path(__file__).parent / 'subscribers.json'
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


# ============================================================
# EMAIL NOTIFICATION
# ============================================================

def send_monthly_update_email(recipient_email, recipient_name, month_name, update_url):
    """Send notification that this month's update is ready."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"[WARN] Email not configured. Would send to: {recipient_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✨ Your {month_name} Soul Map Energy Update Is Ready"
        msg["From"] = SMTP_EMAIL
        msg["To"] = recipient_email

        # Plain text
        text = f"""\
Hello {recipient_name},

Your {month_name} energy update is ready.

VIEW YOUR UPDATE:
{update_url}

This month's reading reveals the frequency you're operating within and what to focus on.

The First Spark
thefirstspark.shop
"""

        # HTML
        html = f"""\
<html>
  <body style="font-family: 'Cormorant Garamond', Georgia, serif; background: #0B0B0C; color: #e0e7ff; padding: 40px 20px;">
    <div style="max-width: 700px; margin: 0 auto; border: 1px solid #6B4DF2; border-radius: 8px; padding: 40px; background: #0d0d14;">
      <h1 style="color: #F3B23A; text-align: center; margin-bottom: 10px;">✨ Monthly Update Ready</h1>
      <p style="text-align: center; color: #26E4D8; font-size: 14px; margin-bottom: 40px;">{month_name} energy reading</p>

      <p style="font-size: 16px; line-height: 1.6;">Hello <strong>{recipient_name}</strong>,</p>

      <p style="font-size: 16px; line-height: 1.6;">
        Your {month_name} soul map energy update has been generated.
      </p>

      <div style="text-align: center; margin: 40px 0;">
        <a href="{update_url}" style="background: linear-gradient(135deg, #F3B23A, #FF6A3D); color: #0B0B0C; padding: 16px 32px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block; font-family: 'Space Mono', monospace;">
          VIEW THIS MONTH'S ENERGY
        </a>
      </div>

      <p style="font-size: 14px; line-height: 1.6; margin-top: 30px; color: #a8a8a8;">
        This is a personal frequency reading for the current month. Check back next month for your next update.
      </p>

      <div style="margin-top: 50px; padding-top: 30px; border-top: 1px solid #6B4DF2; text-align: center; font-size: 12px; color: #6b7280;">
        <p><strong style="color: #F3B23A;">The First Spark</strong></p>
        <p><a href="https://thefirstspark.shop" style="color: #26E4D8; text-decoration: none;">thefirstspark.shop</a></p>
      </div>
    </div>
  </body>
</html>
"""

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, recipient_email, msg.as_string())

        print(f"  [EMAIL] ✓ {recipient_name} ({recipient_email})")
        return True

    except Exception as e:
        print(f"  [EMAIL] ✗ Failed for {recipient_email}: {e}")
        return False


# ============================================================
# MONTHLY REGENERATION
# ============================================================

def regenerate_all_monthly_updates(send_emails=True):
    """
    Regenerate monthly updates for all active subscribers.

    Returns: (success_count, total_count, failed_list)
    """
    today = date.today()
    month_name = today.strftime('%B %Y')

    # Get active subscribers
    subscribers = get_active_subscribers()
    if not subscribers:
        print("No active subscribers to update.")
        return 0, 0, []

    print(f"\n⚡ MONTHLY UPDATE REGENERATION")
    print(f"{'='*60}")
    print(f"  Month:        {month_name}")
    print(f"  Subscribers:  {len(subscribers)}")
    print(f"  Send Emails:  {'Yes' if send_emails else 'No'}")
    print(f"{'='*60}\n")

    success_count = 0
    failed = []
    files_generated = []

    for i, sub in enumerate(subscribers, 1):
        name = sub['name']
        email = sub['email']
        dob_str = sub['dob']

        try:
            # Parse DOB
            from datetime import datetime as dt
            birth_date = dt.strptime(dob_str, '%Y-%m-%d').date()

            # Generate monthly update
            html, filename, summary = generate_monthly_update(name, birth_date)
            files_generated.append((filename, html))

            print(f"  [{i}/{len(subscribers)}] ✓ {name:30s} → {filename}")
            success_count += 1

            # Send email notification (optional)
            if send_emails and email:
                # Build live URL (assumes GitHub Pages at soul-maps.thefirstspark.shop)
                live_url = f"https://soul-maps.thefirstspark.shop/{filename}"
                send_monthly_update_email(email, name, month_name, live_url)

        except Exception as e:
            print(f"  [{i}/{len(subscribers)}] ✗ {name:30s} — {str(e)}")
            failed.append({'name': name, 'email': email, 'error': str(e)})

    # Commit all files to GitHub in one batch
    if files_generated:
        print(f"\n  [GIT] Committing {len(files_generated)} files to GitHub...")
        try:
            for filename, html in files_generated:
                success, result = deploy_to_github(html, filename)
                if not success:
                    print(f"    ✗ Failed: {filename} — {result}")
                    # Remove from success count if commit failed
                    success_count -= 1
                    failed.append({'name': '', 'email': '', 'error': f'{filename}: {result}'})
            print(f"  [GIT] ✓ All updates committed")
        except Exception as e:
            print(f"  [GIT] ✗ Commit failed: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Completed: {success_count}/{len(subscribers)} ✓")
    if failed:
        print(f"  Failed:    {len(failed)} ✗")
    print(f"{'='*60}\n")

    return success_count, len(subscribers), failed


# ============================================================
# CLI
# ============================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Monthly Soul Map Update Regenerator')
    parser.add_argument('--no-emails', action='store_true', help='Skip sending email notifications')
    parser.add_argument('--list', action='store_true', help='List all active subscribers')

    args = parser.parse_args()

    # List mode
    if args.list:
        subscribers = get_active_subscribers()
        print(f"\n📋 ACTIVE SUBSCRIBERS ({len(subscribers)})")
        print(f"{'='*60}")
        for sub in subscribers:
            expiry = datetime.fromisoformat(sub['expiry_date'])
            days_left = (expiry - datetime.now()).days
            print(f"  {sub['name']:30s} | {sub['email']:30s} | {days_left:3d} days left")
        print(f"{'='*60}\n")
        sys.exit(0)

    # Check environment
    if not os.getenv('GITHUB_PAT'):
        print("\n[ERROR] GITHUB_PAT environment variable not set.")
        print("  Export it: export GITHUB_PAT=ghp_...")
        sys.exit(1)

    if not os.getenv('SMTP_EMAIL') or not os.getenv('SMTP_PASSWORD'):
        print("\n[WARN] Email not configured (SMTP_EMAIL / SMTP_PASSWORD).")
        print("  Monthly regeneration will work, but subscribers won't get email notifications.\n")

    # Run regeneration
    success, total, failed = regenerate_all_monthly_updates(send_emails=not args.no_emails)

    # Report
    if failed:
        print("FAILED:")
        for f in failed:
            print(f"  - {f.get('name', f.get('error'))}: {f.get('error', '')}")

    sys.exit(0 if len(failed) == 0 else 1)
