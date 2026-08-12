import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { useEffect, useMemo } from 'react'
import type { Restaurant } from '../App'

type Props = {
  restaurants: Restaurant[]
  selected: Restaurant | null
  userPosition?: [number, number] | null
  sortActive?: boolean
  onSelect: (item: Restaurant) => void
  lang: string
}

function FlyTo({ selected, userPosition, sortActive }: { selected: Restaurant | null; userPosition?: [number, number] | null; sortActive?: boolean }) {
  const map = useMap()
  useEffect(() => {
    if (selected) {
      map.flyTo([selected.lat, selected.lng], 14, { duration: 0.7 })
    } else if (sortActive && userPosition) {
      map.flyTo(userPosition, 13, { duration: 0.7 })
    }
  }, [selected, userPosition, sortActive, map])
  return null
}

export default function MapView({ restaurants, selected, userPosition, sortActive, onSelect, lang }: Props) {
  const info = lang === 'ja' ? '代表メニュー' : lang === 'en' ? 'Menu' : '대표 메뉴'
  const myLocText = lang === 'ja' ? '現在地' : lang === 'en' ? 'My Location' : '내 위치 (현재 위치)'
  const mapMarkers = useMemo(() => {
    if (selected) return restaurants
    const seen = new Set<string>()
    return restaurants.filter((restaurant) => {
      const key = `${restaurant.lat.toFixed(3)}:${restaurant.lng.toFixed(3)}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [restaurants, selected])

  return (
    <MapContainer center={[35.151, 129.075]} zoom={11} className="map-view" zoomControl={false}>
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FlyTo selected={selected} userPosition={userPosition} sortActive={sortActive} />
      
      {/* User Position Marker */}
      {userPosition && (
        <CircleMarker
          center={userPosition}
          radius={11}
          pathOptions={{ color: '#ffffff', fillColor: '#1e5fa8', fillOpacity: 0.95, weight: 3 }}
        >
          <Popup>
            <div className="map-popup">
              <strong style={{ color: '#1e5fa8' }}>📍 {myLocText}</strong>
            </div>
          </Popup>
        </CircleMarker>
      )}

      {/* Restaurant Markers */}
      {mapMarkers.map(r => (
        <CircleMarker
          key={r.id}
          center={[r.lat, r.lng]}
          radius={selected?.id === r.id ? 15 : 8}
          pathOptions={{
            color: '#1e5fa8',
            fillColor: '#f47c3c',
            fillOpacity: selected?.id === r.id ? 1 : 0.88,
            weight: 2
          }}
          eventHandlers={{ click: () => onSelect(r) }}
        >
          <Popup>
            <div className="map-popup">
              <strong>{r.name}</strong>
              <span>{r.district} · {r.address}</span>
              {r.menu && <span>{info}: {r.menu}</span>}
              {r.distance !== undefined && (
                <span style={{ color: '#ba5422', fontWeight: 'bold' }}>
                  {lang === 'ja' ? `現在地から ${r.distance.toFixed(1)}km` : lang === 'en' ? `${r.distance.toFixed(1)}km from location` : `내 위치에서약 ${r.distance.toFixed(1)}km`}
                </span>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}

