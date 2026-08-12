# AGENTS.md - Busan Nopo Food Map Application Specification & Guidelines

## 📌 Project Overview
**Busan Nopo Food Map (부산 노포 맛집 지도 앱)** is a modern web application providing official data and interactive map navigation for traditional/nopo restaurants in Busan, South Korea.

- **Frontend**: React (TypeScript), Vite, Leaflet / React-Leaflet, Vanilla CSS.
- **Backend**: FastAPI (Python), SQLite (`busan_food.db` / `data/app.db`).

---

## 🎯 System Requirements & Operational Rules

### 1. Logo & Home Reset Behavior (부산 음식 로고 및 홈 설정)
- **Busan Food Logo**: The app displays a dedicated SVG logo (`BusanFoodLogo.tsx`) featuring traditional Busan cuisine (steaming pork soup/stew bowl badge with Busan ocean blue accent).
- **Home Reset Action**: Clicking the logo brand container in the topbar resets the application to its initial home state:
  - Clears search input query
  - Clears district filter
  - Resets active view to 'map'
  - Turns off distance sorting
  - Deselects selected restaurant
  - Resets map center to Busan center `[35.1796, 129.0756]`

### 2. Multi-Language Support for Add Restaurant Modal (맛집 추가 다국어 지원)
- All modal dialogs (including the "Add Restaurant" form modal, headers, input labels, district select dropdown options, placeholders, cancel/submit buttons, and popup alert messages) MUST support `ko`, `en`, and `ja`.
- Localized district names (e.g. `Haeundae-gu`, `海雲台区`) are dynamically rendered in dropdowns based on the selected language.

### 3. Automatic Coordinate Assignment without Lat/Lng Inputs (위도/경도 삭제 및 자동 좌표 지정)
- The Add Restaurant form modal does NOT contain manual latitude or longitude input fields.
- Latitude and longitude coordinates are assigned automatically based on the selected Busan district center coordinates (`DISTRICT_COORDINATES` mapping table for all 16 Busan districts: 해운대구, 수영구, 중구, 부산진구, 동래구, 남구, 서구, 동구, 영도구, 금정구, 강서구, 연제구, 사상구, 사하구, 북구, 기장군).

### 4. Busan-Only Geofenced Location Finding (내 위치 찾기 - 부산 지역 외 위치 차단)
- When "내 위치 찾기" (Find My Location) is triggered:
  - The app inspects user geolocation coordinates (`latitude`, `longitude`).
  - Coordinates are validated against Busan's bounding box:
    - Latitude: `34.85` ~ `35.40`
    - Longitude: `128.75` ~ `129.35`
  - If the user is outside Busan (e.g. Seoul, Japan, abroad), the position is NOT updated on the map, and a localized alert notification is displayed informing the user that location search is restricted to Busan.
  - If inside Busan, user position is set, distance sorting is enabled, and the map flies to the user position.

### 5. Haversine Distance Calculation & Explicit Display (거리 순 정렬 및 거리 표기)
- Distance from user position to each restaurant (e.g. '만드리곤드레밥') is calculated accurately in kilometers using the Haversine formula.
- Distances are displayed clearly on restaurant cards, map popups, and detail views (e.g. `내 위치에서 약 1.2km` / `About 1.2km from location` / `現在地から約 1.2km`).

---

## 🛠️ Codebase Structure

```
busanfood/
├── AGENTS.md                  # System rules and agent specifications
├── src/
│   ├── App.tsx                # Main App component with state, labels, and modal logic
│   ├── index.css              # Custom design system styling & animations
│   ├── components/
│   │   ├── BusanFoodLogo.tsx  # Custom SVG logo component for Busan Food
│   │   ├── MapView.tsx        # Leaflet map container with user position & restaurant markers
│   │   └── RestaurantCard.tsx # Restaurant card component with distance display & actions
│   └── lib/
│       └── api.ts             # API client utility
└── backend/
    └── main.py                # FastAPI REST server with SQLite persistence
```

