"""Rei Ayanami (Tentative Name) (slug "rei-ayanami-tentative-name"), a Burst-3
Wind AR attacker. A DISTINCT unit from Rei Ayanami (`rei-ayanami`, a Fire MG) -
not a signature variant. Base skills (no signature/Treasure). Collected from
lootandwaifus.com.

Modeled (DPS-relevant):
- Attack State (skills[2], her burst): self Attack Damage +35.9% and self flat
  ATK = 63.36% of the caster's ATK, both for 10 sec, plus the burst nuke, 990.2%
  of final ATK (`attack_state_burst_percent`). Attack State itself lasts 10 sec
  from her burst - the window the per-shot nuke below is gated to.
- Maintenance and Resupply (skills[1]): on entering Full Burst, all allies gain
  flat ATK = 11.61% of the caster's ATK for 10 sec (squad scope).
- Maintenance and Resupply's second bullet: on Full Burst entry, allies holding
  a Machine Gun who have already used their Burst Skill get MG heating up speed
  +100% for 13 sec - halving the 2.28-sec warm-up every one of their magazines
  pays (docs/measurements/mg-spinup.md).
- Annihilation Support (skills[0]) Attack-State clause: every 7 normal attacks
  while in Attack State (her own 10s burst window, gap #7's
  `every_during_own_status_window`), a 286.37%-of-final-ATK nuke. "As additional
  damage", so Full-Burst-Bonus eligible (and it lands inside her burst's Full
  Burst). See `build_annihilation_support_per_shot_rules`.

Not modeled / deferred:
- Annihilation Support's main payload (skills[0]): "after 18 normal attacks
  against a target in Anti A.T. Field status, deal 590.64% as additional damage
  (+10 Anti A.T. Field stacks)". Anti A.T. Field is a target/boss status applied
  by other Evangelion-collab units - a cross-unit target-status the engine
  doesn't model. This is her signature collab-synergy damage.
- Annihilation Support's Full-Burst clause for "allies in Annihilation State"
  (units-affected +1, attack range +500%, ATK +17.6% of caster ATK) - gated on
  the Annihilation State ally status, also cross-unit and unmodeled.
"""
from app.skill_rules._helpers import (
    ANNIHILATION_STATE_SLUGS,
    buff_rule,
    instant_nuke_pulse_rule,
    member_subset_buff_rule,
)
# The Anti A.T. Field window belongs to Asuka - it is her Annihilation State -
# so its length and her slug are imported rather than restated here.
from app.skill_rules.asuka_shikinami_langley_wille import (
    ANNIHILATION_STATE_DURATION,
    ANTI_AT_FIELD,
    SLUG as ASUKA_SLUG,
)

SLUG = "rei-ayanami-tentative-name"


SKILL_VALUE_MANIFESTS = {
    "rei-ayanami-tentative-name": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rei_ayanami_tentative_name",
        "keys": {
            "annihilation_support": ("skills", 0),
            "maintenance_and_resupply": ("skills", 1),
            "attack_state": ("skills", 2),
        },
    },
}


ATTACK_STATE_WINDOW = 10.0  # Attack State (skills[2]) lasts 10 sec from her burst


def attack_state_burst_percent(values):
    return float(values["attack_state"]["description_value_05"])


