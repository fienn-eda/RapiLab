"""Emma: Tactical Upgrade (slug "emma-tactical-upgrade"), a Burst-1 Fire MG
supporter. Values from ShiftyPad; effect text cross-read from lootandwaifus.

She is the LT Formation half of the Absolute pair; Eunhwa: Tactical Upgrade is
the AS Formation half, and each one's bonus block is live exactly when the other
is in the deck (Fienn, 2026-08-08).

Modeled (DPS-relevant):
- Environment Setup (skills[0]): all enemies Damage Taken +3.9% for 10 sec,
  recurring every 30 sec - or every 10 sec while she is in AS Formation, i.e.
  beside Eunhwa. Two mechanisms together, because the skill is neither a plain
  passive nor a plain cooldowned skill:
  - it "activates at the start of battle", so a `battle_start` rule fires the
    t=0 instance that `periodic_rules` (which starts at t=interval) cannot;
  - the repeats are two `periodic_rules` entries, 30 sec and 10 sec, each gated
    on whether Eunhwa is in the deck. Registering both and letting the
    conditions pick is what lets a deck-dependent INTERVAL work at all: an
    entry's cooldown is fixed when the registry builds it, and only a rule's
    condition can see the deck.
  At 30 sec the debuff is up a third of the time; at 10 sec on a 10-sec effect
  it is continuous.
- LT Formation (skills[1]), continuous from battle start:
  - Absolute-squad allies Critical Damage +23.51%. Same exact-membership
    treatment as Eunhwa's crit-rate bullet - see `ABSOLUTE_SQUAD_SLUGS`.
  - squad Projectile Explosion Damage +2.32%.
  - the AS Formation bonus: squad True Damage +30.97% and another squad
    Projectile Explosion Damage +3.09%. The two Projectile Explosion bullets
    are separate grants and add.
- Battlefield Formation (skills[2], her burst, cd 20): squad ATK +40.07% of HER
  ATK for 10 sec, as `flat_atk` off `caster_atk`.
- Enhanced Environment Setup, the burst's rider: "Damage taken multiplier of
  Environment Setup is scaled by 100%" for 10 sec, i.e. another +3.9% on top of
  the running debuff. Gated on her being in Environment Setup status when she
  bursts - which, paired, is always (a 10-sec status on a 10-sec interval), so
  it is modeled for the paired case only. See the deferred note below for solo.

Not modeled / deferred:
- Enhanced Environment Setup in a deck WITHOUT Eunhwa. The status is then up
  for 10 sec in every 30, and whether her burst lands inside it depends on the
  cycle length the rest of the deck produces - a per-cycle overlap the rules
  layer has no way to ask about (a `condition` sees the deck, not the clock).
  Deferring understates her slightly in solo decks; approximating it either way
  would be a guess about a coin-flip.
- Environment Setup's regen (2.32% of her Max HP per second) and the burst's
  Incoming Healing +29.04%: survivability. The regen's OCCURRENCE is a trigger
  elsewhere, so she IS in `HEAL_PROVIDER_SLUGS`.
- Exposure, the permanent taunt, and LT Formation's "Exposure activation
  disabled" - the engine has no aggro model, and nothing else in her kit is
  gated on either.
"""
from app.skill_rules._helpers import (
    ABSOLUTE_SQUAD_SLUGS,
    buff_rule,
    member_subset_buff_rule,
)
from app.squad_engine import deck_contains, not_condition


SKILL_VALUE_MANIFESTS = {
    "emma-tactical-upgrade": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_emma_tactical_upgrade",
        "keys": {
            "environment_setup": ("skills", 0),
            "lt_formation": ("skills", 1),
            "battlefield_formation": ("skills", 2),
        },
    },
}


EUNHWA = "eunhwa-tactical-upgrade"  # the AS Formation half of the pair

# The two possible recurring intervals: the printed 30 sec, and 30 minus LT
# Formation's own "Recurring interval ▼ 20 sec" while she is in AS Formation.
# Registered as constants because `periodic_rules` fixes an entry's cooldown at
# build time, so both have to exist before the deck is known.
ENVIRONMENT_SETUP_SOLO_INTERVAL = 30.0
ENVIRONMENT_SETUP_PAIRED_INTERVAL = 10.0


def _is_absolute_squad(member, _context=None):
    return member.slug in ABSOLUTE_SQUAD_SLUGS


def _environment_setup_debuff(setup):
    return (
        float(setup["description_value_01"]) / 100,
        float(setup["description_value_02"]),
    )


def build_environment_setup_periodic_rules(values):
    """Environment Setup's repeats, one entry per possible interval. The
    conditions are mutually exclusive, so exactly one entry ever fires."""
    setup = values["environment_setup"]
    lt = values["lt_formation"]
    debuff, duration = _environment_setup_debuff(setup)

    printed = float(setup["description_value_05"])
    shortened = printed - float(lt["description_value_05"])
    assert (printed, shortened) == (
        ENVIRONMENT_SETUP_SOLO_INTERVAL, ENVIRONMENT_SETUP_PAIRED_INTERVAL
    ), "the data's intervals moved; the registered cooldowns must move with them"

    with_eunhwa = deck_contains(EUNHWA)
    return [
        (
            ENVIRONMENT_SETUP_SOLO_INTERVAL,
            [buff_rule("periodic", [("damage_taken_up", debuff, "squad", duration)],
                       condition=not_condition(with_eunhwa))],
        ),
        (
            ENVIRONMENT_SETUP_PAIRED_INTERVAL,
            [buff_rule("periodic", [("damage_taken_up", debuff, "squad", duration)],
                       condition=with_eunhwa)],
        ),
    ]


def build_emma_tactical_upgrade_rules(values):
    setup = values["environment_setup"]
    lt = values["lt_formation"]
    battlefield = values["battlefield_formation"]
    caster_atk = values["caster_atk"]

    debuff, debuff_duration = _environment_setup_debuff(setup)
    squad_crit_damage = float(lt["description_value_01"]) / 100
    projectile_explosion = float(lt["description_value_02"]) / 100
    true_damage = float(lt["description_value_03"]) / 100
    bonus_projectile_explosion = float(lt["description_value_04"]) / 100
    squad_atk = float(battlefield["description_value_01"]) / 100 * caster_atk
    squad_atk_duration = float(battlefield["description_value_02"])

    with_eunhwa = deck_contains(EUNHWA)

    return [
        # The t=0 instance; the repeats live in periodic_rules.
        buff_rule("battle_start", [("damage_taken_up", debuff, "squad", debuff_duration)]),
        member_subset_buff_rule(
            "battle_start", _is_absolute_squad,
            [("other_critical_damage_sources", squad_crit_damage, None)],
        ),
        buff_rule("battle_start", [
            ("projectile_explosion_damage_up", projectile_explosion, "squad", None),
        ]),
        buff_rule(
            "battle_start",
            [
                ("true_damage_up", true_damage, "squad", None),
                ("projectile_explosion_damage_up", bonus_projectile_explosion, "squad", None),
            ],
            condition=with_eunhwa,
        ),
        buff_rule("own_burst_activate", [("flat_atk", squad_atk, "squad", squad_atk_duration)]),
        # Enhanced Environment Setup: the debuff's multiplier scaled by 100%,
        # i.e. the same value again. Paired only - see the module docstring.
        buff_rule(
            "own_burst_activate",
            [("damage_taken_up", debuff, "squad", debuff_duration)],
            condition=with_eunhwa,
        ),
    ]
