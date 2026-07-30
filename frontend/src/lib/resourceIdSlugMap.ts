// blablalink resource_id -> our encoded character_slug, for the collector
// (roster.json) import path. Decoupled from name-derived aliasing so base/variant and
// same-name collisions resolve unambiguously (each game unit, including each SSR
// variant, has its own resource_id).
//
// IDENTITY vs INVESTMENT are deliberately separate:
//   RESOURCE_ID_TO_SLUG holds the *base* slug and never encodes user investment.
//   A dual-slot unit (base + "-signature" encodings) shares ONE resource_id between
//   both forms — Drake is resource_id 101 whether or not his Favorite Item is owned —
//   so no id-keyed table can distinguish them. Ownership comes from the roster
//   (each unit's `favorite_item` flag), never from this table.
//
// Values are a subset of the backend's ENCODED_SLUGS, and DUAL_SLOT_BASES must match
// the encoded base/-signature pairs; both are enforced by the backend test
// backend/tests/test_resource_id_slug_map.py.
//
// Ids absent here are units we have not encoded (or do not own) -> excluded from
// recommendation, kept visible in the roster draft via raw deriveSlug.
//
// A mode-variant unit (Cinderella: Crystal Wave's MG/Snipe pre-battle choice - see
// MODE_VARIANTS in the backend registry) maps its id to the BASE slug, not either
// mode slug: the backend fans that one base slug out to every candidate mode slug,
// so the base is the map's legal value even though it is never itself encoded.
export const RESOURCE_ID_TO_SLUG: Record<number, string> = {
  15: 'anis-sparkling-summer', // Anis: Sparkling Summer
  16: 'rapi-red-hood', // Rapi: Red Hood
  17: 'anis-star', // Anis: Star
  18: 'neon-vision-eye', // Neon: Vision Eye (14 = Neon: Blue Ocean, not encoded)
  32: 'miranda', // Miranda — dual-slot base; promoted per the roster
  43: 'd-killer-wife', // D: Killer Wife
  73: 'brid-silent-track', // Brid: Silent Track
  74: 'soline-frost-ticket', // Soline: Frost Ticket (71 = base Soline, not encoded)
  75: 'diesel-winter-sweets', // Diesel: Winter Sweets - base slug; fans out to -intro/-highlight (MODE_VARIANTS)
  80: 'centi', // Centi — dual-slot base; promoted per the roster
  82: 'liter', // Liter
  100: 'laplace', // Laplace — dual-slot base; promoted per the roster
  101: 'drake', // Drake — dual-slot base; promoted per the roster
  102: 'maxwell', // Maxwell
  103: 'laplace-ultimate-hero', // Laplace: Ultimate Hero
  105: 'maxwell-ordinary-mechanic', // Maxwell: Ordinary Mechanic
  140: 'sugar', // Sugar — dual-slot base; promoted per the roster
  143: 'milk-blooming-bunny', // Milk: Blooming Bunny
  150: 'julia', // Julia — dual-slot base; promoted per the roster
  162: 'mihara-bonding-chain', // Mihara: Bonding Chain
  170: 'privaty', // Privaty — dual-slot base; promoted per the roster
  182: 'guillotine-winter-slayer', // Guillotine: Winter Slayer
  183: 'maiden-ice-rose', // Maiden: Ice Rose
  192: 'tove', // Tove — dual-slot base; promoted per the roster
  194: 'ludmilla-winter-owner', // Ludmilla: Winter Owner
  220: 'snow-white', // Snow White (224 = Snow White: Innocent Days, not encoded)
  223: 'nayuta', // Nayuta
  225: 'scarlet-black-shadow', // Scarlet: Black Shadow (222 = base Scarlet, not encoded)
  231: 'isabel', // Isabel
  234: 'dorothy-serendipity', // Dorothy: Serendipity
  260: 'modernia', // Modernia
  262: 'liberalio', // Liberalio
  270: 'blanc', // Blanc
  271: 'noir', // Noir
  272: 'rouge', // Rouge
  280: 'rosanna', // Rosanna — dual-slot base; a different unit from 283 Rosanna: Chic Ocean
  281: 'moran', // Moran — dual-slot base; promoted per the roster
  283: 'rosanna-chic-ocean', // Rosanna: Chic Ocean
  284: 'sakura-bloom-in-summer', // Sakura: Bloom in Summer
  290: 'mana', // Mana
  314: 'soda-twinkling-bunny', // Soda: Twinkling Bunny
  315: 'ade-agent-bunny', // Ade: Agent Bunny
  316: 'velvet', // Velvet
  322: 'marciana-marine-study', // Marciana: Marine Study (321 = base, not encoded)
  330: 'crown', // Crown
  352: 'helm', // Helm — dual-slot base; promoted per the roster
  353: 'helm-aquamarine', // Helm: Aquamarine
  354: 'mast-romantic-maid', // Mast: Romantic Maid
  355: 'anchor-innocent-maid', // Anchor: Innocent Maid
  390: 'zwei', // Zwei — dual-slot base; promoted per the roster
  391: 'ein', // Ein
  403: 'quency-escape-queen', // Quency: Escape Queen
  411: 'flora', // Flora — dual-slot base; promoted per the roster
  431: 'volume', // Volume
  470: 'red-hood', // Red Hood (16 = Rapi: Red Hood, separately encoded)
  471: 'snow-white-heavy-arms', // Snow White: Heavy Arms
  502: 'elegg-boom-and-shock', // Elegg: Boom and Shock
  511: 'cinderella', // Cinderella
  513: 'little-mermaid', // Little Mermaid
  514: 'grave', // Grave
  515: 'cinderella-crystal-wave', // Cinderella: Crystal Wave - base slug; fans out to -mg/-snipe (MODE_VARIANTS)
  520: 'bready', // Bready - base slug; fans out to -lingering/-recommended (MODE_VARIANTS)
  570: 'ark-ranger-black', // Ark Ranger Black
  580: 'phantom', // Phantom — dual-slot base; promoted per the roster
  581: 'arcana', // Arcana
  583: 'arcana-fortune-mate', // Arcana: Fortune Mate
  600: 'mint', // Mint
  601: 'prika', // Prika
  831: 'rei-ayanami', // Rei (레이) — 392 is a different character also shown as "Rei"
  834: 'rei-ayanami-tentative-name', // Rei (Tentative Name)
  835: 'asuka-shikinami-langley-wille', // Asuka: WILLE
  840: 'ada-wong', // Ada
  841: 'jill-valentine', // Jill
  850: 'eve', // EVE
  851: 'raven', // Raven
  860: 'chisato-nishikigi', // Chisato
  861: 'takina-inoue', // Takina
}

