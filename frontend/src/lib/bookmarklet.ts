// 유저의 blablalink 세션으로 API를 호출해 원시 payload를 우리 앱에 넘기는
// 북마크릿. blablalink 페이지 컨텍스트에서 도는 것이 전제다 - 거기서만
// credentials:'include' fetch가 CORS를 통과한다(2026-07-19 실측).
//
// 계정 닉네임은 GetUserProfileBasicInfo의 `data.basic_info.nickname`에 있다
// (2026-07-25 실측; `role_name`도 같은 값이다). 한 단계 얕게 `data.nickname`을
// 읽으면 항상 undefined다.
//
// **이 조회는 최선 노력이다.** blablalink는 code 1300015("Requests are too
// frequent")로 이것만 거절하는데, 거절을 부르는 것은 우리 묶음이 아니라
// **ShiftyPad 화면 자신**이다: 그 화면은 뜨면서 프록시를 1.3초에 열세 번 부르고
// 그중 하나가 이 조회다. 유저가 공유 URL을 복사한 직후 북마크를 누르는 최초
// 동기화는 정확히 그 몇 초 안이라 늘 거절된다. 호출 하나짜리로 줄여도 거절되고,
// 로스터 조회는 같은 순간에 멀쩡히 통과한다(2026-08-09 실측).
//
// 그래서 재시도하지 않는다. **거절된 요청도 제한 창을 민다** - 15/30/60/120초
// 정적을 두고 다시 물어도 4분 내내 거절됐다. 세 번 더 묻는 것은 완화가 아니라
// 스스로 못 빠져나오게 만드는 악화다. 같은 이유로, 이 페이지가 **이미** 그
// 조회를 했으면 아예 묻지 않는다 - Resource Timing 기록은 문서마다 새로
// 시작하므로 시간 상수 없이 「이 화면이 이미 물었다」를 알 수 있다. 이 버퍼는
// 기본 250엔트리라 SPA가 그것을 넘기면 이름 조회 엔트리가 밀려나 PAGE_ASKED가
// false로 잘못 나올 수 있다 - 그러면 다시 물어 거절당하지만, 그 실패도 다른
// 거절과 똑같이 최선 노력 1회로 끝나고 화면은 유저에게 직접 이름을 붙이라고
// 안내하므로 해롭지는 않다.
//
// 이름을 못 받아도 그것은 실패가 아니다. 앱에서 계정 이름은 유저가 소유하는
// 라벨이고(types/profile.ts), 동기화는 그것이 비어 있을 때만 씨앗을 심는다.
// 한 계정에 한 번만 성공하면 되고, 그 뒤로는 `known.namedAreas`가 건너뛴다 -
// 단, `NAMED`는 이 북마크릿을 **만들 때**의 스냅샷이라 이미 설치된 북마크릿에는
// 반영되지 않는다. 이름을 붙인 뒤에도 그 북마크릿을 다시 복사해야 실제로
// 건너뛴다.
// 왜 비었는지는 payload의 `nickname_error`에 남긴다 - 값이 아니라 코드와 최상위
// 키 이름만 담으므로 계정 정보가 새지 않는다.
//
// 에러 코드 분기는 문자열 정규식이 아니라 `err.code` 숫자 비교로 한다. 메시지가
// 코드 뒤에 붙는 순간 `/:1302125$/`의 `$` 앵커가 빗나가고, 앵커를 넓히려 하면
// 템플릿 리터럴이 `\s`의 백슬래시를 먹어 생성된 소스에 `(s|$)`가 박힌다.
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

const OPEN_ID = /^\d{6,}$/

// 앱이 열려 있을 만한 포트들. `backend/app/desktop.py`의 SYNC_PORTS와 짝이고,
// 마지막 8000은 개발용(uvicorn 기본)이다 - 한쪽만 고치면 동기화가 조용히 안 된다.
export const LOCAL_SYNC_PORTS = [41573, 41574, 41575, 41576, 8000]

// 수집 부분. 두 빌더가 같은 것을 쓰므로 한 곳에 둔다 - 전송 방식만 다르다.
// `payload` 변수에 결과를 담고, 실패는 바깥 try/catch로 던진다.
//
// `call`은 호출 사이 최소 간격(GAP)을 둔다. 필요한지는 **재지 않았다** -
// 페이지 자신이 1.3초에 열세 번을 무간격으로 던져 전부 통과하는 것을 보면
// 아마 없어도 된다. 그래도 두는 이유는 이 파일이 **브라우저에 설치되는
// 물건이라 틀렸을 때 전 유저가 재설치해야** 해서다. 이름 조회의 거절과는
// **무관하다** - 그쪽은 간격으로 안 풀린다는 것이 실측됐다(위 헤더 참고).
/** 앱이 이 계정에 대해 이미 아는 것. 아는 서버만 조회하는 것은 속도 이득이고
 * (다섯 서버를 다 훑지 않는다), 이미 아는 이름을 다시 묻지 않는 것은 거절될
 * 조회를 아예 안 하는 것이다. */
