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
  useEffect(()=>{
    if (lang === 'ko') { setTranslations({}); setTranslationNames({}); return }
    api(`restaurants/translations?lang=${lang}`)
      .then(r=>r.ok?r.json():Promise.reject())
      .then(applyTranslations)
      .catch(()=>{ setTranslations({}); setTranslationNames({}) })
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
  const districts=useMemo(()=>Array.from(new Set(items.map(x=>x.district).filter(Boolean))).sort((a,b)=>a.localeCompare(b,'ko')), [items])
  const display=useMemo(()=>{ const words=query.trim().toLowerCase(); let r=items.filter(x=> { const locale=localized(x); return (!district || x.district===district) && (!words || [locale.name,x.name,x.district,locale.address,x.address,x.menu,locale.description,x.description].join(' ').toLowerCase().includes(words)) }); if(view==='favorites') r=r.filter(x=>x.favorite); const localizedItems=r.map(localized); return sort ? [...localizedItems].map(x=>({...x,distance:dist(position[0],position[1],x.lat,x.lng)})).sort((a,b)=>(a.distance||0)-(b.distance||0)) : localizedItems },[items,query,district,sort,view,position,translations,translationNames])
  const visibleItems = showAll ? display : display.slice(0, 24)
  const selectedDisplay = selected ? localized(selected) : null
  const syncTranslations = async (v: Exclude<Lang, 'ko'>) => {
    try {
      const syncResponse = await api(`restaurants/translations/sync?lang=${v}`, { method: 'POST' })
      if (!syncResponse.ok) throw new Error('translation sync failed')
      const response = await api(`restaurants/translations?lang=${v}`)
      if (!response.ok) throw new Error('translation load failed')
      applyTranslations(await response.json())
    } catch {
      // The previously saved official translations remain visible if the source is unavailable.
    }
  }
  const changeLang=(v:Lang)=>{
    setLang(v)
    if (v !== 'ko') syncTranslations(v)
    api('preferences',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:'lang',value:v})}).catch(()=>{})
  }
  const changeDistrict=(v:string)=>{ setDistrict(v); setShowAll(false); api('preferences',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:'district',value:v})}).catch(()=>{}) }
  useEffect(()=>{ setShowAll(false) }, [query, view, sort])
  const toggle=async(item:Restaurant)=>{ const method=item.favorite?'DELETE':'POST'; try { const r=await api(`favorites/${item.id}`,{method}); if(!r.ok) throw new Error(); const updated={...item,favorite:item.favorite?0:1}; setItems(old=>old.map(x=>x.id===item.id?updated:x)); setSelected(current=>current?.id===item.id?updated:current) } catch { setError('save') } }
  const locate=()=>{ if(!navigator.geolocation){ setSort(true); return } navigator.geolocation.getCurrentPosition(p=>{setPosition([p.coords.latitude,p.coords.longitude]);setSort(true)},()=>setSort(true),{timeout:6000}) }
  const submit=(e:React.FormEvent)=>{e.preventDefault(); if(query.trim()) api('searches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})}).catch(()=>{})}
  return <div className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">●</span><div><b>{t.title}</b><small>{t.sub}</small></div></div><nav><button className={view==='map'?'active':''} onClick={()=>setView('map')}>⌖ {t.map}</button><button className={view==='favorites'?'active':''} onClick={()=>setView('favorites')}>♥ {t.fav}<em>{items.filter(x=>x.favorite).length}</em></button></nav><div className="language" aria-label="언어 선택">{(['ko','en','ja'] as Lang[]).map(l=><button key={l} onClick={()=>changeLang(l)} className={lang===l?'active':''}>{l==='ko'?'KO':l==='en'?'EN':'日本語'}</button>)}</div></header>
    <main><section className="map-stage"><MapView restaurants={display} selected={selectedDisplay} onSelect={setSelected} lang={lang}/><div className="controls"><form className="search" onSubmit={submit}><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t.search}/><button type="submit" aria-label="검색">→</button></form><div className="tool-row"><button onClick={()=>setSort(!sort)} className={sort?'selected':''}>↕ {t.distance}</button><details><summary>⌖ {t.filter}{district?`: ${district}`:''}</summary><div className="filter-menu"><button className={!district?'selected':''} onClick={()=>changeDistrict('')}>{t.all}</button>{districts.map(d=><button key={d} className={district===d?'selected':''} onClick={()=>changeDistrict(d)}>{d}</button>)}</div></details><button onClick={locate}>◎ {t.near}</button></div></div>
      <div className="map-caption"><span className="pulse"></span>{sort?t.location:t.basedOn} · <b>{display.length}{t.result}</b></div>
      {selectedDisplay && <aside className="detail-card"><button className="close" onClick={()=>setSelected(null)} aria-label="닫기">×</button><span className="category">{selectedDisplay.district || t.district}</span><h2>{selectedDisplay.name}</h2>{lang !== 'ko' && selectedDisplay.source_name && <p className="translation-note">{selectedDisplay.source_name}</p>}<p className="detail-menu">{t.menu} · {selectedDisplay.menu || t.noMenu}</p><p>{selectedDisplay.address}{selectedDisplay.address_detail ? ` ${selectedDisplay.address_detail}`:''}</p>{lang !== 'ko' && selectedDisplay.source_address && <p className="translation-note">{selectedDisplay.source_address}</p>}{selectedDisplay.phone&&<p><b>{t.phone}</b> · <a href={`tel:${selectedDisplay.phone.replace(/[^0-9+]/g,'')}`}>{selectedDisplay.phone}</a></p>}{selectedDisplay.hours&&<p><b>{t.hours}</b> · {selectedDisplay.hours}</p>}<p className="detail-description">{selectedDisplay.description || t.noDescription}</p>{lang !== 'ko' && selectedDisplay.source_description && <p className="translation-note">{selectedDisplay.source_description}</p>}{selectedDisplay.homepage_url&&<a className="homepage-link" href={selectedDisplay.homepage_url} target="_blank" rel="noreferrer">↗ {lang === 'ko' ? '공식 안내 보기' : lang === 'en' ? 'Visit website' : '公式案内を見る'}</a>}{lang !== 'ko' && !selectedDisplay.translation_available && <p className="translation-note">{lang === 'en' ? 'Official English details are not available for this restaurant yet.' : 'この店舗の公式日本語情報は準備中です。'}</p>}<button className="save-button" onClick={()=>toggle(selectedDisplay)}>{selectedDisplay.favorite?'♥ '+t.saved:'♡ '+t.save}</button></aside>}
    </section>
    <section className="list-panel"><div className="list-heading"><div><p className="eyebrow">{t.source.toUpperCase()}</p><h1>{view==='favorites'?t.fav:t.list}</h1></div><span>{display.length}{t.result}</span></div>{loading?<div className="state">{t.loading}</div>:error?<div className="state error">{t.error}<button onClick={load}>{t.retry}</button></div>:display.length===0?<div className="state">{t.empty}</div>:<><div className="card-grid">{visibleItems.map(item=><RestaurantCard key={item.id} item={item} lang={lang} onToggle={toggle} onSelect={setSelected}/>)}</div>{display.length>visibleItems.length&&<button className="more-button" onClick={()=>setShowAll(true)}>{lang==='ko'?`맛집 ${display.length - visibleItems.length}곳 더 보기`:lang==='en'?`Show ${display.length - visibleItems.length} more restaurants`:`さらに${display.length - visibleItems.length}件を見る`}</button>}</>}</section>
  </main></div>
}
