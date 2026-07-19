// 유저의 blablalink 세션으로 3개 API를 호출해 원시 payload를 우리 앱에 넘기는
// 북마크릿. blablalink 페이지 컨텍스트에서 도는 것이 전제다 - 거기서만
// credentials:'include' fetch가 CORS를 통과한다(2026-07-19 실측).
//
// 외부 스크립트 로딩은 blablalink CSP의 script-src에 막힐 공산이 커서 로직이
// 인라인으로 강제되고, 따라서 이 코드를 바꾸면 전 유저가 북마크를 다시 깔아야
// 한다. 판단·조립·검증은 전부 서버로 미루고 여기는 얇게 유지할 것.

export const BLABLALINK_ORIGIN = 'https://www.blablalink.com'
export const READY_MESSAGE = 'nikke-sync-ready'
export const PAYLOAD_MESSAGE = 'nikke-sync-payload'

const OPEN_ID = /^\d+$/

// 생성된 소스에 그대로 splice되므로 따옴표가 섞이면 문법이 깨지거나 주입이 된다.
// origin 형태(경로/쿼리/프래그먼트 없음, http(s)만)까지 확인해 http 문자열
// 이스케이퍼 없이 저렴하게 막는다.
const isPlainHttpOrigin = (value: string): boolean => {
  if (/['"]/.test(value)) return false
  try {
    const url = new URL(value)
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.origin === value
  } catch {
    return false
  }
}

export const buildBookmarklet = (openId: string, appOrigin: string): string => {
  if (!OPEN_ID.test(openId)) {
    throw new Error(`buildBookmarklet: openId must be digits only, got ${JSON.stringify(openId)}`)
  }
  if (!isPlainHttpOrigin(appOrigin)) {
    throw new Error(
      `buildBookmarklet: appOrigin must be a plain http(s) origin with no quotes, got ${JSON.stringify(appOrigin)}`,
    )
  }
  const source = `(async()=>{
if(location.origin!=='${BLABLALINK_ORIGIN}'){alert('blablalink 페이지에서 눌러주세요.');return}
const call=async(ep,body)=>{
 const r=await fetch('https://api.blablalink.com/api/game/proxy/Game/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'include'});
 const j=await r.json();
 if(j.code!==0)throw new Error(ep+':'+j.code);
 return j.data};
const base={intl_open_id:'${openId}',nikke_area_id:81};
try{
 const owned=(await call('GetUserCharacters',{...base})).characters||[];
 const detail=await call('GetUserCharacterDetails',{...base,name_codes:owned.map(c=>c.name_code)});
 const outpost=await call('GetUserProfileOutpostInfo',{...base});
 const payload={owned:owned,character_details:detail.character_details||[],recycle_room_researches:((outpost.outpost_info||{}).recycle_room_researches)||[]};
 let w;
 window.addEventListener('message',e=>{
  if(w&&e.origin==='${appOrigin}'&&e.data&&e.data.type==='${READY_MESSAGE}'){
   w.postMessage({type:'${PAYLOAD_MESSAGE}',payload:payload},'${appOrigin}')}});
 w=window.open('${appOrigin}');
 if(!w){alert('팝업이 차단됐어요. 차단을 해제하고 다시 눌러주세요.');return}
}catch(err){
 const m=String(err);
 alert(m.indexOf('300001')>=0?'blablalink 로그인이 필요해요.':(m.indexOf('1303005')>=0||m.indexOf(':1')>=0)?'공유 URL을 다시 확인해주세요.':'가져오기 실패: '+m)}
})()`
  return 'javascript:' + encodeURIComponent(source)
}
