import datetime
import pytz
import time

def is_market_open_ist():
    return True

def main_loop():
    print("🚀 US Equities AI Trader Initialized")
    while True:
        if is_market_open_ist():
            print(f"[{datetime.datetime.now()}] Market Window Active. Scanning...")
        else:
            print(f"[{datetime.datetime.now()}] Outside Trading Window (9:30 AM - 1:00 PM IST). Sleeping...")
        time.sleep(60)

if __name__ == '__main__':
    main_loop()
