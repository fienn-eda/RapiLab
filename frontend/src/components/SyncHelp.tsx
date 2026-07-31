// blablalink 동기화 안내: 공유 URL을 어디서 얻는지부터 계정이 여러 개일 때까지.
// 펼침/접힘은 SyncRosterPanel이 소유하고 문안은 lib/helpText.ts가 가지므로,
// 여기가 하는 일은 그 둘을 화면 구조에 얹는 것뿐이다.

import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

interface SyncHelpProps {
  /** 토글 버튼의 aria-controls가 가리키는 id. */
  id: string
  hidden: boolean
}

const COPY = HELP.syncHelp

export function SyncHelp({ id, hidden }: SyncHelpProps) {
  return (
    <div className="sync-help" id={id} hidden={hidden}>
      <ol className="sync-help__steps">
        {COPY.steps.map((step) => (
          <li key={step.text}>
            <HelpText>{step.text}</HelpText>
            {step.shot && (
              <img
                className="sync-help__shot"
                src={`/help/${step.shot.src}`}
                alt={step.shot.alt}
                width={step.shot.width}
                height={step.shot.height}
              />
            )}
          </li>
        ))}
      </ol>

      <h3 className="sync-help__heading">{COPY.resyncHeading}</h3>
      <p className="sync-help__text">
        <HelpText>{COPY.resync}</HelpText>
      </p>

      <h3 className="sync-help__heading">{COPY.multiAccountHeading}</h3>
      <p className="sync-help__text">
        <HelpText>{COPY.multiAccount}</HelpText>
      </p>
      <ol className="sync-help__steps">
        {COPY.multiAccountSteps.map((step) => (
          <li key={step}>
            <HelpText>{step}</HelpText>
          </li>
        ))}
      </ol>

      <p className="sync-help__text">
        <HelpText>{COPY.switchNote}</HelpText>
      </p>
    </div>
  )
}
