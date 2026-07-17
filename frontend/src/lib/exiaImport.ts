// Parses an ExiaInvasion export (blablalink roster JSON) into editable NikkeDrafts.
// Only the fields the export carries are mapped; ATK/HP/DEF and cube stay manual.
// The cookie/game_uid fields in the export are credentials and are never read.

// name_en (short in-game name) -> our character_slug, for the cases where the
// kebab-cased name does not already match our slug. Derived-slug keyed.
const SLUG_ALIASES: Record<string, string> = {
  rei: 'rei-ayanami',
  'rei-tentative-name': 'rei-ayanami-tentative-name',
  ada: 'ada-wong',
  jill: 'jill-valentine',
  'asuka-wille': 'asuka-shikinami-langley-wille',
  soline: 'soline-frost-ticket',
  marciana: 'marciana-marine-study',
  takina: 'takina-inoue',
  chisato: 'chisato-nishikigi',
}

export const deriveSlug = (nameEn: string): string =>
  nameEn
    .toLowerCase()
    .replace(/[()]/g, '')
    .replace(/:/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/ /g, '-')

export const resolveSlug = (nameEn: string): string => {
  const derived = deriveSlug(nameEn)
  return SLUG_ALIASES[derived] ?? derived
}
