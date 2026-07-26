import os
import requests
from bs4 import BeautifulSoup
import sys

def main():
    url = "https://hausandkinder.com/collections/double-bedsheet?filter.p.m.custom.thread_count=300+TC&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        sys.exit(1)

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
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            print("Telegram credentials not found in environment variables.")
            sys.exit(1)
            
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        names_str = "\n".join([f"- {name}" for name in product_names])
        message = f"Alert: Found {count} items (>= 3) on Haus and Kinder.\n\nProducts:\n{names_str}"
        
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        
        try:
            tg_response = requests.post(telegram_url, json=payload)
            tg_response.raise_for_status()
            print("Telegram notification sent successfully.")
        except requests.RequestException as e:
            print(f"Error sending Telegram notification: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
