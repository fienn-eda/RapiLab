"""Metadata (slug/name/burst tier/element) for every unit the frontend has to
name or draw, so it can group a palette by burst tier without knowing the
skill-value manifest / registry internals.

That list spans TWO vocabularies, and conflating them hid three owned
characters from the UI. A roster entry names the character the player owns
(`bready`); the engine's candidates are the slugs the roster loader fans her out
into (`bready-lingering`, `bready-recommended`, via MODE_VARIANTS). Listing only
the candidates meant intersecting the roster with this list dropped her - the
palette called her "not yet supported" and offered no way to exclude her, while
the recommender was fielding her all along. So both are listed: an owned slug
that stands for several candidates carries `candidates` naming them, and every
other entry is its own single candidate.
"""
from app.display_names import DISPLAY_NAMES
from app.skill_rules.registry import (ENCODED_SLUGS, MODE_VARIANTS,
                                      VARIANT_BURST_TIERS,
                                      get_skill_value_manifest)
from app.skill_values import DATA_DIR, load_character_data, load_weapon_data


def _humanize(slug):
    return slug.replace("-", " ").title()


def _load_meta(slug, data_dir):
    """Resolve slug's metadata dict, mirroring user_roster.load_nikke_spec's
    meta resolution exactly: the manifest's data_slug (the same remap
    load_nikke_spec uses - covers both MODE_VARIANTS siblings like
    cinderella-crystal-wave-mg and signature-weapon builds like
    julia-signature) looked up in lootandwaifus, falling back to the
    manifest's own weapon-data source when there's no lootandwaifus file
    (e.g. Privaty).

    The weapon file is loaded even when lootandwaifus supplies the metadata,
    and is deliberately NOT guarded: a unit whose weapon data is missing cannot
    be loaded into a roster at all, so listing it here would put a unit in the
    palette that load_nikke_spec then refuses. Both callers resolve that file
    through load_weapon_data, so the two can no longer drift apart."""
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        raise FileNotFoundError(f"no skill-value manifest for {slug!r}")
    weapon_data = load_weapon_data(manifest, slug, data_dir)
    try:
        return load_character_data(
            "lootandwaifus", manifest.get("data_slug", slug), data_dir)
    except FileNotFoundError:
        return weapon_data


def _entry(slug, data_dir):
    """One catalog entry, or None if this slug's data can't be resolved.

    The name is the hand-written Korean one when the table has it. An empty or
    absent entry means "not translated yet" and falls back to the source data's
    English name, so display_names.py can be filled one unit at a time without
    ever blanking a label."""
    try:
        meta = _load_meta(slug, data_dir)
        return {"slug": slug,
                "name": (DISPLAY_NAMES.get(slug)
                         or meta.get("name") or _humanize(slug)),
                "burst_tier": VARIANT_BURST_TIERS.get(slug, int(meta["burst"])),
                "element": meta["element"]}
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        return None


def supported_units(data_dir=DATA_DIR):
    out = [e for e in (_entry(slug, data_dir) for slug in ENCODED_SLUGS)
           if e is not None]
    by_slug = {e["slug"]: e for e in out}

    for base, variants in MODE_VARIANTS.items():
        loadable = [v for v in variants if v in by_slug]
        if not loadable:
            continue
        # A base that is itself a candidate (rapi-red-hood) is already listed
        # on her own terms - name, element and her NOMINAL burst tier - so she
        # needs no merged entry, only the candidate list. She is the one base
        # whose candidates sit at different burst tiers, and that list is how a
        # client learns the engine may seat her at either: without it, a result
        # naming `rapi-red-hood-b1` reads as a unit nobody drafted.
        if base in by_slug:
            by_slug[base]["candidates"] = loadable
            continue
        # The candidates are the same character, so element/burst tier agree
        # and the first one describes her; test_supported_units pins that
        # agreement, since a base whose candidates disagreed on burst tier
        # could not be drawn as one palette chip and would need a decision
        # rather than a silent guess.
        #
        # The NAME no longer agrees, though - that is the point of the table.
        # The base is the character herself, so she takes her own entry; only
        # an untranslated base still borrows a candidate's name, and then the
        # duplicate it creates is what test_display_names' uniqueness check
        # reports.
        merged = {**by_slug[loadable[0]], "slug": base, "candidates": loadable}
        if DISPLAY_NAMES.get(base):
            merged["name"] = DISPLAY_NAMES[base]
        out.append(merged)
    return out
