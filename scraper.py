import os
import requests
from bs4 import BeautifulSoup
import sys
import re

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ZOSTEL_BOOKING_URL = "https://www.zostel.com/destination/varanasi/stay/zostel-varanasi-vrnh142/?checkin=2026-09-30&checkout=2026-10-04"
ZOSTEL_TARGET_ROOM_ID = 1563

def send_telegram_message(message, parse_mode=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing, cannot send message.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
        
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def check_haus_and_kinder():
    print("--- Running Haus and Kinder Check ---")
    url = "https://hausandkinder.com/collections/double-bedsheet?filter.p.m.custom.thread_count=300+TC&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        items = soup.select(".card--product")
        count = len(items)
        print(f"Found {count} .card--product elements.")

        product_names = []
        for item in items:
            title_element = item.select_one('h2, h3')
            if title_element:
                name = title_element.text.strip()
            else:
                img = item.select_one('img')
                name = img.get('alt').strip() if img and img.get('alt') else "Unknown Product"
            
            name = name.split(" - ")[0].strip()
            product_names.append(name)

        if count >= 3:
            names_str = "\n".join([f"- {name}" for name in product_names])
            message = f"Alert: Found {count} items (>= 3) on Haus and Kinder.\n\nProducts:\n{names_str}"
            send_telegram_message(message)
    except Exception as e:
        print(f"Error during Haus and Kinder check: {e}")

def check_zostel():
    print("--- Running Zostel Varanasi Check ---")
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            print(f"Navigating to {ZOSTEL_BOOKING_URL}")
            page.goto(ZOSTEL_BOOKING_URL, wait_until="networkidle")
            page.wait_for_timeout(5000)
            
            body_text = page.locator("body").inner_text()
            
            start_idx = body_text.find("Deluxe 4 Bed Mixed Dorm")
            if start_idx != -1:
                room_text = body_text[start_idx:start_idx+1500]
                
                if "0 units" in room_text or "Bookings Not Open" in room_text or "❌" in room_text:
                    print(f"Room ID {ZOSTEL_TARGET_ROOM_ID} (Deluxe 4 Bed Mixed Dorm) is still sold out or unavailable.")
                else:
                    print("Availability found! Sending Telegram alert.")
                    
                    price_match = re.search(r'₹\s*([0-9,]+)', room_text)
                    price = price_match.group(1) if price_match else "N/A"
                    
                    msg = (
                        f"🚨 <b>Zostel Varanasi Alert!</b>\n\n"
                        f"The <b>Deluxe 4 Bed Mixed Dorm</b> is now available!\n"
                        f"💰 <b>Price per night:</b> ₹{price}\n\n"
                        f"Book here: <a href='{ZOSTEL_BOOKING_URL}'>Zostel Varanasi</a>"
                    )
                    send_telegram_message(msg, parse_mode="HTML")
            else:
                print(f"Room 'Deluxe 4 Bed Mixed Dorm' not found in the DOM. Layout might have changed.")
                
            browser.close()

    except Exception as e:
        print(f"Error during Zostel check: {e}")

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Warning: Telegram credentials missing. Alerts will not be sent.")
        
    check_haus_and_kinder()
    print("")
    check_zostel()

if __name__ == "__main__":
    main()
