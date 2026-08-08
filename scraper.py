import os
import requests
from bs4 import BeautifulSoup
import sys
import re

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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
            message = f"✅ Alert: Found {count} items (>= 3) on Haus and Kinder.\n\nProducts:\n{names_str}"
            send_telegram_message(message)
        else:
            print(f"ℹ️ Haus and Kinder Check: Only {count} items found (Threshold is 3). Waiting for restock...")
            
    except Exception as e:
        msg = f"⚠️ Error during Haus and Kinder check: {e}"
        print(msg)
        send_telegram_message(msg)

def check_zostel():
    print("--- Running Zostel Checks ---")
    
    targets = [
        {
            "name": "Zostel Varanasi",
            "url": "https://www.zostel.com/destination/varanasi/stay/zostel-varanasi-vrnh142/?checkin=2026-09-30&checkout=2026-10-04",
            "room_name": "Deluxe 4 Bed Mixed Dorm",
            "check_omission": False
        },
        {
            "name": "Zostel Sam Desert (Jaisalmer)",
            "url": "https://www.zostel.com/destination/jaisalmer/stay/zostel-sam-desert-jaisalmer-jslh187/?checkin=2026-09-30&checkout=2026-10-04",
            "room_name": "10 Bed Mixed Dorm with a porch (Mudhouse)",
            "check_omission": False
        }
    ]
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            for target in targets:
                print(f"Navigating to {target['name']}...")
                try:
                    page.goto(target['url'], wait_until="networkidle")
                    page.wait_for_timeout(5000)
                    
                    body_text = page.locator("body").inner_text()
                    
                    if target['check_omission']:
                        if "10 Bed" in body_text or target["room_name_alt"] in body_text:
                            print(f"Availability found for {target['name']}!")
                            
                            start_idx = body_text.find("10 Bed")
                            if start_idx == -1:
                                start_idx = body_text.find(target["room_name_alt"])
                                
                            price = "N/A"
                            if start_idx != -1:
                                room_text = body_text[start_idx:start_idx+1500]
                                price_match = re.search(r'₹\s*([0-9,]+)', room_text)
                                if price_match:
                                    price = price_match.group(1)
                                    
                            msg = (
                                f"🚨 <b>{target['name']} Alert!</b>\n\n"
                                f"The <b>10 Bed Mixed Dorm (Mudhouse)</b> is now available!\n"
                                f"💰 <b>Price per night:</b> ₹{price}\n\n"
                                f"Book here: <a href='{target['url']}'>Book Now</a>"
                            )
                            send_telegram_message(msg, parse_mode="HTML")
                        else:
                            print(f"ℹ️ {target['name']} Check: Target Room (10 Bed / Mudhouse) is omitted/sold out.")
                    else:
                        start_idx = body_text.find(target['room_name'])
                        if start_idx != -1:
                            room_text = body_text[start_idx:start_idx+1500]
                            
                            if "0 units" in room_text or "Bookings Not Open" in room_text or "❌" in room_text:
                                print(f"ℹ️ {target['name']} Check: Room '{target['room_name']}' is still sold out or unavailable for your dates.")
                            else:
                                print(f"Availability found for {target['name']}!")
                                
                                price_match = re.search(r'₹\s*([0-9,]+)', room_text)
                                price = price_match.group(1) if price_match else "N/A"
                                
                                msg = (
                                    f"🚨 <b>{target['name']} Alert!</b>\n\n"
                                    f"The <b>{target['room_name']}</b> is now available!\n"
                                    f"💰 <b>Price per night:</b> ₹{price}\n\n"
                                    f"Book here: <a href='{target['url']}'>Book Now</a>"
                                )
                                send_telegram_message(msg, parse_mode="HTML")
                        else:
                            msg = f"⚠️ Error: Room '{target['room_name']}' not found in the DOM for {target['name']}. Layout might have changed."
                            print(msg)
                            send_telegram_message(msg)
                            
                except Exception as e:
                    msg = f"⚠️ Error checking {target['name']}: {e}"
                    print(msg)
                    send_telegram_message(msg)
                
            browser.close()

    except Exception as e:
        msg = f"⚠️ Critical Error during Zostel checks: {e}"
        print(msg)
        send_telegram_message(msg)

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Warning: Telegram credentials missing. Alerts will not be sent.")
        
    check_haus_and_kinder()
    print("")
    check_zostel()

if __name__ == "__main__":
    main()
