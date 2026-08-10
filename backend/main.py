import json
import os
import sqlite3
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
DB_PATH = "/workspace/data/app.db"
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
          (lang, source_id, source_name, name, district, address, address_detail, menu, description, hours, phone, homepage_url)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT(lang, source_id) DO UPDATE SET
            source_name=excluded.source_name, name=excluded.name, district=excluded.district,
            address=excluded.address, address_detail=excluded.address_detail, menu=excluded.menu,
            description=excluded.description, hours=excluded.hours, phone=excluded.phone,
            homepage_url=excluded.homepage_url, updated_at=CURRENT_TIMESTAMP
        ''', rows)
    return {'ok': True, 'lang': lang, 'count': len(rows)}
@app.get('/api/restaurants/translations')
def restaurant_translations(lang: str = Query(..., pattern='^(en|ja)$')):
    with get_db() as conn:
        official = conn.execute('''
          SELECT source_id AS id, name, address, address_detail, description, menu, hours, district,
                 source_name, phone, homepage_url, updated_at
          FROM official_translations
          WHERE lang = ? AND TRIM(name) <> ''
          ORDER BY updated_at DESC, name COLLATE NOCASE
        ''', (lang,)).fetchall()
    return {'lang': lang, 'items': [dict(row) for row in official], 'count': len(official)}

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
