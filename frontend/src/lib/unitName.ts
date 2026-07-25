// Slug -> the name a player would say out loud.
//
// GET /api/supported-units carries a real name for every slug the engine can
// simulate, and that is always preferred. Everything else - the units a
// player owns that the engine does not support yet - has no name source in
// the frontend at all, so the name is derived from the slug rather than
// shipping a second character directory just to label them.

/** Uppercases the first LETTER of a word, not its first character, so a slug
 * that starts with a digit still reads right: `2b` -> `2B`, not `2b`. */
const titleCaseWord = (word: string): string => word.replace(/[a-z]/, (c) => c.toUpperCase())

/** `ada-wong` -> `Ada Wong`. Good enough to label a unit; it will not
 * reproduce punctuation or casing the official name has. */
export const nameFromSlug = (slug: string): string =>
  slug.split('-').filter(Boolean).map(titleCaseWord).join(' ')

/** The backend's name for a supported slug, else one derived from the slug. */
export const displayName = (slug: string, names: ReadonlyMap<string, string>): string =>
  names.get(slug) ?? nameFromSlug(slug)
