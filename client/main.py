import os
import time
import json
import requests
import psutil
from datetime import datetime,timezone

# Configuration
API_URL = "http://localhost:5000/api/health"  # Replace with your actual backend URL
CACHE_FILE = "cache.json"
SLEEP_INTERVAL = 10  # Interval in seconds between checks

def collect_data():
    """Collect system health data."""
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage('/')._asdict(),
        "net_io": psutil.net_io_counters()._asdict()
    }
    return data

def load_cache():
    """Load cached data from file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Cache file is corrupted. Starting fresh.")
                return None
    return None

def save_cache(data):
    """Save data to cache file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def has_changes(current, cached):
    """Check if current data differs from cached data."""
    if not cached:
        return True
    return current != cached

def send_data(data):
    """Send data to the backend API."""
    try:
        response = requests.post(API_URL, json=data)
        if response.status_code == 200:
            print(f"Data reported at {data['timestamp']}")
            return True
        else:
            print(f"Failed to report data: {response.status_code} - {response.text}")
            return False
    except requests.RequestException as e:
        print(f"Error sending data: {e}")
        return False

def run_daemon():
    """Run the monitoring daemon."""
    print("Starting system health monitoring...")
    cached_data = load_cache()
    while True:
        current_data = collect_data()
        if has_changes(current_data, cached_data):
            print("Change detected. Sending data...")
            if send_data(current_data):
                save_cache(current_data)
                cached_data = current_data
        else:
            print("No change detected.")
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    run_daemon()
