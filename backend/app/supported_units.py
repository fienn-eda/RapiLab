"""Metadata for every engine-supported unit (slug/name/burst tier/element),
so the frontend draft palette can group units by burst tier without the
frontend needing to know MODE_VARIANTS/VARIANT_BURST_TIERS itself.
"""
from app.skill_rules.registry import ENCODED_SLUGS, MODE_VARIANTS, VARIANT_BURST_TIERS
from app.skill_values import DATA_DIR, load_character_data

# variant slug -> its data slug (e.g. cinderella-crystal-wave-mg -> base)
_VARIANT_DATA_SLUG = {v: base for base, variants in MODE_VARIANTS.items()
                      for v in variants}


def _humanize(slug):
    return slug.replace("-", " ").title()


def supported_units(data_dir=DATA_DIR):
    out = []
    for slug in ENCODED_SLUGS:
        data_slug = _VARIANT_DATA_SLUG.get(slug, slug)
        try:
            meta = load_character_data("lootandwaifus", data_slug, data_dir)
            burst_tier = VARIANT_BURST_TIERS.get(slug, int(meta["burst"]))
            element = meta["element"]
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            continue
        out.append({"slug": slug,
                    "name": meta.get("name") or _humanize(slug),
                    "burst_tier": burst_tier,
                    "element": element})
    return out
