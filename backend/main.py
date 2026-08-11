import json
import os
import sqlite3
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "app.db")
DB_PATH = os.environ.get("DB_PATH", DEFAULT_DB_PATH)

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS favorites (
          restaurant_id TEXT PRIMARY KEY,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS search_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          query TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS preferences (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS official_translations (
          lang TEXT NOT NULL,
          source_id TEXT NOT NULL,
          source_name TEXT NOT NULL DEFAULT '',
          name TEXT NOT NULL DEFAULT '',
          district TEXT NOT NULL DEFAULT '',
          address TEXT NOT NULL DEFAULT '',
          address_detail TEXT NOT NULL DEFAULT '',
          menu TEXT NOT NULL DEFAULT '',
          description TEXT NOT NULL DEFAULT '',
          hours TEXT NOT NULL DEFAULT '',
          phone TEXT NOT NULL DEFAULT '',
          homepage_url TEXT NOT NULL DEFAULT '',
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (lang, source_id)
        );
        """)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class SearchBody(BaseModel):
    query: str
class PreferenceBody(BaseModel):
    key: str
    value: str
BASE_SELECT = """
SELECT
  e.UC_SEQ AS id,
  COALESCE(NULLIF(TRIM(e.MAIN_TITLE), ''), NULLIF(TRIM(e.TITLE), ''), '이름 미상') AS name,
  TRIM(COALESCE(e.GUGUN_NM, '')) AS district,
  TRIM(COALESCE(e.ADDR1, '')) AS address,
  TRIM(COALESCE(e.ADDR2, '')) AS address_detail,
  TRIM(COALESCE(e.RPRSNTV_MENU, '')) AS menu,
  TRIM(COALESCE(e.ITEMCNTNTS, '')) AS description,
  TRIM(COALESCE(e.CNTCT_TEL, '')) AS phone,
  TRIM(COALESCE(e.USAGE_DAY_WEEK_AND_TIME, '')) AS hours,
  TRIM(COALESCE(e.HOMEPAGE_URL, '')) AS homepage_url,
  TRIM(COALESCE(e.MAIN_IMG_THUMB, '')) AS image_url,
  CAST(e.LAT AS REAL) AS lat,
  CAST(e.LNG AS REAL) AS lng,
  CASE WHEN f.restaurant_id IS NULL THEN 0 ELSE 1 END AS favorite
FROM external_data e
LEFT JOIN favorites f ON f.restaurant_id = e.UC_SEQ
WHERE TRIM(COALESCE(e.UC_SEQ, '')) <> ''
  AND TRIM(COALESCE(e.LAT, '')) <> ''
  AND TRIM(COALESCE(e.LNG, '')) <> ''
"""
@app.get('/api/health')
def health():
    return {'ok': True}
@app.get('/api/restaurants')
def restaurants(
    query: str = '',
    favorites_only: bool = False,
    limit: int = Query(default=500, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    keywords = f"%{query.strip()}%"
    sql = BASE_SELECT
    params = []
    if query.strip():
        sql += """ AND (
          e.MAIN_TITLE LIKE ? OR e.TITLE LIKE ? OR e.GUGUN_NM LIKE ? OR
          e.ADDR1 LIKE ? OR e.RPRSNTV_MENU LIKE ? OR e.ITEMCNTNTS LIKE ?
        )"""
        params.extend([keywords] * 6)
    if favorites_only:
        sql += " AND f.restaurant_id IS NOT NULL"
    sql += " ORDER BY e.GUGUN_NM COLLATE NOCASE, e.MAIN_TITLE COLLATE NOCASE LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {'items': [dict(row) for row in rows], 'limit': limit, 'offset': offset}

@app.delete('/api/restaurants/{restaurant_id}')
def delete_restaurant(restaurant_id: str):
    with get_db() as conn:
        conn.execute('DELETE FROM external_data WHERE UC_SEQ = ?', (restaurant_id,))
        conn.execute('DELETE FROM favorites WHERE restaurant_id = ?', (restaurant_id,))
        conn.execute('DELETE FROM official_translations WHERE source_id = ?', (restaurant_id,))
    return {'ok': True}

class CreateRestaurantBody(BaseModel):
    name: str
    district: str = ""
    address: str = ""
    address_detail: str = ""
    menu: str = ""
    description: str = ""
    phone: str = ""
    hours: str = ""
    homepage_url: str = ""
    lat: float = 35.1796
    lng: float = 129.0756

@app.post('/api/restaurants')
def create_restaurant(body: CreateRestaurantBody):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="상호명을 입력해 주세요.")
    
    import uuid
    new_id = f"custom_{uuid.uuid4().hex[:8]}"
    with get_db() as conn:
        conn.execute("""
            INSERT INTO external_data
            (UC_SEQ, MAIN_TITLE, GUGUN_NM, ADDR1, ADDR2, RPRSNTV_MENU, ITEMCNTNTS, CNTCT_TEL, USAGE_DAY_WEEK_AND_TIME, HOMEPAGE_URL, LAT, LNG)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id, body.name.strip(), body.district.strip(), body.address.strip(),
            body.address_detail.strip(), body.menu.strip(), body.description.strip(),
            body.phone.strip(), body.hours.strip(), body.homepage_url.strip(),
            str(body.lat), str(body.lng)
        ))
    return {'ok': True, 'id': new_id}