export interface KnownAccount {
  /** 이 계정의 로스터가 있는 서버들. 비어 있으면 전부 훑는다. */
  areas: number[]
  /** 이미 이름을 아는 서버들. 그 서버에서는 이름 조회를 아예 건너뛴다 -
   * 이름은 계정당 한 번만 필요하고, 다시 묻는 것은 거절될 뿐이다. */
  namedAreas: number[]
}

const collectSource = (openId: string, known: KnownAccount): string => `
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const GAP=350;
let lastCall=0;
const call=async(ep,body)=>{
 const wait=GAP-(Date.now()-lastCall);
 if(wait>0)await sleep(wait);
 lastCall=Date.now();
 const r=await fetch('https://api.blablalink.com/api/game/proxy/Game/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'include'});
 const j=await r.json();
 if(j.code!==0){const e=new Error(ep+':'+j.code+(j.msg?' '+j.msg:''));e.code=j.code;throw e}
 return j.data};
const NAME_EP='GetUserProfileBasicInfo';
const PAGE_ASKED=performance.getEntriesByType('resource').some(e=>e.name.indexOf(NAME_EP)>=0);
const AREAS=[${(known.areas.length ? known.areas : [...SERVER_AREAS]).join(',')}];
const NAMED=[${known.namedAreas.join(',')}];
const found=[];let probeErr=null;
for(const a of AREAS){
 let owned=[];
 try{owned=(await call('GetUserCharacters',{intl_open_id:'${openId}',nikke_area_id:a})).characters||[]}catch(e){if(!probeErr&&e.code!==1302125)probeErr=e;owned=[]}
 if(owned.length)found.push({area:a,owned:owned})}
if(!found.length){if(probeErr)throw probeErr;throw new Error('이 계정에서 니케를 찾지 못했어요. 공유 URL이 맞는지 확인해주세요.')}
const servers=[];
for(const f of found){
 const base={intl_open_id:'${openId}',nikke_area_id:f.area};
 const detail=await call('GetUserCharacterDetails',{...base,name_codes:f.owned.map(c=>c.name_code)});
 const outpost=await call('GetUserProfileOutpostInfo',{...base});
 let nickErr='',nick='';
 if(NAMED.indexOf(f.area)>=0){}
 else if(PAGE_ASKED){nickErr='page already asked'}
 else{
  let basic=null;
  try{basic=await call(NAME_EP,{...base})}catch(e){nickErr=String(e&&e.message||e)}
  const bi=(basic&&basic.basic_info)||{};
  nick=bi.nickname||bi.role_name||'';
  if(!nick&&!nickErr)nickErr='shape:'+Object.keys(basic||{}).join('|');}
 servers.push({area:f.area,nickname:nick,nickname_error:nick?'':nickErr,owned:f.owned,character_details:detail.character_details||[],recycle_room_researches:((outpost.outpost_info||{}).recycle_room_researches)||[],synchro_level:(outpost.outpost_info||{}).synchro_level})}
payload={open_id:'${openId}',servers:servers};`

// 실패 문구. 두 빌더가 같은 코드를 같은 말로 설명해야 한다.
const errorAlertSource = `
const m=String(err),c=err&&err.code;
alert(c===300001?'blablalink 로그인이 필요해요.':(c===1303005||c===1)?'공유 URL을 다시 확인해주세요.':'가져오기 실패: '+m)`

/**
 * 앱이 켜져 있는 로컬 서버로 로스터를 직접 보내는 북마크릿.
 *
 * 네이티브 창(WebView2)은 유저 브라우저와 별개라 `window.open`+postMessage가
 * 앱에 닿지 않는다. 대신 수집한 것을 `127.0.0.1`의 인박스로 POST하고 앱이
 * 가져간다. 2026-07-31 라이브 확인: https 페이지에서 loopback으로 나가는 요청은
 * 브라우저가 허용하며(안전한 출처로 친다), CORS 헤더만 서버가 내주면 된다.
 *
 * 포트를 훑는 이유는 앱이 비어 있는 첫 포트를 잡기 때문이다.
 */
const NOTHING_KNOWN: KnownAccount = { areas: [], namedAreas: [] }

export const buildLocalSyncBookmarklet = (
  openId: string,
  known: KnownAccount = NOTHING_KNOWN,
): string => {
  if (!OPEN_ID.test(openId)) {
    throw new Error(`open ID(${JSON.stringify(openId)})는 숫자로만 이뤄져야 해요.`)
  }
  const source = `(async()=>{
if(location.origin!=='${BLABLALINK_ORIGIN}'){alert('blablalink 페이지에서 눌러주세요.');return}
let payload=null;
try{${collectSource(openId, known)}
 let sent=false;
 for(const p of ${JSON.stringify(LOCAL_SYNC_PORTS)}){
  try{const r=await fetch('http://127.0.0.1:'+p+'/api/sync-inbox',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(r.ok){sent=true;break}}catch(e){}}
 alert(sent?'로스터를 보냈어요. RapiLab 창에서 확인해주세요.':'RapiLab을 찾지 못했어요. 앱을 켜고 다시 눌러주세요.')
}catch(err){${errorAlertSource}}
})()`
  return 'javascript:' + encodeURIComponent(source)
}
