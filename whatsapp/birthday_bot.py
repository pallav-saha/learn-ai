"""
WhatsApp Birthday Bot
- Reads birthdays from a JSON file
- Checks if today is anyone's birthday
- Generates a unique message using Groq LLM (OpenAI-compatible)
- Sends the message via Selenium (WhatsApp Web)

Prerequisites:
- You must be logged into WhatsApp Web in Chrome
- Chrome and chromedriver must be installed
- Run this script daily (manually or via cron/scheduler)
"""

import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from parent directory's .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Configuration ---
JSON_FILE = os.path.join(os.path.dirname(__file__), "birthdays.json")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "openai/gpt-oss-120b"

# Chrome user data directory — keeps WhatsApp Web logged in between runs
CHROME_PROFILE_DIR = os.path.expanduser("~/whatsapp-chrome-profile")


def get_groq_client():
    """Initialize Groq client using OpenAI-compatible API."""
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not found in .env file")
        sys.exit(1)

    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )


def read_birthdays(file_path):
    """Read birthday data from JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def get_todays_birthdays(birthdays):
    """Filter people whose birthday is today."""
    today = datetime.now().strftime("%d-%m")  # DD-MM
    return [b for b in birthdays if b["birthday"] == today]


def generate_birthday_message(client, name):
    """Generate a unique birthday message using Groq LLM."""
    prompt = f"""Generate a warm, fun, and unique happy birthday message for {name}. 
    Keep it short (2-3 sentences max). Make it personal and heartfelt. 
    Don't use generic templates — be creative each time.
    Just return the message text, nothing else."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly person writing birthday wishes for friends and colleagues. Be warm, creative, and unique every time.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=1.0,  # high temperature for variety
            max_tokens=150,
        )

        message = response.choices[0].message.content
        if not message or not message.strip():
            print("   ⚠️  LLM returned empty message, using fallback")
            return f"Happy Birthday, {name}! 🎂 Wishing you an amazing year ahead!"
        return message.strip()

    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        return f"Happy Birthday, {name}! 🎂 Wishing you an amazing year ahead!"


def send_whatsapp_message(phone, message):
    """Send a WhatsApp message using Selenium + Chrome."""
    # Set up Chrome with a persistent profile (so WhatsApp Web stays logged in)
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Open WhatsApp Web with the phone number and message pre-filled
        encoded_message = quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        driver.get(url)

        # Wait for the send button to appear (means WhatsApp Web is loaded and message is ready)
        print("   ⏳ Waiting for WhatsApp Web to load...")
        send_button = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Send"]'))
        )

        # Click send
        time.sleep(2)  # small extra wait for stability
        send_button.click()
        print("   📤 Message sent!")

        time.sleep(3)  # wait for message to actually deliver
        return True

    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    finally:
        driver.quit()


def main():
    print("=" * 50)
    print("🎂 WhatsApp Birthday Bot")
    print("=" * 50)
    print(f"Date: {datetime.now().strftime('%d-%m-%Y')}")
    print()

    # Read JSON
    birthdays = read_birthdays(JSON_FILE)
    print(f"📋 Loaded {len(birthdays)} contacts from birthdays.json")

    # Check today's birthdays
    todays = get_todays_birthdays(birthdays)

    if not todays:
        print("🚫 No birthdays today. Nothing to send.")
        return

    print(f"🎉 {len(todays)} birthday(s) today!\n")

    # Initialize Groq client
    client = get_groq_client()

    # Process each birthday
    for person in todays:
        name = person["name"]
        phone = person["phone"]

        print(f"👤 {name} ({phone})")

        # Generate unique message
        message = generate_birthday_message(client, name)
        print(f"   Message: {message}")

        # Send via WhatsApp
        print("   Sending via WhatsApp...")
        success = send_whatsapp_message(phone, message)

        if success:
            print("   ✅ Sent successfully!")
        else:
            print("   ❌ Failed to send")

        print()

    print("=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
