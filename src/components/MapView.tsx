import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { useEffect, useMemo } from 'react'
import type { Restaurant } from '../App'
type Props = { restaurants: Restaurant[]; selected: Restaurant | null; onSelect: (item: Restaurant) => void; lang: string }
function FlyTo({ selected }: { selected: Restaurant | null }) {
  const map = useMap()
  useEffect(() => { if (selected) map.flyTo([selected.lat, selected.lng], 14, { duration: 0.7 }) }, [selected, map])
  return null
}
export default function MapView({ restaurants, selected, onSelect, lang }: Props) {
  const info = lang === 'ja' ? '代表メニュー' : lang === 'en' ? 'Menu' : '대표 메뉴'
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
  return <MapContainer center={[35.151, 129.075]} zoom={11} className="map-view" zoomControl={false}>
    <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <FlyTo selected={selected} />
    {mapMarkers.map(r => <CircleMarker key={r.id} center={[r.lat, r.lng]} radius={selected?.id === r.id ? 15 : 8} pathOptions={{ color: '#1e5fa8', fillColor: '#f47c3c', fillOpacity: selected?.id === r.id ? 1 : .88, weight: 2 }} eventHandlers={{ click: () => onSelect(r) }}>
      <Popup><div className="map-popup"><strong>{r.name}</strong><span>{r.district} · {r.address}</span>{r.menu && <span>{info}: {r.menu}</span>}</div></Popup>
    </CircleMarker>)}
  </MapContainer>
}
