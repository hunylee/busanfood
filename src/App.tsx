import { useEffect, useMemo, useState } from 'react'
import 'leaflet/dist/leaflet.css'
import { api } from './lib/api'
import MapView from './components/MapView'
import RestaurantCard from './components/RestaurantCard'
export type Restaurant = {
  id: string; name: string; district: string; address: string; address_detail: string
  menu: string; description: string; phone: string; hours: string; homepage_url: string
  image_url: string; lat: number; lng: number; favorite: number; distance?: number
}
type Lang = 'ko' | 'en' | 'ja'
type ApiResponse = { items: Restaurant[] }
type Translation = { id: string; name: string; address: string; address_detail?: string; description: string; menu?: string; hours?: string; district?: string; source_name: string; phone?: string; homepage_url?: string }
type LocalizedRestaurant = Restaurant & { translation_available?: boolean; source_name?: string; source_address?: string; source_menu?: string; source_description?: string }
const labels = {
  ko: { title:'부산 맛집 지도', sub:'부산광역시 공식 맛집 정보', search:'맛집 이름, 구·군, 메뉴 검색', distance:'거리순', filter:'지역 필터', fav:'내 즐겨찾기', map:'지도 탐색', all:'전체 지역', result:'곳의 부산 맛집', near:'내 위치 찾기', location:'현재 위치 기준', empty:'조건에 맞는 맛집이 없어요.', loading:'부산의 실제 맛집 정보를 불러오는 중이에요…', error:'정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.', list:'맛집 목록', source:'부산광역시 부산맛집 정보', menu:'대표 메뉴', hours:'운영 시간', phone:'전화', district:'지역', saved:'즐겨찾기 저장됨', save:'즐겨찾기 저장', noMenu:'대표 메뉴 정보 없음', noDescription:'상세 소개 정보가 준비되어 있지 않습니다.', retry:'다시 시도', basedOn:'Busan, Korea', translateNotice:'' },
  en: { title:'Busan Food Map', sub:'Official Busan restaurant information', search:'Search name, district, or menu', distance:'Distance', filter:'Area', fav:'My favorites', map:'Explore map', all:'All areas', result:'Busan restaurants', near:'Find my location', location:'Based on your location', empty:'No restaurants match your choices.', loading:'Loading Busan restaurant information…', error:'Could not load information. Please try again.', list:'Restaurant list', source:'Busan Metropolitan City food data', menu:'Menu', hours:'Hours', phone:'Phone', district:'Area', saved:'Saved to favorites', save:'Save favorite', noMenu:'Menu information unavailable', noDescription:'A detailed introduction is not available.', retry:'Try again', basedOn:'Busan, Korea', translateNotice:'Official English data is shown when available.' },
  ja: { title:'釜山グルメ地図', sub:'釜山広域市 公式グルメ情報', search:'店名・地域・メニューを検索', distance:'距離順', filter:'エリア', fav:'お気に入り', map:'地図を探す', all:'すべての地域', result:'軒の釜山グルメ', near:'現在地を探す', location:'現在地を基準', empty:'条件に合うお店はありません。', loading:'釜山のグルメ情報を読み込んでいます…', error:'情報を読み込めませんでした。', list:'グルメ一覧', source:'釜山広域市 グルメ情報', menu:'おすすめメニュー', hours:'営業時間', phone:'電話', district:'地域', saved:'保存済み', save:'お気に入り保存', noMenu:'メニュー情報はありません', noDescription:'詳しい紹介情報は準備中です。', retry:'もう一度試す', basedOn:'Busan, Korea', translateNotice:'公式日本語データは、利用できる場合に表示されます。' }
}
const districtNames: Record<Lang, Record<string, string>> = {
  ko: {},
  en: {
    '중구': 'Jung-gu', '서구': 'Seo-gu', '동구': 'Dong-gu', '영도구': 'Yeongdo-gu',
    '부산진구': 'Busanjin-gu', '동래구': 'Dongnae-gu', '남구': 'Nam-gu', '북구': 'Buk-gu',
    '해운대구': 'Haeundae-gu', '사하구': 'Saha-gu', '금정구': 'Geumjeong-gu', '강서구': 'Gangseo-gu',
    '연제구': 'Yeonje-gu', '수영구': 'Suyeong-gu', '사상구': 'Sasang-gu', '기장군': 'Gijang-gun'
  },
  ja: {
    '중구': '中区', '서구': '西区', '동구': '東区', '영도구': '影島区',
    '부산진구': '釜山鎮区', '동래구': '東萊区', '남구': '南区', '북구': '北区',
    '해운대구': '海雲台区', '사하구': '沙下区', '금정구': '金井区', '강서구': '江西区',
    '연제구': '蓮堤区', '수영구': '水営区', '사상구': '沙上区', '기장군': '機張郡'
  }
}

