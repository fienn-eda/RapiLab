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

/** The name with a Favorite Item (애장품) heart appended.
 *
 * For the text-only places a badge cannot go: deck rosters, the bench line and
 * the per-deck diff all join names into a single string, so the marker has to
 * BE part of the name there. Where a portrait is drawn - the roster card, the
 * palette chip - FavoriteItemBadge sits on the art instead, and the name is
 * left plain so the heart is not shown twice. */
export const withFavoriteItem = (name: string, equipped?: boolean): string =>
  equipped ? `${name} ♥` : name
