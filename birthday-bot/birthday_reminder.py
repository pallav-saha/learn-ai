"""
Birthday Reminder Bot

Sends email reminders for upcoming birthdays:
1. On the 1st of every month — lists all birthdays that month
2. On the day of a birthday at 6 AM — reminds you to wish them

Uses Gmail SMTP (free) with an App Password.
Designed to run via GitHub Actions on a cron schedule.
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load .env file from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- Configuration ---
# These come from .env file locally, or GitHub Secrets in production
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

BIRTHDAYS_FILE = os.path.join(os.path.dirname(__file__), "birthdays.json")

# --- Helpers ---


def load_birthdays():
    """Load birthdays from JSON file."""
    with open(BIRTHDAYS_FILE, "r") as f:
        return json.load(f)


def get_month_birthdays(birthdays, month):
    """Get all birthdays in a given month."""
    return [
        b for b in birthdays
        if int(b["birthday"].split("-")[1]) == month
    ]


def get_todays_birthdays(birthdays):
    """Get birthdays that match today's date (DD-MM)."""
    today = datetime.now().strftime("%d-%m")
    return [b for b in birthdays if b["birthday"] == today]


def send_email(subject, body_html):
    """Send an email via Gmail SMTP."""
    if not SENDER_APP_PASSWORD:
        print("ERROR: SENDER_APP_PASSWORD not set in environment variables.")
        print("Set it as a GitHub Secret or export it locally for testing.")
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"✅ Email sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        sys.exit(1)


# --- Email Templates ---


def build_monthly_summary_email(month_name, birthdays):
    """Build HTML email for monthly birthday summary."""
    rows = ""
    # Sort by day
    sorted_bdays = sorted(birthdays, key=lambda b: int(b["birthday"].split("-")[0]))

    for b in sorted_bdays:
        day = b["birthday"].split("-")[0]
        rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{b['name']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{day} {month_name}</td>
        </tr>
        """

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>🎂 Birthdays in {month_name}</h2>
        <p>Here are the birthdays coming up this month:</p>
        <table style="border-collapse: collapse; width: 100%; max-width: 400px;">
            <tr style="background-color: #f5f5f5;">
                <th style="padding: 8px; text-align: left;">Name</th>
                <th style="padding: 8px; text-align: left;">Date</th>
            </tr>
            {rows}
        </table>
        <p style="margin-top: 20px; color: #666;">
            You'll get a reminder on each birthday at 6 AM ☀️
        </p>
    </body>
    </html>
    """
    return html


def build_daily_reminder_email(birthdays):
    """Build HTML email for today's birthday reminder."""
    names = ", ".join(b["name"] for b in birthdays)
    names_list = "".join(
        f"<li style='margin: 8px 0;'><strong>{b['name']}</strong></li>"
        for b in birthdays
    )

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>🎉 Birthday Today!</h2>
        <p>Don't forget to wish:</p>
        <ul>
            {names_list}
        </ul>
        <p style="margin-top: 20px;">
            Send them a birthday message! 🎁🎈
        </p>
        <p style="color: #666; font-size: 12px;">
            — Birthday Reminder Bot
        </p>
    </body>
    </html>
    """
    return html


# --- Main Logic ---


def run_monthly_summary():
    """Send monthly summary of all birthdays this month."""
    birthdays = load_birthdays()
    now = datetime.now()
    month = now.month
    month_name = now.strftime("%B")  # e.g., "August"

    month_birthdays = get_month_birthdays(birthdays, month)

    if not month_birthdays:
        print(f"No birthdays in {month_name}. No email sent.")
        return

    print(f"📋 {len(month_birthdays)} birthday(s) in {month_name}")
    subject = f"🎂 {len(month_birthdays)} Birthday(s) in {month_name}"
    body = build_monthly_summary_email(month_name, month_birthdays)
    send_email(subject, body)


def run_daily_reminder():
    """Send reminder if today is someone's birthday."""
    birthdays = load_birthdays()
    todays = get_todays_birthdays(birthdays)

    if not todays:
        print("No birthdays today. No email sent.")
        return

    names = ", ".join(b["name"] for b in todays)
    print(f"🎉 Today's birthday(s): {names}")
    subject = f"🎉 Birthday Today: {names}"
    body = build_daily_reminder_email(todays)
    send_email(subject, body)


if __name__ == "__main__":
    # Determine which mode to run based on command-line argument
    if len(sys.argv) < 2:
        print("Usage: python birthday_reminder.py [monthly|daily]")
        print("  monthly  — Send summary of all birthdays this month (run on 1st)")
        print("  daily    — Send reminder if today is someone's birthday (run daily at 6 AM)")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "monthly":
        run_monthly_summary()
    elif mode == "daily":
        run_daily_reminder()
    else:
        print(f"Unknown mode: {mode}. Use 'monthly' or 'daily'.")
        sys.exit(1)
