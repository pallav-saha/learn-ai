"""
Birthday Reminder Cron Job

Runs daily (via GitHub Actions or Render cron):
1. Connects to Supabase DB
2. Checks all users' birthdays
3. Sends email reminders

On the 1st of the month → monthly summary
Every day → daily birthday reminder
"""

import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from supabase import create_client, Client

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service role key (full access)
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")


def get_supabase() -> Client:
    """Initialize Supabase client with service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def send_email(to_email: str, subject: str, body_html: str):
    """Send an email via Gmail SMTP."""
    if not SENDER_APP_PASSWORD:
        print(f"ERROR: SENDER_APP_PASSWORD not set")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"  ✅ Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send to {to_email}: {e}")
        return False


def build_monthly_email(month_name: str, birthdays: list) -> str:
    """Build HTML for monthly summary."""
    sorted_bdays = sorted(birthdays, key=lambda b: int(b["birthday"].split("-")[0]))
    rows = ""
    for b in sorted_bdays:
        day = b["birthday"].split("-")[0]
        rows += f'<tr><td style="padding:8px;border-bottom:1px solid #eee;">{b["name"]}</td>'
        rows += f'<td style="padding:8px;border-bottom:1px solid #eee;">{day} {month_name}</td></tr>'

    return f"""
    <html><body style="font-family:Arial,sans-serif;padding:20px;">
    <h2>🎂 Birthdays in {month_name}</h2>
    <p>Here are the birthdays coming up this month:</p>
    <table style="border-collapse:collapse;width:100%;max-width:400px;">
    <tr style="background:#f5f5f5;"><th style="padding:8px;text-align:left;">Name</th>
    <th style="padding:8px;text-align:left;">Date</th></tr>
    {rows}
    </table>
    <p style="margin-top:20px;color:#666;">You'll get a reminder on each birthday at 6 AM ☀️</p>
    </body></html>
    """


def build_daily_email(birthdays: list) -> str:
    """Build HTML for daily reminder."""
    names_list = "".join(
        f'<li style="margin:8px 0;"><strong>{b["name"]}</strong></li>'
        for b in birthdays
    )
    return f"""
    <html><body style="font-family:Arial,sans-serif;padding:20px;">
    <h2>🎉 Birthday Today!</h2>
    <p>Don't forget to wish:</p>
    <ul>{names_list}</ul>
    <p style="margin-top:20px;">Send them a birthday message! 🎁🎈</p>
    <p style="color:#666;font-size:12px;">— Birthday Reminder Bot</p>
    </body></html>
    """


def run_daily():
    """Check all users' birthdays for today and send reminders."""
    supabase = get_supabase()
    today = datetime.now().strftime("%d-%m")

    print(f"📅 Checking birthdays for {today}...")

    # Get all birthdays matching today
    result = supabase.table("birthdays").select("*, user_id").eq("birthday", today).execute()
    todays_birthdays = result.data

    if not todays_birthdays:
        print("No birthdays today.")
        return

    # Group by user_id
    user_birthdays: dict = {}
    for b in todays_birthdays:
        uid = b["user_id"]
        if uid not in user_birthdays:
            user_birthdays[uid] = []
        user_birthdays[uid].append(b)

    # Get user emails and send reminders
    for user_id, birthdays in user_birthdays.items():
        # Get user email from auth
        user = supabase.auth.admin.get_user_by_id(user_id)
        if not user or not user.user:
            continue

        user_email = user.user.email
        names = ", ".join(b["name"] for b in birthdays)
        subject = f"🎉 Birthday Today: {names}"
        body = build_daily_email(birthdays)
        send_email(user_email, subject, body)


def run_monthly():
    """Send monthly summary to all users who have birthdays this month."""
    supabase = get_supabase()
    now = datetime.now()
    month = now.month
    month_str = f"-{month:02d}"  # e.g., "-08" for August
    month_name = now.strftime("%B")

    print(f"📋 Sending monthly summary for {month_name}...")

    # Get all birthdays this month (birthday field is DD-MM)
    result = supabase.table("birthdays").select("*, user_id").like("birthday", f"%{month_str}").execute()
    month_birthdays = result.data

    if not month_birthdays:
        print("No birthdays this month across all users.")
        return

    # Group by user_id
    user_birthdays: dict = {}
    for b in month_birthdays:
        uid = b["user_id"]
        if uid not in user_birthdays:
            user_birthdays[uid] = []
        user_birthdays[uid].append(b)

    # Send summary to each user
    for user_id, birthdays in user_birthdays.items():
        user = supabase.auth.admin.get_user_by_id(user_id)
        if not user or not user.user:
            continue

        user_email = user.user.email
        subject = f"🎂 {len(birthdays)} Birthday(s) in {month_name}"
        body = build_monthly_email(month_name, birthdays)
        send_email(user_email, subject, body)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_reminders.py [daily|monthly]")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "daily":
        run_daily()
    elif mode == "monthly":
        run_monthly()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