// Base slugs that have a separate "-signature" encoding. Only these can be promoted.
// The backend drift test asserts this equals the encoded base/-signature pairs, so a
// newly encoded dual-slot unit fails the suite until it is added here.
export const DUAL_SLOT_BASES: ReadonlySet<string> = new Set([
  'centi',
  'drake', 'flora', 'helm', 'julia', 'laplace', 'miranda', 'moran', 'phantom', 'privaty',
  'rosanna',
  'sugar', 'tove', 'zwei',
])

// Single entry point: identity lookup, then signature promotion when owned.
//
// `ownsFavoriteItem` comes from the roster itself and is the only thing that can
// promote. A roster that does not say defaults to NOT owned, which yields the base
// encoding: the conservative answer, since promoting a unit the user has not invested
// in inflates its recommendation, while a missed promotion merely undersells it. The
// slug is editable in the UI, so that case is recoverable by hand.
export const resolveSlugForUnit = (
  resourceId: number | undefined,
  ownsFavoriteItem = false,
): string | undefined => {
  if (resourceId === undefined) return undefined
  const base = RESOURCE_ID_TO_SLUG[resourceId]
  if (base === undefined) return undefined
  // Any unit can hold a Favorite Item; only a dual-slot base has a second
  // encoding to promote to.
  if (ownsFavoriteItem && DUAL_SLOT_BASES.has(base)) {
    return `${base}-signature`
  }
  return base
}
