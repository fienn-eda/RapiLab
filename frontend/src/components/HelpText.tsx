// `lib/helpText.ts`의 문구를 그린다. `**...**`로 감싼 부분만 굵게 나오고,
// 나머지는 글자 그대로다.
//
// 마크다운 파서를 들이지 않는 이유: 안내 문구에 필요한 표현이 강조 하나뿐이다.
// 링크나 목록이 필요해지면 그때 이 자리에서 다시 판단한다.

interface HelpTextProps {
  children: string
}

export function HelpText({ children }: HelpTextProps) {
  // 캡처 그룹이 있는 split은 구분자도 결과에 남긴다 - 홀수 자리가 별표 안이다.
  const parts = children.split(/\*\*(.+?)\*\*/)

  return (
    <>
      {parts.map((part, index) =>
        index % 2 === 1 ? <strong key={index}>{part}</strong> : part,
      )}
    </>
  )
}