function dist(a:number,b:number,c:number,d:number) { const x=(c-a)*111, y=(d-b)*91; return Math.sqrt(x*x+y*y) }

export default function App() {
  const [items,setItems]=useState<Restaurant[]>([]), [loading,setLoading]=useState(true), [error,setError]=useState('')
  const [query,setQuery]=useState(''), [district,setDistrict]=useState(''), [sort,setSort]=useState(false)
  const [view,setView]=useState<'map'|'favorites'>('map'), [lang,setLang]=useState<Lang>('ko'), [selected,setSelected]=useState<Restaurant|null>(null)
  const [showAll,setShowAll]=useState(false)
  const [position,setPosition]=useState<[number,number]>([35.1796,129.0756])
  const [translations, setTranslations] = useState<Record<string, Translation>>({})
  const [translationNames, setTranslationNames] = useState<Record<string, Translation>>({})
  const t=labels[lang]
  const load=async()=>{ try { setLoading(true); setError(''); const res=await api('restaurants?limit=500'); if(!res.ok) throw new Error(); const data:ApiResponse=await res.json(); setItems(data.items || []) } catch { setError('load') } finally { setLoading(false) } }
  useEffect(()=>{ load(); api('preferences').then(r=>r.ok?r.json():{}).then(p=>{ if(p.lang && ['ko','en','ja'].includes(p.lang)) setLang(p.lang) }).catch(()=>{}) },[])
  const applyTranslations = (data: { items: Translation[] }) => {
    const byId: Record<string, Translation> = {}
    const byName: Record<string, Translation> = {}
    data.items.forEach(item => {
      byId[String(item.id)] = item
      if (item.source_name) byName[item.source_name.trim().replace(/\s+/g, '').toLowerCase()] = item
    })
    setTranslations(byId)
    setTranslationNames(byName)
  }

  const fetchTranslations = (v: Exclude<Lang, 'ko'>) => {
    api(`restaurants/translations?lang=${v}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(applyTranslations)
      .catch(() => { setTranslations({}); setTranslationNames({}) })
  }

  useEffect(()=>{
    if (lang === 'ko') { setTranslations({}); setTranslationNames({}); return }
    fetchTranslations(lang)
  },[lang])

  const localized = (item: Restaurant): LocalizedRestaurant => {
    const normalizedName = item.name.trim().replace(/\s+/g, '').toLowerCase()
    const translated = translations[item.id] || translationNames[normalizedName]
    if (!translated) return { ...item, translation_available: lang === 'ko' }
    return {
      ...item,
      name: translated.name || item.name,
      district: translated.district || item.district,
      address: translated.address || item.address,
      address_detail: translated.address_detail || item.address_detail,
      menu: translated.menu || item.menu,
      hours: translated.hours || item.hours,
      phone: translated.phone || item.phone,
      homepage_url: translated.homepage_url || item.homepage_url,
      description: translated.description || item.description,
      source_name: item.name,
      source_address: item.address,
      source_menu: item.menu,
      source_description: item.description,
      translation_available: true,
    }
  }

  const getDistrictName = (d: string, currentLang: Lang) => {
    if (!d) return ''
    return districtNames[currentLang]?.[d] || d
  }

  const districts=useMemo(()=>Array.from(new Set(items.map(x=>x.district).filter(Boolean))).sort((a,b)=>a.localeCompare(b,'ko')), [items])
  const display=useMemo(()=>{ const words=query.trim().toLowerCase(); let r=items.filter(x=> { const locale=localized(x); return (!district || x.district===district) && (!words || [locale.name,x.name,x.district,locale.address,x.address,x.menu,locale.description,x.description].join(' ').toLowerCase().includes(words)) }); if(view==='favorites') r=r.filter(x=>x.favorite); const localizedItems=r.map(localized); return sort ? [...localizedItems].map(x=>({...x,distance:dist(position[0],position[1],x.lat,x.lng)})).sort((a,b)=>(a.distance||0)-(b.distance||0)) : localizedItems },[items,query,district,sort,view,position,translations,translationNames])
  const visibleItems = showAll ? display : display.slice(0, 24)
  const selectedDisplay = selected ? localized(selected) : null
  const syncTranslations = async (v: Exclude<Lang, 'ko'>) => {
    try {
      await api(`restaurants/translations/sync?lang=${v}`, { method: 'POST' })
      fetchTranslations(v)
    } catch {
      // Optional background sync fallback
    }
  }
  const changeLang=(v:Lang)=>{
    setLang(v)
    if (v !== 'ko') {
      fetchTranslations(v)
      syncTranslations(v)
    } else {
      setTranslations({})
      setTranslationNames({})
    }
    api('preferences',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:'lang',value:v})}).catch(()=>{})
  }
  const changeDistrict=(v:string)=>{ setDistrict(v); setShowAll(false); api('preferences',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:'district',value:v})}).catch(()=>{}) }
  useEffect(()=>{ setShowAll(false) }, [query, view, sort])
  const toggle=async(item:Restaurant)=>{ const method=item.favorite?'DELETE':'POST'; try { const r=await api(`favorites/${item.id}`,{method}); if(!r.ok) throw new Error(); const updated={...item,favorite:item.favorite?0:1}; setItems(old=>old.map(x=>x.id===item.id?updated:x)); setSelected(current=>current?.id===item.id?updated:current) } catch { setError('save') } }
  const locate=()=>{ if(!navigator.geolocation){ setSort(true); return } navigator.geolocation.getCurrentPosition(p=>{setPosition([p.coords.latitude,p.coords.longitude]);setSort(true)},()=>setSort(true),{timeout:6000}) }
  const submit=(e:React.FormEvent)=>{e.preventDefault(); if(query.trim()) api('searches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})}).catch(()=>{})}
  const [showModal, setShowModal] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [formData, setFormData] = useState({
    name: '', district: '해운대구', address: '', address_detail: '', menu: '', description: '', phone: '', hours: '', homepage_url: '', lat: 35.1587, lng: 129.1604
  })

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) return alert('상호명을 입력해 주세요.')
    try {
      const res = await api('restaurants', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (!res.ok) throw new Error('추가 실패')
      alert('맛집이 SQLite 데이터베이스에 성공적으로 추가되었습니다!')
      setShowModal(false)
      setFormData({ name: '', district: '해운대구', address: '', address_detail: '', menu: '', description: '', phone: '', hours: '', homepage_url: '', lat: 35.1587, lng: 129.1604 })
      load()
    } catch {
      alert('맛집 추가 중 오류가 발생했습니다.')
    }
  }

  const handleDelete = async (item: Restaurant) => {
    if (!confirm(`'${item.name}' 맛집을 SQLite 데이터베이스에서 삭제하시겠습니까?`)) return
    try {
      const res = await api(`restaurants/${item.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      alert('맛집이 SQLite 데이터베이스에서 삭제되었습니다.')
      setSelected(null)
      load()
    } catch {
      alert('삭제 처리 중 오류가 발생했습니다.')
    }
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">●</span><div><b>{t.title}</b><small>{t.sub}</small></div></div>
      <nav>
        <button className={view==='map'?'active':''} onClick={()=>setView('map')}>⌖ {t.map}</button>
        <button className={view==='favorites'?'active':''} onClick={()=>setView('favorites')}>♥ {t.fav}<em>{items.filter(x=>x.favorite).length}</em></button>
        <button className="add-button" onClick={()=>setShowModal(true)}>+ {lang==='ko'?'맛집 추가':lang==='en'?'Add Place':'お店を追加'}</button>
      </nav>
      <div className="language" aria-label="언어 선택">{(['ko','en','ja'] as Lang[]).map(l=><button key={l} onClick={()=>changeLang(l)} className={lang===l?'active':''}>{l==='ko'?'KO':l==='en'?'EN':'日本語'}</button>)}</div>
    </header>

    <main><section className="map-stage"><MapView restaurants={display} selected={selectedDisplay} onSelect={setSelected} lang={lang}/><div className="controls"><form className="search" onSubmit={submit}><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t.search}/><button type="submit" aria-label="검색">→</button></form><div className="tool-row"><button onClick={()=>setSort(!sort)} className={sort?'selected':''}>↕ {t.distance}</button><details><summary>⌖ {t.filter}{district?`: ${getDistrictName(district, lang)}`:''}</summary><div className="filter-menu"><button className={!district?'selected':''} onClick={()=>changeDistrict('')}>{t.all}</button>{districts.map(d=><button key={d} className={district===d?'selected':''} onClick={()=>changeDistrict(d)}>{getDistrictName(d, lang)}</button>)}</div></details><button onClick={locate}>◎ {t.near}</button></div></div>
      <div className="map-caption"><span className="pulse"></span>{sort?t.location:t.basedOn} · <b>{display.length}{t.result}</b></div>
      {selectedDisplay && <aside className="detail-card">
        <button className="close" onClick={()=>setSelected(null)} aria-label="닫기">×</button>
        <span className="category">{selectedDisplay.district || t.district}</span>
        <h2>{selectedDisplay.name}</h2>
        {lang !== 'ko' && selectedDisplay.source_name && <p className="translation-note">{selectedDisplay.source_name}</p>}
        <p className="detail-menu">{t.menu} · {selectedDisplay.menu || t.noMenu}</p>
        <p>{selectedDisplay.address}{selectedDisplay.address_detail ? ` ${selectedDisplay.address_detail}`:''}</p>
        {lang !== 'ko' && selectedDisplay.source_address && <p className="translation-note">{selectedDisplay.source_address}</p>}
        {selectedDisplay.phone&&<p><b>{t.phone}</b> · <a href={`tel:${selectedDisplay.phone.replace(/[^0-9+]/g,'')}`}>{selectedDisplay.phone}</a></p>}
        {selectedDisplay.hours&&<p><b>{t.hours}</b> · {selectedDisplay.hours}</p>}
        <p className="detail-description">{selectedDisplay.description || t.noDescription}</p>
        {lang !== 'ko' && selectedDisplay.source_description && <p className="translation-note">{selectedDisplay.source_description}</p>}
        {selectedDisplay.homepage_url&&<a className="homepage-link" href={selectedDisplay.homepage_url} target="_blank" rel="noreferrer">↗ {lang === 'ko' ? '공식 안내 보기' : lang === 'en' ? 'Visit website' : '公式案内を見る'}</a>}
        <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
          <button className="save-button" style={{ flex: 1 }} onClick={()=>toggle(selectedDisplay)}>{selectedDisplay.favorite?'♥ '+t.saved:'♡ '+t.save}</button>
          <button className="save-button" style={{ background: '#c94a38', width: 'auto', padding: '12px 14px' }} onClick={()=>handleDelete(selectedDisplay)} title="맛집 삭제">🗑 삭제</button>
        </div>
      </aside>}
    </section>
    <section className="list-panel"><div className="list-heading"><div><p className="eyebrow">{t.source.toUpperCase()}</p><h1>{view==='favorites'?t.fav:t.list}</h1></div><span>{display.length}{t.result}</span></div>{loading?<div className="state">{t.loading}</div>:error?<div className="state error">{t.error}<button onClick={load}>{t.retry}</button></div>:display.length===0?<div className="state">{t.empty}</div>:<><div className="card-grid">{visibleItems.map(item=><RestaurantCard key={item.id} item={item} lang={lang} onToggle={toggle} onSelect={setSelected} onDelete={handleDelete}/>)}</div>{display.length>visibleItems.length&&<button className="more-button" onClick={()=>setShowAll(true)}>{lang==='ko'?`맛집 ${display.length - visibleItems.length}곳 더 보기`:lang==='en'?`Show ${display.length - visibleItems.length} more restaurants`:`さらに${display.length - visibleItems.length}件を見る`}</button>}</>}</section>
  </main>

  {showModal && <div className="modal-overlay" onClick={()=>setShowModal(false)}>
    <div className="modal-box" onClick={e=>e.stopPropagation()}>
      <div className="modal-header">
        <h2>+ 새로운 맛집 직접 등록</h2>
        <button className="close" onClick={()=>setShowModal(false)}>×</button>
      </div>
      <form onSubmit={handleCreateSubmit} className="form-grid">
        <div className="form-group full">
          <label>상호명 (식당 이름) *</label>
          <input required placeholder="예: 부산 광안리 맛집" value={formData.name} onChange={e=>setFormData({...formData, name: e.target.value})}/>
        </div>
        <div className="form-group">
          <label>구 · 군 선택</label>
          <select value={formData.district} onChange={e=>setFormData({...formData, district: e.target.value})}>
            {['해운대구','수영구','중구','부산진구','동래구','남구','서구','동구','영도구','금정구','강서구','연제구','사상구','사하구','북구','기장군'].map(d=><option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>전화번호</label>
          <input placeholder="예: 051-123-4567" value={formData.phone} onChange={e=>setFormData({...formData, phone: e.target.value})}/>
        </div>
        <div className="form-group full">
          <label>주소</label>
          <input placeholder="예: 부산광역시 해운대구 우동 123-4" value={formData.address} onChange={e=>setFormData({...formData, address: e.target.value})}/>
        </div>
        <div className="form-group full">
          <label>대표 메뉴</label>
          <input placeholder="예: 돼지국밥, 밀면, 해물파전" value={formData.menu} onChange={e=>setFormData({...formData, menu: e.target.value})}/>
        </div>
        <div className="form-group full">
          <label>상세 소개</label>
          <textarea rows={3} placeholder="식당에 대한 설명을 입력하세요." value={formData.description} onChange={e=>setFormData({...formData, description: e.target.value})}/>
        </div>
        <div className="form-group">
          <label>위도 (Latitude)</label>
          <input type="number" step="any" value={formData.lat} onChange={e=>setFormData({...formData, lat: parseFloat(e.target.value)||0})}/>
        </div>
        <div className="form-group">
          <label>경도 (Longitude)</label>
          <input type="number" step="any" value={formData.lng} onChange={e=>setFormData({...formData, lng: parseFloat(e.target.value)||0})}/>
        </div>
        <div className="form-actions full">
          <button type="button" className="btn-cancel" onClick={()=>setShowModal(false)}>취소</button>
          <button type="submit" className="btn-submit">SQLite DB 저장하기</button>
        </div>
      </form>
    </div>
  </div>}
  </div>
}
