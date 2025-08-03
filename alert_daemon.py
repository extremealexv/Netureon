import psycopg2
import smtplib
import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database config
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Email config
EMAIL_FROM = "alexander.vasilyev83@gmail.com"
EMAIL_TO = "aleksandr@vasilyev.tech"
EMAIL_SUBJECT = "Intrusion Alert"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "alexander.vasilyev83@gmail.com"
SMTP_PASSWORD = "ghyw apii fowv lwgf"

# Telegram config
# TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
# TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

def send_email(body):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            message = f"Subject:{EMAIL_SUBJECT}\n\n{body}"
            server.sendmail(EMAIL_FROM, EMAIL_TO, message)
    except Exception as e:
        print(f"Email error: {e}")

# def send_telegram(message):
#     url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
#     payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
#     try:
#         requests.post(url, data=payload)
#     except Exception as e:
#         print(f"Telegram error: {e}")

def check_alerts():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id, device_id, detected_at FROM alerts")
        rows = cursor.fetchall()

        for alert_id, device_id, timestamp in rows:
            message = f" New Device Detected: {device_id}\n Time: {timestamp}"
            send_email(message)
            # send_telegram(message)
            cursor.execute("DELETE FROM alerts WHERE id = %s", (alert_id,))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    while True:
        check_alerts()
        time.sleep(10)  # Check every 10 seconds
