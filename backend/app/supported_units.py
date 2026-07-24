"""Metadata for every engine-supported unit (slug/name/burst tier/element),
so the frontend draft palette can group units by burst tier without the
frontend needing to know the skill-value manifest / registry internals.
"""
from app.skill_rules.registry import ENCODED_SLUGS, VARIANT_BURST_TIERS, get_skill_value_manifest
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
