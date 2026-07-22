// Kebab-cases an in-game display name into our character_slug convention.
// Shared by the collector import path (rosterImport.ts) for units whose
// resource_id doesn't resolve through the identity map.

export const deriveSlug = (nameEn: string): string =>
  nameEn
    .toLowerCase()
    .replace(/[()]/g, '')
    .replace(/:/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/ /g, '-')
