// 보관물이 언제 저장됐는지. 목록 두 곳(SavedRunList, ImportRunButton)이 같은
// 모양으로 말해야 해서 한곳에 둔다.

export const savedAtLabel = (savedAt: number): string => {
  const at = new Date(savedAt)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(at.getMonth() + 1)}-${pad(at.getDate())} ${pad(at.getHours())}:${pad(at.getMinutes())}`
}
