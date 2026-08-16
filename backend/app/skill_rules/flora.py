"""Flora (slug "flora"), a Burst-2 Electric MG Supporter. She is a healer, so
almost her whole kit is outside the damage model - what she contributes to a
raid deck is True Damage.

Modeled (DPS-relevant):
- Iris (skills[1]): squad True Damage +30.97%, permanent. The skill text gates it
  on "when either adjacent ally reaches max HP", but the sim never damages
  allies, so they are always at max HP - Fienn ruled it always-on (2026-07-24).
  Squad is the bullet's own scope, not an approximation of adjacency: the
  effect line reads "Affects all allies" and only the TRIGGER names an adjacent
  ally, so no seating changes who this reaches (which is why Flora is not in
  registry.SEATED_BUFF_SLUGS). Modelling it as
  permanent also erases the base/Favorite-Item duration difference on this
  bullet (5 sec vs 10 sec), which is the cost of the ruling.
- Secret Garden (skills[2], her burst, cd 40): squad True Damage +42.39% for
  10 sec. A separate source from Iris, so the two sum. Her burst deals no
  damage, so the registry's burst percent is None.

- Petunia (skills[0]), 2nd bullet: "after landing 100 normal attacks, all
  Electric Code allies: Increases the stack count of stackable buffs by 1".
  See build_petunia_stack_contributions.

Not modeled / skipped:
- Every heal, shield and Incoming Healing bullet (Petunia's 1%/sec regen and
  +4% Incoming Healing, Iris's 10.22% Max-HP shield, Secret Garden's 10.45%
  Max-HP heal) - survivability, not damage.
"""
from app.skill_rules._helpers import buff_rule


SLUG = "flora"


SKILL_VALUE_MANIFESTS = {
    "flora": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_flora",
        "keys": {
            "petunia": ("skills", 0),
            "iris": ("skills", 1),
            "secret_garden": ("skills", 2),
        },
    },
}


# Petunia's 2nd bullet, ("how many normal attacks", "how many stacks"). The two
# Flora builds read DIFFERENT sources (`SKILL_VALUE_MANIFESTS`), and the source
# is what numbers the slots - shiftypad puts this bullet's pair at _03/_04,
# lootandwaifus at _04/_05. So each build owns its own mapping and the shared
# builder takes it, rather than one of them being silently wrong.
PETUNIA_STACK_SLOTS = ("description_value_03", "description_value_04")


def build_petunia_stack_contributions(values, caster_slug=SLUG,
                                      slots=PETUNIA_STACK_SLOTS):
    """Petunia's 2nd bullet: "Activates after landing 100 normal attacks.
    Affects all Electric Code allies. Increases the stack count of stackable
    buffs by 1."

    It names no target, so it is a CLASS-scoped contribution (`target_filter`):
    the merge in `roster` resolves it against whichever fielded members are
    Electric AND hold a resource declared `stackable_buff`. The holders' own
    caps still clamp the merged total, which is what keeps "+1 a time" from
    running past what their skills state.

    What it raises is the CURRENT count, not the cap (Fienn, 2026-08-16) - so it
    only pays where a real counter sits below its cap. A stacking buff the
    engine already approximates at its steady-state maximum gains nothing.

    Which resources are "stackable buffs" is DECLARED, not inferred: Maiden
    carries a buff (Meditation) and a gauge (MP) at once and takes the bump only
    on the first (Fienn, range test 2026-08-17). See `ResourceSpec.stackable_buff`.

    No "except the skill user" clause, so she is in her own scope - she holds no
    such resource today, which is why that costs nothing to state correctly.
    """
    petunia = values["petunia"]
    threshold_slot, amount_slot = slots
    return [{
        "target_filter": {"element": "Electric", "stackable_buff": True},
        "fill": ("per_shot_every_by_ally",
                 int(float(petunia[threshold_slot])), caster_slug),
        "amount": float(petunia[amount_slot]),
    }]


def build_flora_rules(values):
    iris = values["iris"]
    garden = values["secret_garden"]
    iris_true_damage = float(iris["description_value_04"]) / 100
    burst_true_damage = float(garden["description_value_02"]) / 100
    burst_duration = float(garden["description_value_03"])
    return [
        buff_rule("battle_start", [
            ("true_damage_up", iris_true_damage, "squad", None),
        ]),
        buff_rule("own_burst_activate", [
            ("true_damage_up", burst_true_damage, "squad", burst_duration),
        ]),
    ]
