"""Cinderella: Crystal Wave, encoded as TWO static mode slugs (Fienn,
2026-07-18 spec review): the player picks MG or Snipe pre-battle and holds it,
so each mode is a fixed weapon profile + statically wired mode effects, and
deck search shows which mode a recommendation used via the slug itself.

Snipe full-charge semantics (Fienn, 2026-07-19): like Velvet's ammo pouch, a
full charge actually FIRES ONE round - the "expends 40 rounds" text is ammo
ACCOUNTING for consumption-counting synergies, not magazine drain. The
15-round magazine cycles on real shots. That accounting feeds skills we defer
anyway (see below), so it appears only in this docstring and the
little_mermaid cross-note.

Modeled (DPS-relevant):
- Beauty-Full (skills[0]): battle-start self Attack Damage +24% (shared by
  both modes). Its Snipe-Mode weapon-transform block (charge time, damage,
  full charge damage, magazine) is not a buff - it's the Snipe slug's static
  weapon profile, see build_snipe_weapon_profile. Its "every 5 sec, nearest
  enemy" 900%-of-final-ATK nuke is a periodic nuke (both modes; Preparation
  for Change's own timing gimmick around it is mode-switch machinery, deferred).
- Mode Swap (skills[1]): battle-start self ATK +29% (shared). MG keeps
  Pinpoint (core-hit damage +26%, other_core_damage_sources); Snipe keeps
  Destroy (parts damage +26.21%, damage_to_parts_up) - the two are mutually
  exclusive per-mode status flags collapsed to "whichever mode this slug is."
  The mode-dependent Full-Burst-after-own-Burst nuke splits per mode: MG's is
  a core strike (833.79%, gated on an exploitable core existing) and Snipe's
  is a flat hit on all enemies/parts (1189.66%, ungated) - both still require
  her own Burst Skill to have fired this cycle first.
- Glass Slippers, Full Contact W (skills[2], her burst): self Attack Damage
  +92% / ATK +65% for 10 sec (shared), plus a 6000%-of-final-ATK burst nuke.

Not modeled / deferred:
- Decoy avatar (survivability, no damage path).
- Burst-gauge +12% per 200 ally rounds (gauge charge time is a fixed sim
  input - same defer as Little Mermaid's Bubble Order).
(Snipe Mode's "Gains Pierce" is NOT deferred: the engine holds the pierce
property itself as `has_pierce`, distinct from the `pierce_damage_up` bucket,
and it is granted permanently below.)
- Mode-switch machinery (Preparation for Change, reload-fixed windows):
  meaningless once the mode is held for the whole fight.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.squad_engine import boss_core_hittable, own_burst_fired_this_cycle

SNIPE_RELOAD_TIME_SEC = 2.5  # no reload value in the skill text - Snipe mode
# borrows the MG base reload (Fienn's ruling, 2026-07-19).

SKILL_VALUE_MANIFESTS = {
    "cinderella-crystal-wave-mg": {
        "source": "lootandwaifus",
        "data_slug": "cinderella-crystal-wave",
        "dotgg_slug": "cinderella-crystal-wave",
        "test_module": "test_skill_rules_cinderella_crystal_wave",
        "keys": {
            "beauty_full": ("skills", 0),
            "mode_swap": ("skills", 1),
            "glass_slippers": ("skills", 2),
        },
    },
    "cinderella-crystal-wave-snipe": {
        "source": "lootandwaifus",
        "data_slug": "cinderella-crystal-wave",
        "dotgg_slug": "cinderella-crystal-wave",
        "test_module": "test_skill_rules_cinderella_crystal_wave",
        "keys": {
            "beauty_full": ("skills", 0),
            "mode_swap": ("skills", 1),
            "glass_slippers": ("skills", 2),
        },
    },
}


def _shared_rules(values):
    beauty = values["beauty_full"]
    mode_swap = values["mode_swap"]
    glass = values["glass_slippers"]
    return [
        buff_rule("battle_start", [
            ("attack_damage_up", float(beauty["description_value_10"]) / 100, "self", None),
            ("atk_percent", float(mode_swap["description_value_02"]) / 100, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", float(glass["description_value_01"]) / 100, "self",
             float(glass["description_value_02"])),
            ("atk_percent", float(glass["description_value_03"]) / 100, "self",
             float(glass["description_value_04"])),
        ]),
    ]


def build_crystal_wave_mg_rules(values):
    mode_swap = values["mode_swap"]
    fired = own_burst_fired_this_cycle()
    core = boss_core_hittable()

    def own_burst_and_core(context, caster_slug):
        return fired(context, caster_slug) and core(context, caster_slug)

    return _shared_rules(values) + [
        buff_rule("battle_start", [
            ("other_core_damage_sources", float(mode_swap["description_value_04"]) / 100,
             "self", None),                                   # Pinpoint
        ]),
        # 833.79% core strike: the skill text scopes this to "enemies with
        # activated cores" - the sim's core correction is a uniform per-instance
        # model (core_damage.core_hit_bonus_for, no per-enemy distinction), so
        # gating the whole
        # nuke on core_hittable is the established convention for a
        # core-activated-enemies-only effect.
        #
        # "core strike damage" (코어 명중 대미지) collects the core bonus
        # multiplier and every Core Damage up/down effect, even though it is
        # skill damage and strikes the body rather than a real core part - see
        # raid_simulator.core_eligible. Her own Pinpoint (+26%) is one of the
        # effects it therefore picks up.
        instant_nuke_pulse_rule(
            "full_burst_enter", float(mode_swap["description_value_08"]),
            condition=own_burst_and_core, damage_type="core_strike"),
    ]


def build_crystal_wave_snipe_rules(values):
    mode_swap = values["mode_swap"]
    return _shared_rules(values) + [
        buff_rule("battle_start", [
            ("damage_to_parts_up", float(mode_swap["description_value_03"]) / 100,
             "self", None),                                   # Destroy
            # Snipe Mode's "Additional Effect 1: Gains Pierce" - permanent
            # here because this slug holds Snipe for the whole fight.
            ("has_pierce", 1.0, "self", None),
        ]),
        instant_nuke_pulse_rule(
            "full_burst_enter", float(mode_swap["description_value_06"]),
            condition=own_burst_fired_this_cycle()),          # 1189.66%, ungated
    ]


def crystal_wave_burst_percent(values):
    return float(values["glass_slippers"]["description_value_05"])


def crystal_wave_periodic_nuke(values):
    beauty = values["beauty_full"]
    return {"cooldown": float(beauty["description_value_13"]),
            "percent": float(beauty["description_value_14"])}


def build_snipe_weapon_profile(values, weapon_stats=None):
    """Snipe's static weapon profile (Beauty-Full's "Changes the weapon in
    use: Snipe Mode" block). The `weapon` field stays "MG" at the unit-identity
    level in registry/roster data (weapon-type ally filters, e.g. Tove's SG
    theme, key off the character's real gun) - firing cadence and per-shot
    typing are decided by THIS profile's "SR" weapon field once it's swapped
    in via get_weapon_profile_override. `weapon_stats` (the collected profile)
    is unused: this is a full swap, not a correction."""
    beauty = values["beauty_full"]
    return {
        "weapon": "SR",
        "damage_percent": float(beauty["description_value_02"]),
        "max_ammo": int(float(beauty["description_value_04"])),
        "reload_time": SNIPE_RELOAD_TIME_SEC,
        "charge_time": float(beauty["description_value_01"]),
        "charge_damage_percent": float(beauty["description_value_03"]),
    }
