import type { Restaurant } from '../App'
type Props = { item: Restaurant; lang: string; onToggle: (item: Restaurant) => void; onSelect: (item: Restaurant) => void; onDelete?: (item: Restaurant) => void }
const copy = { ko: { save: '즐겨찾기 저장', delete: '삭제', menu: '대표 메뉴', view: '지도에서 보기', area: '지역', noMenu: '메뉴 정보 없음', noAddress: '주소 정보 없음', distance: '현재 위치에서 약' }, en: { save: 'Save favorite', delete: 'Delete', menu: 'Menu', view: 'View on map', area: 'Area', noMenu: 'Menu unavailable', noAddress: 'Address unavailable', distance: 'About' }, ja: { save: 'お気に入り保存', delete: '削除', menu: 'おすすめメニュー', view: '地図で見る', area: '地域', noMenu: 'メニュー情報はありません', noAddress: '住所情報はありません', distance: '現在地から約' } }
export default function RestaurantCard({ item, lang, onToggle, onSelect, onDelete }: Props) {
  const t = copy[lang as keyof typeof copy] || copy.ko
  return <article className="restaurant-card">
    <div className="card-top">
      <span className="category">{item.district || t.area}</span>
      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        {onDelete && <button className="delete-icon-btn" onClick={() => onDelete(item)} title={t.delete} style={{ background: 'transparent', color: '#b94a48', fontSize: '14px' }}>🗑</button>}
        <button className={'heart ' + (item.favorite ? 'saved' : '')} onClick={() => onToggle(item)} aria-label={t.save}>{item.favorite ? '♥' : '♡'}</button>
      </div>
    </div>
    <h3>{item.name}</h3>
    <p className="menu-label">{t.menu}</p>
    <p className="card-menu">{item.menu || t.noMenu}</p>
    <p>{item.address || t.noAddress}</p>
    {item.distance !== undefined && (
      <p className="distance">
        📍 {t.distance} {item.distance.toFixed(1)}km
      </p>
    )}
    <button className="text-button" onClick={() => onSelect(item)}>⌖ {t.view}</button>
  </article>
}

