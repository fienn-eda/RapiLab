// 유저의 blablalink 세션으로 4개 API를 호출해 원시 payload를 우리 앱에 넘기는
// 북마크릿. blablalink 페이지 컨텍스트에서 도는 것이 전제다 - 거기서만
// credentials:'include' fetch가 CORS를 통과한다(2026-07-19 실측).
//
// 계정 닉네임은 GetUserProfileBasicInfo의 `data.basic_info.nickname`에 있다
// (2026-07-25 실측; `role_name`도 같은 값을 담는다). 한 단계 얕게 `data.nickname`을
// 읽으면 항상 undefined라 화면이 UID로 폴백한다. 이 호출만은 실패해도 삼킨다 -
// 닉네임은 표시용 부가 정보인데, 이 엔드포인트가 code 1303005("user has not bind
// role_id")로 떨어지는 것이 관측된 이상 그 실패가 로스터 싱크 전체를 죽여선 안 된다.
//
// 한 계정이 여러 서버에 로스터를 가질 수 있으므로 다섯 서버를 모두 조회한다.
// 어느 것을 쓸지는 앱이 정한다 - 여기서는 니케가 있는 서버를 후보로 올리는
// 것까지만 한다. 후보를 찾는 첫 단계(GetUserCharacters)만 서버별로 실패를
// 감싼다: 1303002("proxy.GetUserShiftyspadPrivacy error")가 간헐적으로
// 관측됐고, 그것이 나머지 서버를 후보에서 찾는 것까지 막아선 안 된다. 일단
// 후보가 된 서버의 상세/거점 조회(GetUserCharacterDetails,
// GetUserProfileOutpostInfo)는 감싸지 않는다 - 여기서 실패하면 동기화 전체를
// 중단시킨다. 그 서버만 조용히 빼고 나머지로 계속 진행하면, 유저가 알아챌
// 방법이 없는 반쪽짜리 로스터를 보내게 된다. 눈에 띄는 실패를 내고 재시도를
// 맡기는 쪽이 더 안전하다.
//
// 1302125("get info list err")는 그 계정이 그 서버에 로스터가 없다는 뜻일
// 뿐이다 - 다섯 중 넷에서는 정상이고, 로스터가 아예 없는 계정에서는 보통 가장
// 먼저 기록되는 에러다. 그래서 probeErr에는 담지 않는다: 다섯 서버 모두
// 1302125로 끝나면 "니케를 찾지 못했어요" 문구를 그대로 보여줘야 하고, 담아
// 두면 그 문구 대신 아무 정보도 없는 원시 코드가 새어나간다. 300001(로그인
// 필요)·1303005(공유 URL 오류) 같은, 실제로 유용한 코드는 그대로 담아 바깥
// catch의 alert 분기로 보낸다.
//
// 외부 스크립트 로딩은 blablalink CSP의 script-src에 막힐 공산이 커서 로직이
// 인라인으로 강제되고, 따라서 이 코드를 바꾸면 전 유저가 북마크를 다시 깔아야
// 한다. 판단·조립·검증은 전부 서버로 미루고 여기는 얇게 유지할 것.

import { SERVER_AREAS } from '../types/server'

export const BLABLALINK_ORIGIN = 'https://www.blablalink.com'
export const READY_MESSAGE = 'nikke-sync-ready'
export const PAYLOAD_MESSAGE = 'nikke-sync-payload'

const OPEN_ID = /^\d{6,}$/

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
    throw new Error(`open ID(${JSON.stringify(openId)})는 숫자로만 이뤄져야 해요.`)
  }
  if (!isPlainHttpOrigin(appOrigin)) {
    throw new Error(
      `앱 주소(${JSON.stringify(appOrigin)})가 따옴표 없는 올바른 http(s) 주소가 아니에요.`,
    )
  }
  // 클릭의 transient activation은 짧게 유지된다(크롬 5초, 파이어폭스는 프라미스
  // 연속 안 window.open에 더 엄격). 세 API 호출을 먼저 기다리면 그 사이
  // activation이 만료돼 정상 사용자도 팝업 차단을 겪는다 - 그래서 window.open과
  // message 리스너 등록은 첫 await 전, 하나의 동기 블록 안에서 끝낸다.
  const source = `(async()=>{
if(location.origin!=='${BLABLALINK_ORIGIN}'){alert('blablalink 페이지에서 눌러주세요.');return}
const w=window.open('${appOrigin}','nikke-deck-builder');
if(!w){alert('팝업이 차단됐어요. 차단을 해제하고 다시 눌러주세요.');return}
let ready=false,payload=null;
const send=()=>{if(ready&&payload){w.postMessage({type:'${PAYLOAD_MESSAGE}',payload:payload},'${appOrigin}');window.removeEventListener('message',h)}};
const h=e=>{if(e.source===w&&e.origin==='${appOrigin}'&&e.data&&e.data.type==='${READY_MESSAGE}'){ready=true;send()}};
window.addEventListener('message',h);
const call=async(ep,body)=>{
 const r=await fetch('https://api.blablalink.com/api/game/proxy/Game/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'include'});
 const j=await r.json();
 if(j.code!==0)throw new Error(ep+':'+j.code);
 return j.data};
const AREAS=[${SERVER_AREAS.join(',')}];
try{
 const found=[];let probeErr=null;
 for(const a of AREAS){
  let owned=[];
  try{owned=(await call('GetUserCharacters',{intl_open_id:'${openId}',nikke_area_id:a})).characters||[]}catch(e){if(!probeErr&&!/:1302125$/.test(String(e)))probeErr=e;owned=[]}
  if(owned.length)found.push({area:a,owned:owned})}
 if(!found.length){if(probeErr)throw probeErr;throw new Error('이 계정에서 니케를 찾지 못했어요. 공유 URL이 맞는지 확인해주세요.')}
 const servers=[];
 for(const f of found){
  const base={intl_open_id:'${openId}',nikke_area_id:f.area};
  const detail=await call('GetUserCharacterDetails',{...base,name_codes:f.owned.map(c=>c.name_code)});
  const outpost=await call('GetUserProfileOutpostInfo',{...base});
  const basic=await call('GetUserProfileBasicInfo',{...base}).catch(()=>null);
  const bi=(basic&&basic.basic_info)||{};
  servers.push({area:f.area,nickname:bi.nickname||bi.role_name||'',owned:f.owned,character_details:detail.character_details||[],recycle_room_researches:((outpost.outpost_info||{}).recycle_room_researches)||[]})}
 payload={open_id:'${openId}',servers:servers};
 send()
}catch(err){
 window.removeEventListener('message',h);
 const m=String(err);
 alert(m.indexOf('300001')>=0?'blablalink 로그인이 필요해요.':(m.indexOf('1303005')>=0||/:1$/.test(m))?'공유 URL을 다시 확인해주세요.':'가져오기 실패: '+m)}
})()`
  return 'javascript:' + encodeURIComponent(source)
}
