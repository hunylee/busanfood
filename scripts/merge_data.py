import csv
import sqlite3
import urllib.request
import json
import os

# Constants
CSV_PATH = "/Users/terrylee/Downloads/부산광역시_택슐랭 선정 식당_20250528.csv"
DB_PATH = "busan_food.db"

URLS = {
    "kr": "https://api.koreaconnect.kr/01/1/2603101713597416530PDP/CULTR/6260000/FoodService/getFoodKr",
    "en": "https://api.koreaconnect.kr/01/1/2603101713597416530PDP/CULTR/6260000/FoodService/getFoodEn",
    "ja": "https://api.koreaconconnect.kr/01/1/2603101713597416530PDP/CULTR/6260000/FoodService/getFoodJa"
}

def fetch_api_data(url):
    try:
        # Using urllib to avoid dependency issues in this environment
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def setup_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            address TEXT,
            recommended_menu TEXT,
            latitude REAL,
            longitude REAL,
            source TEXT,
            lang TEXT
        )
    ''')
    conn.commit()

def process_csv(conn):
    cursor = conn.cursor()
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
        return
        
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cursor.execute('''
                    INSERT INTO restaurants (name, category, address, recommended_menu, latitude, longitude, source, lang)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['식당명'], 
                    row['분류'], 
                    row['주소'], 
                    row['추천메뉴'], 
                    float(row['위도']), 
                    float(row['경도']), 
                    'CSV',
                    'ko'
                ))
            except Exception as e:
                print(f"Error processing CSV row: {e}")
    conn.commit()

def process_api(conn, lang, url):
    data = fetch_api_data(url)
    if not data:
        return
    
    cursor = conn.cursor()
    # Since I don't know the exact JSON structure, I'll attempt to find a list of items.
    # Common patterns: 'items', 'content', or just a list itself.
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Try common keys for lists in API responses
        for key in ['items', 'content', 'data', 'list']:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
    
    if not items:
        print(arg := f"No items found in API response for {lang}")
        return

    for item in items:
        try:
            # We'll use generic mapping based on what we expect from a FoodService API
            # This is highly speculative without seeing the actual JSON structure.
            name = item.get('name') or item.get('foodName') or item.get('title')
            category = item.get('category') or item.get('type')
            address = item.get('address') or item.get('location')
            menu = item.get('menu') or item.get('recommendedMenu') or ""
            lat = item.get('latitude') or item.get('lat') or 0.0
            lng = item.get('longitude') or item.get('lng') or 0.0
            
            if name:
                cursor.execute('''
                    INSERT INTO restaurants (name, category, address, recommended_menu, latitude, longitude, source, lang)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, category, address, menu, float(lat), float(lng), 'API', lang))
        except Exception as e:
            print(f"Error processing API item in {lang}: {e}")
            
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    
    print("Processing CSV...")
    process_csv(conn)
    
    for lang, url in URLS.items():
        print(f"Processing API ({lang})...")
        process_api(conn, lang, url)
    
    print("Done.")
    conn.close()

if __name__ == "__main__":
    main()
