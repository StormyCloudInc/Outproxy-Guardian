# I2P Outproxy Guardian

A simple, self-hosted status page and monitoring tool for I2P outproxies. This application periodically checks the health of HAProxy frontends and Tinyproxy backends, provides a live web dashboard with uptime statistics, and sends alerts to Discord when a proxy is confirmed to be offline.

![Dashboard Screenshot](https://i.imgur.com/GqSD81H.png) 


## Features

-   **Live Web Dashboard**: A clean, modern interface to view the status of all monitored proxies.
-   **Uptime Statistics**: Tracks and displays uptime percentage and total uptime duration for each proxy.
-   **Response Time Graphs**: Visualize historical response times for each proxy to spot performance trends.
-   **Smart Alerting**: Implements a re-test delay to prevent false positives from temporary network lag before sending an alert.
-   **Discord Notifications**: Sends an alert to a configured Discord webhook when a proxy is confirmed to be offline.
-   **Prioritized View**: Automatically sorts offline nodes to the top of the dashboard for immediate visibility.
-   **External Configuration**: All settings, including proxy lists and secrets, are managed in an external `config.ini` file, keeping the core script clean and shareable.

## Setup & Installation

### 1. Requirements

-   Python 3.6+
-   The following Python libraries: `requests`, `Flask`, `Flask-Cors`

You can install the required libraries using pip:
```bash
pip install requests Flask Flask-Cors
```

### 2. Configuration

All application settings are managed in the `config.ini` file. Create this file in the same directory as the `guardian.py` script.

Below is an example configuration. You **must** edit the URLs and your Discord webhook to match your setup.

```ini
[proxies]
# Add your HAProxy frontends and Tinyproxy backends here
# The format is: name = url
haproxy-1 = [http://127.0.0.1:8080](http://127.0.0.1:8080)
haproxy-2 = [http://127.0.0.1:8081](http://127.0.0.1:8081)
tinyproxy-1 = [http://127.0.0.1:8888](http://127.0.0.1:8888)
tinyproxy-2 = [http://127.0.0.1:8889](http://127.0.0.1:8889)

[user_test]
# This is a special test to simulate a user connection through the I2P network
# This can be the same as one of your haproxy frontends
i2p-user-test = [http://127.0.0.1:4444](http://127.0.0.1:4444)

[settings]
# Interval in seconds between each check run
check_interval_seconds = 300

# Delay in seconds before re-testing a failed proxy
retest_delay_seconds = 30

# Your Discord webhook URL for alerts.
# IMPORTANT: Keep this URL secret!
discord_webhook_url = YOUR_DISCORD_WEBHOOK_URL

[api]
# The API used to verify the proxy is working and get the exit IP
url = [https://api.ipify.org?format=json](https://api.ipify.org?format=json)
```

## Running the Application

1.  Ensure your `config.ini` file is correctly configured.
2.  Run the main Python script from your terminal:
    ```bash
    python3 guardian.py
    ```
3.  The script will start the background checker and the web server. You will see output like this:
    ```
    --- Starting Flask API server on [http://127.0.0.1:5000](http://127.0.0.1:5000) ---
    --- Access the dashboard at [http://127.0.0.1:5000](http://127.0.0.1:5000) ---
    ```
4.  Open your web browser and navigate to `http://127.0.0.1:5000` to view the dashboard.

## Security Note: `.gitignore`

Your `config.ini` file contains sensitive information (your Discord webhook URL). If you are using Git for version control, you should **NEVER** commit this file. Create a `.gitignore` file in your project directory and add the following lines to it:

```
# Ignore sensitive configuration and the database file
config.ini
proxy_status.db

# Ignore Python's cache files
__pycache__/