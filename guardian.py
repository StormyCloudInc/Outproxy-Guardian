import sqlite3
import requests
import time
import threading
from datetime import datetime, timedelta
import configparser
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

# --- Configuration ---
CONFIG_FILE = 'config.ini'
DATABASE_FILE = 'proxy_status.db'
# Get the absolute path of the directory where the script is running
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    """Loads configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(BASE_DIR, CONFIG_FILE)
    if not os.path.exists(config_path):
        print(f"Warning: {CONFIG_FILE} not found. Using default settings.")
        # Create default config content
        config['proxies'] = {'example-proxy': 'http://127.0.0.1:8080'}
        config['user_test'] = {'i2p-user-test': 'http://127.0.0.1:4444'}
        config['settings'] = {
            'check_interval_seconds': '300',
            'retest_delay_seconds': '30',
            'discord_webhook_url': 'YOUR_DISCORD_WEBHOOK_URL'
        }
        config['api'] = {'url': 'https://api.ipify.org?format=json'}
    else:
        config.read(config_path)

    proxies = []
    if 'proxies' in config:
        for name, url in config.items('proxies'):
            proxies.append({'name': name, 'url': url})
    
    user_tests = []
    if 'user_test' in config:
        for name, url in config.items('user_test'):
            user_tests.append({'name': name, 'url': url})

    settings = config['settings']
    api_url = config.get('api', 'url', fallback='https://api.ipify.org?format=json')

    return {
        'proxies': proxies,
        'user_tests': user_tests,
        'check_interval': settings.getint('check_interval_seconds', 300),
        'retest_delay': settings.getint('retest_delay_seconds', 30),
        'discord_webhook': settings.get('discord_webhook_url', 'YOUR_DISCORD_WEBHOOK_URL'),
        'api_url': api_url
    }

# --- Flask Web Server Setup ---
app = Flask(__name__)
CORS(app) 

# --- Route to serve the frontend ---
@app.route('/')
def serve_index():
    """Serves the index.html file for the root URL."""
    # Using an absolute path to the project directory to prevent pathing issues.
    return send_from_directory(BASE_DIR, 'index.html')


# --- API Routes ---
@app.route('/api/status', methods=['GET'])
def get_status():
    db_path = os.path.join(BASE_DIR, DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    proxies_data = {}
    c.execute("SELECT * FROM uptime_stats")
    stats_rows = c.fetchall()
    stats_map = {row['proxy_name']: dict(row) for row in stats_rows}
    c.execute("""
        SELECT a.* FROM status_history a
        INNER JOIN (
            SELECT proxy_name, MAX(id) as max_id FROM status_history GROUP BY proxy_name
        ) b ON a.proxy_name = b.proxy_name AND a.id = b.max_id
    """)
    latest_checks = c.fetchall()
    for row in latest_checks:
        proxy_name = row['proxy_name']
        stats = stats_map.get(proxy_name)
        if not stats: continue
        uptime_percentage = (stats['successful_checks'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 100
        first_seen_dt = datetime.strptime(stats['first_seen'], '%Y-%m-%d %H:%M:%S.%f')
        uptime_duration = datetime.utcnow() - first_seen_dt
        proxies_data[proxy_name] = {
            'name': proxy_name, 'status': row['status'], 'last_checked': row['timestamp'],
            'last_ip': row['ip_address'], 'uptime_percentage': round(uptime_percentage, 2),
            'uptime_duration_days': uptime_duration.days, 'uptime_duration_seconds': uptime_duration.seconds,
            'total_checks': stats['total_checks']
        }
    conn.close()
    return jsonify(list(proxies_data.values()))

@app.route('/api/history/<proxy_name>', methods=['GET'])
def get_history(proxy_name):
    db_path = os.path.join(BASE_DIR, DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT timestamp, response_time FROM status_history WHERE proxy_name = ? AND status = 'online' ORDER BY timestamp DESC LIMIT 100",
        (proxy_name,)
    )
    history_rows = c.fetchall()
    conn.close()
    return jsonify([dict(row) for row in reversed(history_rows)])

# --- Main Application ---
config = load_config()
ALL_PROXIES = config['proxies'] + config['user_tests']
CHECK_INTERVAL_SECONDS = config['check_interval']
RETEST_DELAY_SECONDS = config['retest_delay']
DISCORD_WEBHOOK_URL = config['discord_webhook']
API_URL = config['api_url']

def setup_database():
    db_path = os.path.join(BASE_DIR, DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS status_history (id INTEGER PRIMARY KEY, proxy_name TEXT, timestamp DATETIME, status TEXT, response_time REAL, ip_address TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS uptime_stats (proxy_name TEXT PRIMARY KEY, total_checks INTEGER, successful_checks INTEGER, first_seen DATETIME)''')
    conn.commit()
    conn.close()

def check_proxy(proxy):
    proxies = {'http': proxy['url'], 'https': proxy['url']}
    start_time = time.time()
    try:
        # Increased timeout to 30 seconds for better reliability over I2P
        response = requests.get(API_URL, proxies=proxies, timeout=30)
        response_time_ms = (time.time() - start_time) * 1000
        if response.status_code == 200:
            ip_address = response.json().get('ip')
            return {'status': 'online', 'response_time': response_time_ms, 'ip': ip_address}
        else:
            return {'status': 'offline', 'response_time': response_time_ms, 'ip': None}
    except requests.exceptions.RequestException as e:
        response_time_ms = (time.time() - start_time) * 1000
        # Added more detailed error logging
        print(f"Error checking {proxy['name']}. Type: {type(e).__name__}, Details: {e}")
        return {'status': 'offline', 'response_time': response_time_ms, 'ip': None}

def record_status(proxy_name, result):
    db_path = os.path.join(BASE_DIR, DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    now = datetime.utcnow()
    c.execute("INSERT INTO status_history (proxy_name, timestamp, status, response_time, ip_address) VALUES (?, ?, ?, ?, ?)",
              (proxy_name, now, result['status'], result['response_time'], result['ip']))
    c.execute("SELECT * FROM uptime_stats WHERE proxy_name = ?", (proxy_name,))
    stats = c.fetchone()
    if stats is None:
        c.execute("INSERT INTO uptime_stats (proxy_name, total_checks, successful_checks, first_seen) VALUES (?, 1, ?, ?)",
                  (proxy_name, 1 if result['status'] == 'online' else 0, now))
    else:
        successful_checks = stats[2] + (1 if result['status'] == 'online' else 0)
        c.execute("UPDATE uptime_stats SET total_checks = total_checks + 1, successful_checks = ? WHERE proxy_name = ?",
                  (successful_checks, proxy_name))
    conn.commit()
    conn.close()

def send_discord_alert(proxy_name):
    """Sends an alert to the configured Discord webhook."""
    if DISCORD_WEBHOOK_URL == 'YOUR_DISCORD_WEBHOOK_URL' or not DISCORD_WEBHOOK_URL:
        print(f"ALERT: {proxy_name} is confirmed to be offline. (Discord webhook not configured)")
        return
    data = {
        "content": f":rotating_light: **Proxy Alert** :rotating_light:",
        "embeds": [{"title": "Proxy Offline", "description": f"The proxy `{proxy_name}` has been confirmed to be offline.","color": 15158332, "timestamp": datetime.utcnow().isoformat()}]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord alert: {e}")

def run_checks():
    """Main loop to run checks for all configured proxies."""
    print("--- Starting Proxy Status Checks ---")
    if not ALL_PROXIES:
        print("No proxies found in config.ini. Please add your proxies.")
        return
    for proxy in ALL_PROXIES:
        print(f"Checking {proxy['name']}...")
        result = check_proxy(proxy)
        if result['status'] == 'offline':
            print(f"{proxy['name']} appears to be offline. Retesting in {RETEST_DELAY_SECONDS} seconds...")
            time.sleep(RETEST_DELAY_SECONDS)
            result = check_proxy(proxy)
            if result['status'] == 'offline':
                print(f"CONFIRMED: {proxy['name']} is offline.")
                record_status(proxy['name'], result)
                send_discord_alert(proxy['name'])
            else:
                print(f"RECOVERY: {proxy['name']} is back online after retest.")
                record_status(proxy['name'], result)
        else:
            print(f"{proxy['name']} is online. IP: {result['ip']}, Response Time: {result['response_time']:.2f}ms")
            record_status(proxy['name'], result)

def main_loop():
    while True:
        run_checks()
        print(f"\n--- Checks complete. Waiting {CHECK_INTERVAL_SECONDS} seconds for the next run. ---\n")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == '__main__':
    setup_database()
    checker_thread = threading.Thread(target=main_loop, daemon=True)
    checker_thread.start()
    print("--- Starting Flask API server on http://0.0.0.0:5000 ---")
    print("--- Access the dashboard at http://<YOUR_SERVER_IP>:5000 ---")
    app.run(host='0.0.0.0', port=5000)
