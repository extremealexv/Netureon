from flask import Flask, render_template
import psycopg2
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

@app.route('/')
def main_page():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT device_name, mac_address, device_type, notes, last_seen, last_ip
        FROM known_devices
        ORDER BY last_seen DESC
    """)
    known_hosts = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('main.html', hosts=known_hosts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
