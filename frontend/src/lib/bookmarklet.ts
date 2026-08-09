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
// 다만 삼키되 **왜 비었는지는 payload에 적어 보낸다**(`nickname_error`). 2026-08-09에
// 세 계정(JP 둘·KR 하나)이 전부 UID로 표시되는 것이 보고됐는데, 앱은 닉네임이 든
// payload를 넣으면 그대로 저장하는 것이 확인됐다 - 즉 비는 곳은 이 호출이다.
// 실패 코드인지 응답 모양이 바뀐 것인지는 여기서 적어 보내야만 알 수 있다.
// 값이 아니라 코드나 최상위 키 이름만 담으므로 계정 정보가 새지 않는다.
//
// 그 첫 회신은 code 1300015였다 - 우리가 아는 코드가 아니고 문서도 없다. 같은
// `{intl_open_id, nikke_area_id}`로 나머지 셋은 전부 성공하므로 인증이나 파라미터
// 문제가 아니라 이 엔드포인트만의 것이고, 07-25에는 같은 요청이 동작했다.
// 그래서 `call`이 `j.msg`까지 실어 던지게 했다(코드만으로는 물어볼 곳이 없다).
//
// 그러면서 코드 분기를 **문자열 정규식에서 `err.code` 비교로** 바꿨다. 메시지가
// 코드 뒤에 붙는 순간 `/:1302125$/`의 `$` 앵커가 빗나가 "니케를 찾지 못했어요"
// 자리에 원시 코드가 새어나오는데(아래 문단이 경계하는 그 회귀), 앵커를 넓히려
// 하면 이번엔 **템플릿 리터럴이 `\s`의 백슬래시를 먹어** 생성된 소스에 `(s|$)`가
// 박힌다 - 테스트가 잡아주기 전까지 눈에 보이지 않는다. 코드를 숫자로 실어
// 보내면 두 함정이 한꺼번에 사라진다.
//
// 이름이 비었을 때는 이미 성공한 GetUserProfileOutpostInfo의 최상위 키도 같이
// 적는다. 거기에 이름이 들어 있다면 호출을 늘리지 않고 폴백을 만들 수 있고,
// 없다면 그 사실이 후보를 하나 지운다 - 어느 쪽이든 재설치 한 번을 아낀다.
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
const collectSource = (openId: string): string => `
const call=async(ep,body)=>{
 const r=await fetch('https://api.blablalink.com/api/game/proxy/Game/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'include'});
 const j=await r.json();
 if(j.code!==0){const e=new Error(ep+':'+j.code+(j.msg?' '+j.msg:''));e.code=j.code;throw e}
 return j.data};
const AREAS=[${SERVER_AREAS.join(',')}];
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
 let basic=null,nickErr='';
 try{basic=await call('GetUserProfileBasicInfo',{...base})}catch(e){nickErr=String(e&&e.message||e)}
 const bi=(basic&&basic.basic_info)||{};
 const nick=bi.nickname||bi.role_name||'';
 if(!nick&&!nickErr)nickErr='shape:'+Object.keys(basic||{}).join('|');
 if(!nick)nickErr+=' | outpost:'+Object.keys(outpost||{}).join('|')+' / '+Object.keys(outpost.outpost_info||{}).join('|');
 servers.push({area:f.area,nickname:nick,nickname_error:nick?'':nickErr,owned:f.owned,character_details:detail.character_details||[],recycle_room_researches:((outpost.outpost_info||{}).recycle_room_researches)||[]})}
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
export const buildLocalSyncBookmarklet = (openId: string): string => {
  if (!OPEN_ID.test(openId)) {
    throw new Error(`open ID(${JSON.stringify(openId)})는 숫자로만 이뤄져야 해요.`)
  }
  const source = `(async()=>{
if(location.origin!=='${BLABLALINK_ORIGIN}'){alert('blablalink 페이지에서 눌러주세요.');return}
let payload=null;
try{${collectSource(openId)}
 let sent=false;
 for(const p of ${JSON.stringify(LOCAL_SYNC_PORTS)}){
  try{const r=await fetch('http://127.0.0.1:'+p+'/api/sync-inbox',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(r.ok){sent=true;break}}catch(e){}}
 alert(sent?'로스터를 보냈어요. RapiLab 창에서 확인해주세요.':'RapiLab을 찾지 못했어요. 앱을 켜고 다시 눌러주세요.')
}catch(err){${errorAlertSource}}
})()`
  return 'javascript:' + encodeURIComponent(source)
}
