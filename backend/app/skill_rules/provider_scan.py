"""Which encoded Nikkes heal, and which place shields, derived from skill text.

The engine models no heal or shield EVENT, so a bullet that keys off one ("when
recovery takes effect", "when a shield is placed in front of this unit") can only
ask the deck-level question: is there someone here who does that at all. Crown's
Royal Attire and Flora's Favorite Item Iris bullet are the two consumers.

The answer belongs in data, not in someone's memory of 90 kits - and the lists in
`_helpers` went stale exactly once already (six slugs, including both Flora
builds, so Crown's ceiling branch never armed beside the squad's purest healer).
`tests/test_provider_lists_match_data.py` re-derives them here and fails when the
committed constants drift, and `scripts/find_heal_providers.py` prints the
matching line per slug so a classification can be eyeballed.

Nothing in `app/` imports this at runtime: the constants are committed values,
this is what checks them.
"""
import re

from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest
from app.skill_values import load_character_data

# "Within one sentence": any run of characters that does not cross a full stop.
# A bare `[^.]*` reads a DECIMAL POINT as the end of the sentence, which silently
# hid every heal whose amount carries one - Naga's "Recovers 9.58% of the skill
# user's final Max HP as HP" stopped dead at "Recovers 9". Almost every value in
# this data has a decimal, so the miss was the rule rather than the exception;
# the units the old pattern did catch were the ones wording it as "Restores HP
# equal to ...", with no number in between.
_SAME_SENTENCE = r"(?:[^.]|\.\d)*"

# Phrases NIKKE uses for restoring HP. "Incoming Healing ▲" is deliberately NOT
# here: buffing someone else's healing does not itself heal anyone.
HEAL_PATTERNS = (
    re.compile(rf"Recovers?\b{_SAME_SENTENCE}\bHP\b", re.I),
    re.compile(rf"\bRestores?\b{_SAME_SENTENCE}\bHP\b", re.I),
    re.compile(rf"\bHeals?\b{_SAME_SENTENCE}\bHP\b", re.I),
)

# The crouching cover's own health is not a unit receiving recovery, so it does
# not arm Crown's Royal Attire.
COVER_ONLY = re.compile(r"\bCover(?:'s)?\s+HP\b", re.I)

SHIELD_PATTERNS = (
    re.compile(r"Creates? (?:a )?(?:shared )?Shield", re.I),
    re.compile(rf"(?:grants?|gains?|applies) {_SAME_SENTENCE}\bShield\b", re.I),
)


# Buffs that raise a damage TYPE, which is how Bready's two Tastes are entered
# ("Activates when gaining a buff that increases sustained damage").
SUSTAINED_DAMAGE_BUFF = re.compile(r"Sustained Damage\s*▲", re.I)
DISTRIBUTED_DAMAGE_BUFF = re.compile(r"Distributed Damage\s*▲", re.I)

# The "■ ... Affects X." header a bullet sits under names who receives it. Only
# a bullet aimed at ALLIES can put someone else in a Taste - "Affects self" is
# the caster buffing herself, which is most of the matches (Diesel, Mana, Raven,
# Sakura, Mihara), and "Affects targets/enemies" is a debuff on the enemy.
_AFFECTS = re.compile(r"Affects ([^.\n]+)")
_ALLY_TARGET = re.compile(r"\ballies\b", re.I)


SOURCES = ("lootandwaifus", "dotgg")


def _skill_texts(slug, source):
    """[(array, skill name, max-level text)] from one source, or None when that
    source holds no data for the unit."""
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    try:
        data = load_character_data(source, manifest.get("data_slug", slug))
    except (FileNotFoundError, KeyError):
        return None
    texts = []
    for array in ("skills", "dollskills"):
        for skill in data.get(array) or []:
            levels = skill.get("levels") or []
            if not levels:
                continue
            last = levels[-1]
            if isinstance(last, str):
                text = last
            else:
                # dotgg keeps the value slots and the prose apart, and only the
                # prose carries the wording these patterns look for.
                text = skill.get("description", "")
            texts.append((array, skill.get("name"), text))
    return texts or None