@app.post('/api/restaurants/sync-public')
def sync_public_data():
    url = "https://api.koreaconnect.kr/01/1/2603101713597416530PDP/CULTR/6260000/FoodService/getFoodKr"
    req = Request(url, headers={'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode('utf-8-sig'))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"공식 공공데이터 수신 실패: {str(e)}")
    
    rows = find_rows(payload)
    if not rows:
        raise HTTPException(status_code=422, detail="공공데이터 응답에서 맛집 목록을 찾지 못했습니다.")
    
    count = 0
    with get_db() as conn:
        for r in rows:
            if not isinstance(r, dict):
                continue
            uc_seq = value(r, 'UC_SEQ', 'ucSeq', 'id', 'ID')
            main_title = value(r, 'MAIN_TITLE', 'TITLE', 'name', 'NAME')
            if not uc_seq or not main_title:
                continue
            conn.execute("""
                INSERT INTO external_data
                (UC_SEQ, MAIN_TITLE, GUGUN_NM, ADDR1, ADDR2, RPRSNTV_MENU, ITEMCNTNTS, CNTCT_TEL, USAGE_DAY_WEEK_AND_TIME, HOMEPAGE_URL, MAIN_IMG_THUMB, LAT, LNG)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(UC_SEQ) DO UPDATE SET
                  MAIN_TITLE=excluded.MAIN_TITLE, GUGUN_NM=excluded.GUGUN_NM, ADDR1=excluded.ADDR1,
                  ADDR2=excluded.ADDR2, RPRSNTV_MENU=excluded.RPRSNTV_MENU, ITEMCNTNTS=excluded.ITEMCNTNTS,
                  CNTCT_TEL=excluded.CNTCT_TEL, USAGE_DAY_WEEK_AND_TIME=excluded.USAGE_DAY_WEEK_AND_TIME,
                  HOMEPAGE_URL=excluded.HOMEPAGE_URL, MAIN_IMG_THUMB=excluded.MAIN_IMG_THUMB,
                  LAT=excluded.LAT, LNG=excluded.LNG
            """, (
                uc_seq, main_title, value(r, 'GUGUN_NM', 'district'),
                value(r, 'ADDR1', 'address'), value(r, 'ADDR2', 'address_detail'),
                value(r, 'RPRSNTV_MENU', 'menu'), value(r, 'ITEMCNTNTS', 'description'),
                value(r, 'CNTCT_TEL', 'phone'), value(r, 'USAGE_DAY_WEEK_AND_TIME', 'hours'),
                value(r, 'HOMEPAGE_URL', 'homepage_url'), value(r, 'MAIN_IMG_THUMB', 'image_url'),
                value(r, 'LAT', 'lat'), value(r, 'LNG', 'lng')
            ))
            count += 1

    return {'ok': True, 'count': count}

OFFICIAL_TRANSLATION_URLS = {
    'en': 'https://api.koreaconnect.kr/01/1/2603101713597416530PDP/CULTR/6260000/FoodService/getFoodEn',
    'ja': 'https://api.koreaconnect.kr/01/1/2603101713597416530PDP/CULTR/6260000/FoodService/getFoodJa',
}
def value(data, *keys):
    for key in keys:
        result = data.get(key)
        if result is not None and str(result).strip():
            return str(result).strip()
    return ''
def find_rows(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ('items', 'data', 'response', 'body', 'result'):
        found = payload.get(key)
        if isinstance(found, list):
            return found
        if isinstance(found, dict):
            nested = find_rows(found)
            if nested:
                return nested
    return []
def normalize_official_rows(lang, payload):
    rows = []
    for raw in find_rows(payload):
        if not isinstance(raw, dict):
            continue
        source_id = value(raw, 'UC_SEQ', 'ucSeq', 'id', 'ID')
        source_name = value(raw, 'MAIN_TITLE_KO', 'MAIN_TITLE', 'TITLE_KO', 'source_name', 'name_ko', 'NAME_KO')
        name = value(raw, 'MAIN_TITLE', 'TITLE', 'name', 'NAME', 'MAIN_TITLE_EN' if lang == 'en' else 'MAIN_TITLE_JA')
        if not source_id and not source_name:
            continue
        rows.append((
            lang, source_id or source_name.replace(' ', '').lower(), source_name, name,
            value(raw, 'GUGUN_NM', 'district', 'AREA'),
            value(raw, 'ADDR1', 'address', 'ADDRESS'),
            value(raw, 'ADDR2', 'address_detail', 'ADDRESS_DETAIL'),
            value(raw, 'RPRSNTV_MENU', 'menu', 'MENU'),
            value(raw, 'ITEMCNTNTS', 'description', 'DESCRIPTION'),
            value(raw, 'USAGE_DAY_WEEK_AND_TIME', 'hours', 'HOURS'),
            value(raw, 'CNTCT_TEL', 'phone', 'PHONE'),
            value(raw, 'HOMEPAGE_URL', 'homepage_url', 'HOMEPAGE_URL'),
        ))
    return rows
@app.post('/api/restaurants/translations/sync')
def sync_official_translations(lang: str = Query(..., pattern='^(en|ja)$')):
    """Fetch official Busan multilingual restaurant data only when explicitly requested."""
    request = Request(OFFICIAL_TRANSLATION_URLS[lang], headers={'Accept': 'application/json'})
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode('utf-8-sig'))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail='공식 다국어 맛집 정보를 불러오지 못했습니다.') from error
    rows = normalize_official_rows(lang, payload)
    if not rows:
        raise HTTPException(status_code=422, detail='공식 응답에서 저장할 맛집 정보를 찾지 못했습니다.')
    with get_db() as conn:
        conn.executemany('''
          INSERT INTO official_translations
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT(lang, source_id) DO UPDATE SET
            source_name=excluded.source_name, name=excluded.name, district=excluded.district,
            address=excluded.address, address_detail=excluded.address_detail, menu=excluded.menu,
            description=excluded.description, hours=excluded.hours, phone=excluded.phone,
            homepage_url=excluded.homepage_url, updated_at=CURRENT_TIMESTAMP
        ''', rows)
    return {'ok': True, 'lang': lang, 'count': len(rows)}

DISTRICTS_SORTED = [
    ('부산진구', 'Busanjin-gu', '釜山鎮区'),
    ('해운대구', 'Haeundae-gu', '海雲台区'),
    ('금정구', 'Geumjeong-gu', '金井区'),
    ('강서구', 'Gangseo-gu', '江西区'),
    ('연제구', 'Yeonje-gu', '蓮堤区'),
    ('수영구', 'Suyeong-gu', '水営区'),
    ('사상구', 'Sasang-gu', '沙上区'),
    ('사하구', 'Saha-gu', '沙下区'),
    ('기장군', 'Gijang-gun', '機張郡'),
    ('동래구', 'Dongnae-gu', '東萊区'),
    ('영도구', 'Yeongdo-gu', '影島区'),
    ('중구', 'Jung-gu', '中区'),
    ('서구', 'Seo-gu', '西区'),
    ('동구', 'Dong-gu', '東区'),
    ('남구', 'Nam-gu', '南区'),
    ('북구', 'Buk-gu', '北区'),
]

MENU_ITEMS_SORTED = [
    ('갈미조개삼겹살', 'Galmi Clam & Pork Belly', 'ガルミ貝とサムギョプサル'),
    ('갈미샤브샤브', 'Galmi Clam Shabu-Shabu', 'ガルミ貝しゃぶしゃぶ'),
    ('갈미조개구이', 'Grilled Galmi Clams', 'ガルミ貝焼き'),
    ('갈미조개', 'Galmi Clam (Surf Clam)', 'ガルミ貝'),
    ('언양불고기', 'Eonyang Bulgogi', '彦陽プルコギ'),
    ('바지락칼국수', 'Clam Kalguksu Noodle Soup', 'アサリカルグクス'),
    ('해물칼국수', 'Seafood Kalguksu Noodle Soup', '海鮮カルグクス'),
    ('돌솥비빔밥', 'Hot Stone Bibimbap', '石焼きビビンバ'),
    ('부대찌개', 'Army Stew (Budae-jjigae)', 'プデチゲ'),
    ('순두부찌개', 'Soft Tofu Stew', 'スンドゥブチゲ'),
    ('된장찌개', 'Soybean Paste Stew', 'テンジャンチゲ'),
    ('김치찌개', 'Kimchi Stew', 'キムチチゲ'),
    ('돼지국밥', 'Pork Soup with Rice', '豚クッパ'),
    ('순대국밥', 'Sundae Pork Soup', 'スンデクッパ'),
    ('내장국밥', 'Intestine Pork Soup', 'ホルモンクッパ'),
    ('섞어국밥', 'Mixed Pork Soup', 'ミックスクッパ'),
    ('수육백반', 'Boiled Pork Rice Set', '茹で豚肉定食'),
    ('수육', 'Boiled Pork Slices', '茹で豚肉'),
    ('비빔밀면', 'Spicy Mixed Wheat Cold Noodles', 'ビビンミルミョン'),
    ('물밀면', 'Chilled Wheat Cold Noodle Soup', '水ミルミョン'),
    ('밀면', 'Busan Wheat Cold Noodles', 'ミルミョン (小麦冷麺)'),
    ('어묵', 'Busan Fish Cakes', '釜山おでん (オムク)'),
    ('낙곱새', 'Nakgobsae (Octopus, Intestine, Shrimp)', 'ナコプセ (タコ・ホルモン・エビ炒め)'),
    ('낙지볶음', 'Spicy Stir-fried Octopus', 'タコ炒め'),
    ('낙지전골', 'Spicy Octopus Hot Pot', 'タコ鍋'),
    ('해물파전', 'Seafood Scallion Pancake', '海鮮チヂミ'),
    ('파전', 'Scallion Pancake', 'ネギチヂミ'),
    ('양곱창', 'Grilled Beef Intestines', 'ヤンコプチャン'),
    ('소곱창', 'Grilled Beef Intestines', '牛ホルモン'),
    ('곱창전골', 'Spicy Intestine Hot Pot', 'ホルモン鍋'),
    ('곱창', 'Grilled Intestines', 'コプチャン'),
    ('모듬회', 'Assorted Sashimi', '刺身盛り合わせ'),
    ('광어회', 'Flatfish Sashimi', 'ヒラメ刺身'),
    ('우럭회', 'Rockfish Sashimi', 'クロソイ刺身'),
    ('물회', 'Cold Raw Fish Soup', '水刺身'),
    ('생선회', 'Fresh Sashimi', '鮮魚刺身'),
    ('회', 'Sashimi / Raw Fish', '刺身'),
    ('장어구이', 'Grilled Eel', 'ウナギ焼き'),
    ('장어탕', 'Eel Soup', 'ウナギスープ'),
    ('곰장어', 'Grilled Hagfish', 'ヌタウナギ焼き'),
    ('조개구이', 'Grilled Clams', '貝焼き'),
    ('조개찜', 'Steamed Clams', '蒸し貝'),
    ('조개', 'Clams', '貝'),
    ('복국', 'Busan Pufferfish Soup', 'フグ汁'),
    ('복지리', 'Clear Pufferfish Soup', 'フグチリ'),
    ('복매운탕', 'Spicy Pufferfish Stew', 'フグ辛みそ鍋'),
    ('아구찜', 'Braised Monkfish', 'アグチム (アンコウ蒸し)'),
    ('아귀찜', 'Braised Monkfish', 'アグチム (アンコウ蒸し)'),
    ('아구탕', 'Monkfish Soup', 'アンコウスープ'),
    ('해물탕', 'Spicy Seafood Stew', '海鮮鍋'),
    ('해물찜', 'Braised Seafood', '海鮮蒸し'),
    ('갈비탕', 'Beef Short Rib Soup', 'カルビタン'),
    ('돼지갈비', 'Grilled Pork Ribs', '豚カルビ'),
    ('소갈비', 'Grilled Beef Ribs', '牛カルビ'),
    ('갈비', 'Grilled Ribs', 'カルビ'),
    ('삼겹살', 'Pork Belly (Samgyeopsal)', 'サムギョプサル'),
    ('목살', 'Pork Shoulder', '豚モクサル'),
    ('한우', 'Korean Beef (Hanwoo)', '韓牛'),
    ('불고기', 'Bulgogi', 'プルコギ'),
    ('치킨', 'Korean Fried Chicken', '韓国風チキン'),
    ('통닭', 'Whole Fried Chicken', 'トンダック'),
    ('칼국수', 'Kalguksu Noodle Soup', 'カルグクス'),
    ('비빔밥', 'Bibimbap', 'ビビンバ'),
    ('청국장', 'Rich Soybean Stew', 'チョングッチャン'),
    ('물냉면', 'Cold Noodle Soup', '水冷麺'),
    ('비빔냉면', 'Spicy Mixed Cold Noodles', 'ビビン冷麺'),
    ('냉면', 'Cold Noodles', '冷麺'),
    ('군만두', 'Fried Dumplings', '焼き餃子'),
    ('찐만두', 'Steamed Dumplings', '蒸し餃子'),
    ('만두', 'Dumplings', 'マンドゥ'),
    ('떡볶이', 'Spicy Rice Cakes', 'トッポッキ'),
    ('씨앗호떡', 'Busan Seed Pancake', 'シアットック'),
    ('호떡', 'Sweet Pancake', 'ホットク'),
    ('샤브샤브', 'Shabu-Shabu', 'しゃぶしゃぶ'),
    ('국수', 'Noodles', '麺'),
    ('탕수육', 'Sweet & Sour Pork', '酢豚'),
    ('짜장면', 'Jajangmyeon Noodles', 'ジャージャー麺'),
    ('짬뽕', 'Jjamppong Noodle Soup', 'チャンポン'),
    ('초밥', 'Sushi', '寿司'),
    ('돈까스', 'Pork Cutlet (Donkatsu)', 'トンカツ'),
    ('돈가스', 'Pork Cutlet (Donkatsu)', 'トンカツ'),
    ('삼계탕', 'Ginseng Chicken Soup', 'サムゲタン'),
    ('오리불고기', 'Duck Bulgogi', '鴨プルコギ'),
    ('오리고기', 'Duck Meat', '鴨肉'),
    ('재첩국', 'Marsh Clam Soup', 'シジミスープ'),
    ('대구탕', 'Codfish Soup', 'タラスープ'),
]

ROAD_TRANSLATIONS = [
    ('르노삼성대로', 'Renaultsamsung-daero', 'ルノーサムスン大路'),
    ('해운대로', 'Haeundae-ro', '海雲台路'),
    ('중앙대로', 'Jungang-daero', '中央大路'),
    ('광안해변로', 'Gwanganhaebyeon-ro', '広安海辺路'),
    ('자갈치로', 'Jagalchi-ro', 'チャガルチ路'),
    ('구덕로', 'Gudeok-ro', '九徳路'),
    ('수영로', 'Suyeong-ro', '水営路'),
    ('가야대로', 'Gaya-daero', '伽倻大路'),
    ('낙동대로', 'Nakdong-daero', '洛東大路'),
    ('금정로', 'Geumjeong-ro', '金井路'),
]

NAME_TERMS_SORTED = [
    ('갈미샤브샤브', 'Galmi Clam Shabu-Shabu', 'ガルミ貝しゃぶしゃぶ'),
    ('갈미조개', 'Galmi Clam', 'ガルミ貝'),
    ('돼지국밥', 'Pork Soup', '豚クッパ'),
    ('국밥', 'Gukbap Soup', 'クッパ'),
    ('밀면', 'Milmyeon Cold Noodles', 'ミルミョン'),
    ('어묵', 'Fish Cakes', 'オムク'),
    ('양곱창', 'Yang-Gobchang', 'ヤンコプチャン'),
    ('곱창', 'Gobchang Intestines', 'コプチャン'),
    ('암소갈비', 'Amso Ribs', '雌牛カルビ'),
    ('갈비', 'Ribs (Galbi)', 'カルビ'),
    ('삼겹살', 'Pork Belly', 'サムギョプサル'),
    ('치킨', 'Chicken', 'チキン'),
    ('통닭', 'Fried Chicken', 'トンダック'),
    ('할매', 'Grandma (Halmae)', 'ハルメ'),
    ('원조', 'Original (Wonjo)', '元祖'),
    ('소문난', 'Famous (Somunnan)', '噂の'),
    ('본점', 'Main Branch', '本店'),
    ('식당', 'Restaurant', '食堂'),
    ('집', 'House', '家'),
]

def translate_name(name_text: str, lang: str) -> str:
    if not name_text:
        return ''
    res = name_text
    for kr, en, ja in NAME_TERMS_SORTED:
        tr = en if lang == 'en' else ja
        if kr in res:
            res = res.replace(kr, f" {tr} ")
    import re
    res = re.sub(r'\s+', ' ', res).strip()
    return res

def translate_menu(menu_text: str, lang: str) -> str:
    if not menu_text:
        return ''
    res = menu_text
    for kr, en, ja in MENU_ITEMS_SORTED:
        tr = en if lang == 'en' else ja
        if kr in res:
            res = res.replace(kr, f" {tr} ")
    import re
    res = re.sub(r'\s+', ' ', res).strip()
    return res

def translate_address(addr: str, lang: str) -> str:
    if not addr:
        return ''
    res = addr
    res = res.replace('부산광역시', 'Busan' if lang == 'en' else '釜山広域市')
    res = res.replace('부산시', 'Busan' if lang == 'en' else '釜山市')

    for kr, en, ja in DISTRICTS_SORTED:
        tr = en if lang == 'en' else ja
        if kr in res:
            res = res.replace(kr, f" {tr} ")

    for kr, en, ja in ROAD_TRANSLATIONS:
        tr = en if lang == 'en' else ja
        if kr in res:
            res = res.replace(kr, f" {tr} ")

    import re
    res = re.sub(r'\s+', ' ', res).strip()
    return res

def generate_fallback_translation(row: dict, lang: str) -> dict:
    source_id = str(row.get('id', ''))
    source_name = str(row.get('name', ''))
    district_kr = str(row.get('district', ''))
    address_kr = str(row.get('address', ''))
    menu_kr = str(row.get('menu', ''))
    desc_kr = str(row.get('description', ''))
    
    district_tr = district_kr
    for kr, en, ja in DISTRICTS_SORTED:
        if kr == district_kr:
            district_tr = en if lang == 'en' else ja
            break

    name_tr = translate_name(source_name, lang)
    menu_tr = translate_menu(menu_kr, lang)
    address_tr = translate_address(address_kr, lang)
    
    if lang == 'en':
        desc_tr = f"A popular local restaurant in {district_tr}, Busan offering {menu_tr or 'authentic Korean cuisine'}."
    else:
        desc_tr = f"釜山広域市{district_tr}に位置する人気グルメ店。{menu_tr or '伝統的な韓国料理'}をお楽しみいただけます。"
        
    return {
        'id': source_id,
        'name': name_tr or source_name,
        'district': district_tr,
        'address': address_tr,
        'address_detail': str(row.get('address_detail', '')),
        'description': desc_tr if desc_kr else '',
        'menu': menu_tr,
        'hours': str(row.get('hours', '')),
        'source_name': source_name,
        'phone': str(row.get('phone', '')),
        'homepage_url': str(row.get('homepage_url', '')),
        'updated_at': '2026-08-11 00:00:00'
    }

@app.get('/api/restaurants/translations')
def restaurant_translations(lang: str = Query(..., pattern='^(en|ja)$')):
    with get_db() as conn:
        official_rows = conn.execute('''
          SELECT source_id AS id, name, address, address_detail, description, menu, hours, district,
                 source_name, phone, homepage_url, updated_at
          FROM official_translations
          WHERE lang = ? AND TRIM(name) <> ''
          ORDER BY updated_at DESC, name COLLATE NOCASE
        ''', (lang,)).fetchall()
        
        official_map = {dict(row)['id']: dict(row) for row in official_rows}
        base_rows = conn.execute(BASE_SELECT).fetchall()
        
        items = []
        for r in base_rows:
            r_dict = dict(r)
            r_id = str(r_dict['id'])
            if r_id in official_map:
                items.append(official_map[r_id])
            else:
                items.append(generate_fallback_translation(r_dict, lang))

    return {'lang': lang, 'items': items, 'count': len(items)}

@app.get('/api/restaurants/translations/status')
def translation_status():
    with get_db() as conn:
        rows = conn.execute('''
          SELECT lang, COUNT(*) AS count, MAX(updated_at) AS updated_at
          FROM official_translations
          WHERE TRIM(name) <> ''
          GROUP BY lang
        ''').fetchall()
    status = {row['lang']: {'count': row['count'], 'updated_at': row['updated_at']} for row in rows}
    return {
        'en': status.get('en', {'count': 0, 'updated_at': None}),
        'ja': status.get('ja', {'count': 0, 'updated_at': None}),
    }

@app.get('/api/restaurants/summary')
def restaurant_summary():
    with get_db() as conn:
        row = conn.execute("""
          SELECT COUNT(*) AS total, COUNT(DISTINCT NULLIF(TRIM(GUGUN_NM), '')) AS districts
          FROM external_data
          WHERE TRIM(COALESCE(UC_SEQ, '')) <> '' AND TRIM(COALESCE(LAT, '')) <> '' AND TRIM(COALESCE(LNG, '')) <> ''
        """).fetchone()
    return dict(row)

@app.post('/api/favorites/{restaurant_id}')
def add_favorite(restaurant_id: str):
    with get_db() as conn:
        exists = conn.execute('SELECT 1 FROM external_data WHERE UC_SEQ = ?', (restaurant_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail='맛집을 찾을 수 없습니다.')
        conn.execute('INSERT OR IGNORE INTO favorites (restaurant_id) VALUES (?)', (restaurant_id,))
    return {'ok': True}
@app.delete('/api/favorites/{restaurant_id}')
def delete_favorite(restaurant_id: str):
    with get_db() as conn:
        conn.execute('DELETE FROM favorites WHERE restaurant_id = ?', (restaurant_id,))
    return {'ok': True}
@app.post('/api/searches')
def save_search(body: SearchBody):
    query = body.query.strip()
    if query:
        with get_db() as conn:
            conn.execute('INSERT INTO search_history (query) VALUES (?)', (query,))
    return {'ok': True}
@app.get('/api/preferences')
def preferences():
    with get_db() as conn:
        rows = conn.execute('SELECT key, value FROM preferences').fetchall()
    return {row['key']: row['value'] for row in rows}
@app.put('/api/preferences')
def save_preference(body: PreferenceBody):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (body.key, body.value),
        )
    return {'ok': True}
