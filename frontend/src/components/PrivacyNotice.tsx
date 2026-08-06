// 화면 맨 아래의 개인정보 안내. 문안은 lib/helpText.ts가 갖고, 여기는 그것을
// 접이식으로 얹기만 한다.
//
// 바깥 링크가 아니라 앱 안에서 펼치는 이유가 둘 있다. 이 앱은 네이티브 창이라
// 주소창도 뒤로가기도 없어서, 바깥 주소로 넘어가면 돌아올 방법이 없다. 그리고
// "이 앱이 내 정보를 어디로 보내나"를 확인하려는 사람이 그 답을 읽으려고
// 네트워크 요청을 해야 하는 것은 앞뒤가 맞지 않는다 - 이 글은 오프라인에서도
// 읽혀야 한다.

import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

const COPY = HELP.privacy

export function PrivacyNotice() {
  return (
    <details className="privacy">
      <summary className="privacy__summary">개인정보 처리방침</summary>

      <div className="privacy__body">
        <p className="privacy__text">
          <HelpText>{COPY.lede}</HelpText>
        </p>

        {COPY.sections.map((section) => (
          <div key={section.heading}>
            <h3 className="privacy__heading">{section.heading}</h3>
            <ul className="privacy__items">
              {section.items.map((item) => (
                <li key={item}>
                  <HelpText>{item}</HelpText>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <p className="privacy__text">
          <HelpText>{COPY.closing}</HelpText>
        </p>
        <p className="privacy__updated">최종 수정 {COPY.updated}</p>
      </div>
    </details>
  )
}
