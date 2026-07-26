// blablalink 동기화 안내: 공유 URL을 어디서 얻는지부터 계정이 여러 개일 때까지.
// 펼침/접힘은 SyncRosterPanel이 소유하고 여기는 문안만 담는다.
//
// 1~2단계에 스크린샷이 붙는 이유: blablalink의 공유 아이콘과 "링크 복사하기"는
// 둘 다 라벨이 없어, 글만으로는 나란히 있는 방패/물음표 아이콘과 구별해 지목할
// 방법이 없다.

interface SyncHelpProps {
  /** 토글 버튼의 aria-controls가 가리키는 id. */
  id: string
  hidden: boolean
}

export function SyncHelp({ id, hidden }: SyncHelpProps) {
  return (
    <div className="sync-help" id={id} hidden={hidden}>
      <ol className="sync-help__steps">
        <li>
          blablalink <strong>SHIFTYPAD</strong> 페이지 우측 상단의 공유 아이콘을
          눌러요.
          <img
            className="sync-help__shot"
            src="/help/shiftypad-share-button.png"
            alt="SHIFTYPAD 페이지 우측 상단, 방패와 물음표 아이콘 오른쪽에 있는 공유 아이콘"
          />
        </li>
        <li>
          <strong>링크 복사하기</strong>를 눌러 URL을 복사해요.
          <img
            className="sync-help__shot"
            src="/help/shiftypad-copy-link.png"
            alt="공유하기 창에서 Facebook·Twitter·Naver·whatsApp 오른쪽에 있는 링크 복사하기 버튼"
          />
        </li>
        <li>복사한 URL을 아래 칸에 붙여넣어요.</li>
        <li>
          나타나는 <strong>니케 로스터 동기화</strong> 링크를 브라우저 북마크 바로
          드래그해요. 북마크 바가 안 보이면 Ctrl+Shift+B로 켤 수 있어요.
        </li>
        <li>
          blablalink에 로그인한 상태에서 그 북마크를 눌러요. 로스터가 새 탭에서
          열려요.
        </li>
      </ol>

      <h3 className="sync-help__heading">다시 동기화할 때</h3>
      <p className="sync-help__text">
        북마크만 다시 누르면 돼요. 공유 URL을 또 붙여넣을 필요는 없어요.
      </p>

      <h3 className="sync-help__heading">계정이 여러 개일 때</h3>
      <p className="sync-help__text">
        계정마다 북마크가 따로 필요해요 — 북마크릿에는 그 계정의 ID가 들어 있어요.
      </p>
      <ol className="sync-help__steps">
        <li>
          추가할 계정의 SHIFTYPAD에서 공유 URL을 복사해 위 1~4단계를 다시 해요.
        </li>
        <li>
          이름이 다 똑같이 "니케 로스터 동기화"라서, 북마크 이름을 계정 이름으로
          바꿔두면 헷갈리지 않아요.
        </li>
        <li>
          <strong>그 계정으로 blablalink에 로그인한 상태에서</strong> 해당 북마크를
          눌러요.
        </li>
      </ol>
      <p className="sync-help__text">
        동기화한 계정은 위쪽 <strong>계정</strong> 드롭다운에서 전환해요. 계정별
        로스터와 추천 결과는 섞이지 않아요.
      </p>
    </div>
  )
}
