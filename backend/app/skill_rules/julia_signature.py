"""Julia's signature-weapon (dollskills) build, slug "julia-signature" - a
SEPARATE roster entry from base Julia (slug "julia"), per Fienn's decision to
model characters with an optional signature weapon as two distinct slugs
(2026-07-12), matching how Privaty/Helm: Aquamarine are already encoded.
Her Crescendo/Marcato chain was deferred as structurally impossible until
2026-07-20: both fill triggers are "after N critical hit(s) with normal
attacks", and the engine models crit as expected value with no per-hit roll.
EVE's encoding replaced that ruling with a conversion - count EXPECTED crits,
reading the unit's LIVE crit rate per shot so ally crit buffs actually speed
the trigger up (Fienn's condition, 2026-07-20). Crescendo is a CAPPED stack, so
it rides the matching resource fill `("per_critical_hit_every", N)` rather than
the per-shot mode; both share `_expected_crit_positions`.

Modeled (DPS-relevant):
- Decrescendo (skills[0], own cooldown 20s): self Crit Rate +26.04%, self
  Normal Attack Critical Rate +36.16% (its own bucket, so it never reaches
  Climax) and self ATK +20%, all for 10 sec. Fires periodically (t=20,40,...) like base Julia's
  Decrescendo, PLUS an extra cast at battle start - Crescendo's "Activates at
  the start of battle... Forcefully uses Skill 1" bullet (alongside, not
  instead of, the periodic schedule - a forced use still starts her own
  cooldown, so the periodic ticks are unaffected).
- Climax (skills[2], her burst): deals 544.5% of final ATK as damage, attacking
  sequentially 5 times - 5 separate hits (`burst_hit_counts`), each
  independently defense-subtracted.
- Crescendo (dollskills[1]): +1 stack per 6 expected critical hits, capped at 5,
  each stack worth Critical Damage +24.79% for 15 sec. Same ResourceSpec shape
  as base Julia's Crescendo, differing only in the fill (base fills on the last
  bullet of a magazine; the signature fills on crit count).
- Marcato (dollskills[1]): every 8 expected critical hits, 88% of final ATK.
  It rides her own shots, so it is computed at each proc's own time and takes
  the Full Burst bonus on whichever land inside a window - the timing decides
  it, not the "as additional damage" wording (that text rule was deleted
  2026-07-28).
- Climax's gated rider: an additional 544.5% when Crescendo is at max stacks,
  as a `resource_scaled_nukes` entry whose scale_fn is 1 at the cap and 0 below
  it - identical in shape to base Julia's.

Not modeled / deferred:
- Marcato's own rider, "activates if Marcato lands as a crit: 100% of final ATK
  as additional damage". Converting this would mean multiplying the rider by the
  crit rate - an expected-value approximation stacked on top of the one that
  already produced the Marcato proc, and unlike the counter conversion it has
  not been put to Fienn. Left out, which makes this encoding a FLOOR for her by
  roughly `crit_rate * 100%` per Marcato.
- "Affects random enemies" targeting - a raid sim is a single boss.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, linear_resource_buff


SKILL_VALUE_MANIFESTS = {
    "julia-signature": {
        "source": "lootandwaifus",
        "data_slug": "julia",
        "test_module": "test_skill_rules_julia_signature",
        "keys": {
            "decrescendo": ("dollskills", 0),
            "crescendo": ("dollskills", 1),
            "climax": ("dollskills", 2),
        },
    },
}

CRESCENDO = "crescendo"


DECRESCENDO_COOLDOWN = 20.0  # skill text: Skill 1 cooldown 20s
CLIMAX_HIT_COUNT = 5  # skill text: "Attacks sequentially 5 times" (fixed, not a data slot)


def climax_burst_percent(values):
    return float(values["climax"]["description_value_01"])


def _decrescendo_buffs(values):
    crit_rate = float(values["description_value_01"]) / 100
    crit_rate_duration = float(values["description_value_02"])
    atk = float(values["description_value_03"]) / 100
    atk_duration = float(values["description_value_04"])
    normal_crit_rate = float(values["description_value_05"]) / 100
    normal_crit_rate_duration = float(values["description_value_06"])
    return [
        ("crit_rate", crit_rate, "self", crit_rate_duration),
        ("atk_percent", atk, "self", atk_duration),
        # A SECOND, separate bullet: "Normal Attack Critical Rate ▲ 36.16%".
        # Its own bucket, so it reaches her normal attacks (and the expected-crit
        # counters Crescendo rides) without inflating Climax.
        ("normal_attack_crit_rate", normal_crit_rate, "self", normal_crit_rate_duration),
    ]


def build_decrescendo_periodic_rules(values):
    return [buff_rule("periodic", _decrescendo_buffs(values))]


def build_decrescendo_battle_start_rules(values):
    return [buff_rule("battle_start", _decrescendo_buffs(values))]


def _crescendo_cap(values):
    return int(float(values["crescendo"]["description_value_03"]))


def build_crescendo_signature_resources(values):
    """Crescendo: +1 stack per 6 EXPECTED critical hits with normal attacks,
    capped at 5, each stack worth Critical Damage +24.79% for 15 sec. Base
    Julia's Crescendo is the same shape on a different fill (`on_last_bullet`);
    the signature's trigger is the crit counter, hence the new fill kind."""
    cres = values["crescendo"]
    return [
        ResourceSpec(
            name=CRESCENDO,
            fill=("per_critical_hit_every", float(cres["description_value_01"])),
            cap=_crescendo_cap(values),
            buffs=[linear_resource_buff(
                "other_critical_damage_sources",
                float(cres["description_value_02"]) / 100,
                "self",
                lifetime=float(cres["description_value_04"]),
            )],
        )
    ]


def build_marcato_per_shot_rules(values):
    """Marcato: 88% of final ATK every 8 expected critical hits. "As additional
    damage", so it opts into the Full Burst Bonus. Its own "if Marcato crits"
    rider is deferred - see the module docstring."""
    cres = values["crescendo"]
    return [(
        float(cres["description_value_05"]),
        "every_n_critical_hits",
        [instant_nuke_pulse_rule(
            "per_shot", float(cres["description_value_06"])
        )],
    )]


def build_climax_signature_resource_scaled_nuke(values):
    """Climax's rider: an additional 544.5% only while Crescendo sits at max
    stacks, read at her own burst time."""
    cap = _crescendo_cap(values)
    return [{
        "resource": CRESCENDO, "cap": cap,
        "base_percent": float(values["climax"]["description_value_03"]),
        "scale_fn": lambda count, cap=cap: 1.0 if count >= cap else 0.0,
        "tick_count": 1, "tick_interval": 0.0, "resolves_after_cast": True,
    }]
