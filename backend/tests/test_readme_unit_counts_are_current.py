"""README's "N명의 니케 / N가지 빌드" must match what the registry actually holds.

Those two numbers are the first concrete thing a reader meets on the repo page,
and nothing kept them honest: they are hand-written prose, so encoding a Nikke
moved the registry and left the README behind. On 2026-08-22 both were found one
short (85/103 against an actual 86/104).

The same day, the count was ALSO gotten wrong in the other direction, in public.
A release announcement went out saying "93명 · 107가지" - numbers taken from
`len(supported_units())`. That endpoint is a third vocabulary, and it is neither
of the README's two:

    builds       len(ENCODED_SLUGS) == 104   what deck search compares
    characters   86                          builds with variants collapsed
    palette      len(supported_units()) == 107

`supported_units` counts a `-signature` pair as TWO chips (they are two owned
states of one character) while collapsing each MODE_VARIANTS group into ONE base
chip (`bready`, not `bready-lingering` + `bready-recommended`). Being both larger
and smaller than the other two makes it look like a plausible answer to either
question, and it answers neither. That is why the identity rule below is derived
from the registry rather than from that endpoint.

**The identity rule is the repo's, not this test's.** Two builds are the same
character when they differ only by:

- a MODE_VARIANTS candidate vs its base - the table in `skill_rules.registry`
  says so, and `supported_units`'s docstring calls the base "the character the
  player owns";
- the `-signature` suffix - `display_names.py` states the convention outright
  ("애장품(`-signature`)은 base와 같은 이름으로 쓴다"), and gives both slugs the
  same Korean name for exactly this reason.

**What this does NOT catch.** Only these two numbers, only in README.md. The
prose around them is not checked, nor is any count repeated elsewhere (docs/,
release notes, a community post). If a future variant axis is introduced without
a MODE_VARIANTS entry and without sharing a display name, `_character` will read
its builds as separate characters and this test will happily pin the wrong
number - the guard is the counting rule, so a new axis belongs here too.
"""
import re
from pathlib import Path

from app.display_names import DISPLAY_NAMES
from app.skill_rules.registry import ENCODED_SLUGS, MODE_VARIANTS

README = Path(__file__).resolve().parents[2] / "README.md"

SIGNATURE_SUFFIX = "-signature"

# Which base each MODE_VARIANTS candidate belongs to. Built rather than written
# out so a new group in the registry is picked up without touching this file.
_BASE_OF = {candidate: base
            for base, candidates in MODE_VARIANTS.items()
            for candidate in candidates}


def _character(slug):
    """The character this build belongs to.

    Base-mapping runs first: a MODE_VARIANTS candidate is named after its base,
    and stripping the suffix afterwards keeps the rule correct even if a future
    group's candidates are themselves signature builds."""
    return _BASE_OF.get(slug, slug).removesuffix(SIGNATURE_SUFFIX)


def _readme():
    assert README.is_file(), f"README not found at {README}"
    return README.read_text(encoding="utf-8")


def _stated(text, pattern, label):
    """The number README states, failing loudly if the sentence was reworded.

    Without this the test's whole value evaporates on a rewrite: a pattern that
    matches nothing would leave nothing to compare and the assertions below
    would pass over an empty claim."""
    found = re.findall(pattern, text)
    assert len(found) == 1, (
        f"expected exactly one {label} in README.md, found {found}. The "
        f"sentence was reworded - update the pattern {pattern!r} here so this "
        "check keeps guarding it."
    )
    return int(found[0])


def test_readme_states_the_registry_s_build_count():
    """빌드 수 == len(ENCODED_SLUGS), the candidates deck search compares."""
    # Guard the source too: an import that silently returned an empty registry
    # would otherwise make this test demand "0가지" of the README.
    assert len(ENCODED_SLUGS) >= 100, f"registry looks empty: {len(ENCODED_SLUGS)}"

    stated = _stated(_readme(), r"따로 세면 \*\*(\d+)가지\*\*", "build count")
    assert stated == len(ENCODED_SLUGS), (
        f"README says {stated}가지 but ENCODED_SLUGS holds {len(ENCODED_SLUGS)} "
        "builds. Encoding a Nikke moves the registry and leaves the README "
        "behind - update the sentence in README.md."
    )


def test_readme_states_the_character_count_with_variants_collapsed():
    """니케 수 == builds with 애장품/모드 variants collapsed onto one character."""
    assert MODE_VARIANTS, "MODE_VARIANTS is empty - the collapse rule scans nothing"

    characters = {_character(slug) for slug in ENCODED_SLUGS}
    # A collapse that stopped collapsing would silently equal the build count.
    assert len(characters) < len(ENCODED_SLUGS), (
        "no build collapsed onto another character - the variant rule stopped "
        "matching the registry's slug conventions"
    )

    stated = _stated(_readme(), r"현재 \*\*(\d+)명\*\*의 니케", "character count")
    assert stated == len(characters), (
        f"README says {stated}명 but the registry holds {len(characters)} "
        f"characters across {len(ENCODED_SLUGS)} builds. Note this is NOT "
        f"len(supported_units()) - that endpoint counts the palette, a third "
        "number. Update the sentence in README.md."
    )


def test_display_names_agree_that_signature_builds_are_the_same_character():
    """Independent derivation of the same collapse, from the other convention.

    The two rules `_character` folds together are recorded in different places -
    MODE_VARIANTS in the registry, the `-signature` convention in
    display_names.py - so a drift in either is invisible from the other. Here the
    display-name table is asked directly: every signature build must carry its
    base's name. That is what makes the character count reproducible from two
    sources rather than from this file's own suffix arithmetic.
    """
    pairs = [(s, s.removesuffix(SIGNATURE_SUFFIX)) for s in ENCODED_SLUGS
             if s.endswith(SIGNATURE_SUFFIX)]
    assert pairs, "no signature builds in the registry - the scan found nothing"

    disagree = {sig: (DISPLAY_NAMES.get(sig), DISPLAY_NAMES.get(base))
                for sig, base in pairs
                if base in ENCODED_SLUGS
                and DISPLAY_NAMES.get(sig) != DISPLAY_NAMES.get(base)}
    assert not disagree, (
        "these signature builds do not share their base's display name, so the "
        f"two conventions disagree about who they are: {disagree}. Either "
        "display_names.py drifted or the build is a different character - "
        "whichever it is, the count above rests on this agreement."
    )
