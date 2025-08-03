from flask import Flask, render_template, request, redirect, url_for
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



@app.route('/review')
def review_page():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT device_name, mac_address, device_type, last_seen, last_ip, notes
        FROM new_devices
        ORDER BY last_seen DESC
    """)
    new_devices = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('review.html', new_devices=new_devices)


@app.route('/add_known', methods=['POST'])
def add_to_known():
    selected = request.form.getlist('selected')

    if not selected:
        return redirect(url_for('review_page'))

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for mac in selected:
        cur.execute("""
            INSERT INTO known_devices (device_name, mac_address, device_type, last_seen, last_ip, notes)
            SELECT device_name, mac_address, device_type, last_seen, last_ip, notes
            FROM new_devices
            WHERE mac_address = %s
        """, (mac,))
        cur.execute("DELETE FROM new_devices WHERE mac_address = %s", (mac,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('main_page'))
