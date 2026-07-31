import os
import requests
from bs4 import BeautifulSoup
import sys

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ZOSTEL_API_URL = "https://api.zostel.com/api/v1/stay/offered/rooms/"
ZOSTEL_PARAMS = {
    "checkin": "2026-09-30",
    "checkout": "2026-10-04",
    "property_code": "zostel-varanasi-vrnh142"
}
ZOSTEL_BOOKING_URL = "http://zostel.com/destination/varanasi/stay/zostel-varanasi-vrnh142?checkin=2026-09-30&checkout=2026-10-04"
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
        
        # Count the number of elements with the CSS class .card--product
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
            
            # Clean up the name if it has the site suffix
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(ZOSTEL_API_URL, params=ZOSTEL_PARAMS, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        rooms = data.get('rooms', [])
        found_room = False
        
        for room in rooms:
            if room.get('id') == ZOSTEL_TARGET_ROOM_ID:
                found_room = True
                availability = room.get('availability', {})
                is_available = availability.get('available', False)
                units = availability.get('units', 0)
                price = room.get('base_price_per_night', 'N/A')
                
                if is_available and units > 0:
                    print(f"Availability found! {units} beds at ₹{price}.")
                    msg = (
                        f"🚨 <b>Zostel Varanasi Alert!</b>\n\n"
                        f"The <b>Deluxe 4 Bed Mixed Dorm</b> is now available!\n"
                        f"🛏️ <b>Beds available:</b> {units}\n"
                        f"💰 <b>Price per night:</b> ₹{price}\n\n"
                        f"Book here: <a href='{ZOSTEL_BOOKING_URL}'>Zostel Varanasi</a>"
                    )
                    send_telegram_message(msg, parse_mode="HTML")
                else:
                    print(f"Room ID {ZOSTEL_TARGET_ROOM_ID} is still sold out or unavailable.")
                break
                
        if not found_room:
            print(f"Room ID {ZOSTEL_TARGET_ROOM_ID} not found in the response.")

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
