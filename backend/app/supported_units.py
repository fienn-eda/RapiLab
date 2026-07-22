"""Metadata for every engine-supported unit (slug/name/burst tier/element),
so the frontend draft palette can group units by burst tier without the
frontend needing to know the skill-value manifest / registry internals.
"""
from app.skill_rules.registry import ENCODED_SLUGS, VARIANT_BURST_TIERS, get_skill_value_manifest
from app.skill_values import DATA_DIR, load_character_data


def _humanize(slug):
    return slug.replace("-", " ").title()


def _load_meta(slug, data_dir):
    """Resolve slug's metadata dict, mirroring user_roster.load_nikke_spec's
    meta resolution exactly: the manifest's data_slug (the same remap
    load_nikke_spec uses - covers both MODE_VARIANTS siblings like
    cinderella-crystal-wave-mg and signature-weapon builds like
    julia-signature) looked up in lootandwaifus, falling back to the
    manifest's own dotgg/shiftypad weapon-data source when there's no
    lootandwaifus file (e.g. Privaty)."""
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        raise FileNotFoundError(f"no skill-value manifest for {slug!r}")
    data_slug = manifest.get("data_slug", slug)
    if manifest["source"] == "shiftypad":
        weapon_data = load_character_data("shiftypad", data_slug, data_dir)
    else:
        weapon_data = load_character_data(
            "dotgg", manifest.get("dotgg_slug", data_slug), data_dir
        )
    try:
        return load_character_data("lootandwaifus", data_slug, data_dir)
    except FileNotFoundError:
        return weapon_data


def supported_units(data_dir=DATA_DIR):
    out = []
    for slug in ENCODED_SLUGS:
        try:
            meta = _load_meta(slug, data_dir)
            burst_tier = VARIANT_BURST_TIERS.get(slug, int(meta["burst"]))
            element = meta["element"]
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            continue
        out.append({"slug": slug,
                    "name": meta.get("name") or _humanize(slug),
                    "burst_tier": burst_tier,
                    "element": element})
    return out