def build_rei_tentative_rules(values):
    maintenance = values["maintenance_and_resupply"]
    attack_state = values["attack_state"]
    annihilation = values["annihilation_support"]
    caster_atk = values["caster_atk"]
    state_ally_atk = float(annihilation["description_value_10"]) / 100 * caster_atk
    state_ally_atk_duration = float(annihilation["description_value_11"])

    self_attack_damage = float(attack_state["description_value_01"]) / 100
    self_attack_damage_duration = float(attack_state["description_value_02"])
    self_atk = float(attack_state["description_value_03"]) / 100 * caster_atk
    self_atk_duration = float(attack_state["description_value_04"])
    squad_atk = float(maintenance["description_value_03"]) / 100 * caster_atk
    squad_atk_duration = float(maintenance["description_value_04"])
    heating_speed = float(maintenance["description_value_01"]) / 100
    heating_duration = float(maintenance["description_value_02"])

    return [
        buff_rule("own_burst_activate", [
            ("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration),
            ("flat_atk", self_atk, "self", self_atk_duration),
        ]),
        buff_rule("full_burst_enter", [("flat_atk", squad_atk, "squad", squad_atk_duration)]),
        # "Affects all allies with a Machine Gun who have used their Burst
        # Skills" - the narrow subset Effect.scope can't express, resolved live
        # so the "already burst" half is read at the trigger's own moment.
        member_subset_buff_rule(
            "full_burst_enter",
            lambda member, context: (
                member.weapon == "MG"
                and member.slug in context.burst_used_this_cycle),
            [("mg_heating_speed_percent", heating_speed, heating_duration)],
        ),
        # Annihilation Support's Full-Burst clause: "Affects all allies in
        # Annihilation State status ... ATK +17.6% of the skill user's ATK".
        # Same shape as the bullet above - a membership the engine's scopes
        # cannot express, resolved live. Being the right unit is necessary but
        # not sufficient: the state is opened by HER OWN burst, so the audience
        # is also "has bursted this cycle".
        #
        # The clause's two siblings ("Units affected by Annihilation State's
        # additional effect +1", "Attack range +500%") are left out: the effect
        # they widen picks "2 enemy units nearest the crosshair", and a raid has
        # one boss, so a third target and a wider cone reach nothing.
        member_subset_buff_rule(
            "full_burst_enter",
            lambda member, context: (
                member.slug in ANNIHILATION_STATE_SLUGS
                and member.slug in context.burst_used_this_cycle),
            [("flat_atk", state_ally_atk, state_ally_atk_duration)],
        ),
    ]


def build_annihilation_support_per_shot_rules(values):
    """Two shot counters on one skill, gated on two DIFFERENT statuses.

    Attack State (her own 10s burst window): every 7 normal attacks, a
    286.37%-of-final-ATK "additional damage" nuke - gap #7's
    `every_during_own_status_window`.

    Anti A.T. Field (an ALLY's status, on the boss): every 18 normal attacks
    "against a target in Anti A.T. Field status", a 590.64% nuke. Only Asuka:
    WILLE puts that status there and only for her Annihilation State's own
    duration, so this rides `every_during_ally_status_window` anchored to HER
    bursts - with no Asuka in the deck there are no windows and it never fires,
    which is the game's own answer. The count restarts with each window because
    the status is removed when the window ends (Fienn, 2026-08-16).

    The 590.64% bullet also reads "Anti A.T. Field stacks ▲ 10", and that half
    stays out: Asuka alone pins her own 30-stack cap inside every window
    (measured 2026-08-16 - 505 shots at +1 per 10 fills 50 stacks' worth), so
    the rider has no headroom to write into. Wiring it would buy nothing and
    cost a cross-unit fill source whose own fill times depend on the count it
    changes.
    """
    annihilation = values["annihilation_support"]
    threshold = int(float(annihilation["description_value_04"]))
    nuke_percent = float(annihilation["description_value_05"])
    anti_at_threshold = int(float(annihilation["description_value_01"]))
    anti_at_percent = float(annihilation["description_value_02"])
    return [
        (
            (threshold, ATTACK_STATE_WINDOW),
            "every_during_own_status_window",
            [instant_nuke_pulse_rule("per_shot", nuke_percent)],
        ),
        (
            _anti_at_field_trigger(values),
            "every_during_ally_status_window",
            [instant_nuke_pulse_rule("per_shot", anti_at_percent)],
        ),
    ]


def _anti_at_field_trigger(values):
    """The Anti A.T. Field clause's cadence: every 18 of HER normal attacks
    inside Asuka's Annihilation State window.

    Shared by the two halves of that one bullet - the 590.64% nuke and the
    "+10 stacks" contribution below - so the damage and the stack it grants can
    never land on different shots."""
    annihilation = values["annihilation_support"]
    return (
        int(float(annihilation["description_value_01"])),
        ANNIHILATION_STATE_DURATION,
        ASUKA_SLUG,
    )


def build_anti_at_field_stack_contributions(values):
    """The other half of the same bullet: "Anti A.T. Field stacks ▲ 10".

    The stacks belong to ASUKA's resource, so this is declared as a
    CONTRIBUTION that `roster` merges onto her `ResourceSpec` when both units
    are actually fielded - the numbers are Rei's, so they live in Rei's module.
    Her cap still clamps the result (`resource_count` takes `spec.cap`), which
    is what keeps a +10 a time from running past the 30 her skill states.

    Measured 2026-08-16: with the Emergency Repair timing corrected Asuka pins
    that cap on her own inside every window (505 shots at +1 per 10 = 50
    stacks' worth), so today this contribution changes no damage. It is wired
    because the effect is real and the roster is not - a deck that slows her
    below ~33 shots/sec would open headroom for it.
    """
    threshold, window, _asuka = _anti_at_field_trigger(values)
    # The two slugs face opposite ways here. In HER per-shot rule the slug names
    # whose WINDOW to use (Asuka's). In this fill the owner IS Asuka, so the
    # window is already hers and the slug names whose SHOTS to count (Rei's).
    fill = ("per_shot_every_during_own_status_window_by_ally", threshold, window, SLUG)
    return [{
        "target": ASUKA_SLUG,
        "resource": ANTI_AT_FIELD,
        "fill": fill,
        "amount": float(values["annihilation_support"]["description_value_03"]),
    }]