def matching_lines(slug, patterns, exclude=None):
    """[(array, skill name, matched text)] - one entry per matching skill.

    Sources are tried in order and the FIRST one that matches is the answer: a
    unit's two collected files are the same kit, but one of them can be a
    partial capture, so silence in the first is not evidence of absence.
    """
    readable = False
    for source in SOURCES:
        texts = _skill_texts(slug, source)
        if texts is None:
            continue
        readable = True
        found = []
        for array, name, text in texts:
            for pattern in patterns:
                match = pattern.search(text)
                if match and not (exclude and exclude.search(match.group(0))):
                    found.append((array, name, match.group(0).strip()))
                    break
        if found:
            return found
    return [] if readable else None


def heal_provider_slugs():
    """Every encoded slug whose own skills restore a unit's HP."""
    return frozenset(
        slug for slug in ENCODED_SLUGS
        if matching_lines(slug, HEAL_PATTERNS, exclude=COVER_ONLY)
    )


def shield_provider_slugs():
    """Every encoded slug whose own skills place a shield - INCLUDING ones whose
    shield only reaches part of the squad. Which of those actually reach a given
    consumer is the caller's ruling, not this scan's: see
    `_helpers.ELEMENT_GATED_SHIELD_SLUGS`."""
    return frozenset(
        slug for slug in ENCODED_SLUGS if matching_lines(slug, SHIELD_PATTERNS)
    )


def _buffs_an_ally(text, pattern):
    """Whether `text` raises this damage type for someone OTHER than the caster.

    A bullet's recipient is declared by the "Affects X" clause that opens it, so
    the governing clause is the last one before the match. Ark: Ranger Black is
    why this reports "an ally" rather than "every ally": her Tremble! is
    "Affects all Wind Code allies with assault rifles", and whether a partial
    reach covers a given consumer is the caller's ruling (`_helpers`'
    SUBSET_SUSTAINED_DAMAGE_BUFF_SLUGS), the same split the shield scan makes.
    """
    for match in pattern.finditer(text or ""):
        governing = _AFFECTS.findall(text[:match.start()])
        if governing and _ALLY_TARGET.search(governing[-1]):
            return True
    return False


def _damage_type_buff_slugs(pattern):
    found = set()
    for slug in ENCODED_SLUGS:
        for source in SOURCES:
            texts = _skill_texts(slug, source)
            if texts is None:
                continue
            if any(_buffs_an_ally(text, pattern) for _, _, text in texts):
                found.add(slug)
            break
    return frozenset(found)


def sustained_damage_buff_slugs():
    """Every encoded slug that raises an ally's Sustained Damage - what puts
    Bready in Lingering Taste."""
    return _damage_type_buff_slugs(SUSTAINED_DAMAGE_BUFF)


def distributed_damage_buff_slugs():
    """The Recommended Taste half of the same question."""
    return _damage_type_buff_slugs(DISTRIBUTED_DAMAGE_BUFF)


# A Hit Rate bullet, in either direction. It is a damage stat since 2026-08-07
# (accuracy.core_hit_rate), and the fifteen slugs that carried one had all
# written it off as inert - which is why this scan exists rather than a list.
HIT_RATE_BULLET = re.compile(r"Hit Rate\s*[▲▼]", re.I)


def hit_rate_bullet_slugs():
    """Every encoded slug whose own skill text moves Hit Rate, up or down."""
    return frozenset(
        slug for slug in ENCODED_SLUGS if matching_lines(slug, (HIT_RATE_BULLET,))
    )


def unreadable_slugs():
    """Encoded slugs with no manifest or no collected data - they can neither be
    confirmed nor ruled out, so a caller comparing lists must exclude them."""
    return frozenset(
        slug for slug in ENCODED_SLUGS
        if all(_skill_texts(slug, source) is None for source in SOURCES)
    )
