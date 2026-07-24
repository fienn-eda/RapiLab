"""Laplace: Ultimate Hero (slug "laplace-ultimate-hero"), a Burst-3 Wind RL
attacker from MISSILIS. Collected from ShiftyPad (blablalink public data).

WARNING - THIN ENCODING. Her core damage engine is a charge-count-driven weapon
transform loop (Warm Up stacks -> "Electric Power, Fully Full Charge" weapon ->
120 piercing rounds -> Over Energy stages), none of which the engine can express
today (no charge-count trigger, and weapon_mode_schedules anchors on burst/time,
not on a Warm-Up-stack threshold). What is modeled below is only her burst nuke
plus a couple of buffs; the deck search will therefore undervalue her until the
deferred loop is built. See docs/engine-gaps.md.

Modeled (DPS-relevant):
- Electric Power, Full Full Charge (skills[0]), at battle start: self ATK +
  (4.05% of her LIVE Max HP) continuously - resolved through
  max_hp_scaled_atk_rule, so ally/self Max HP buffs feed it. Snapshot at
  battle start: her own Over Energy stages raise Max HP later in the fight
  and must re-apply this buff to be reflected (see the deferred list).
- Over Energy (skills[1]), on her OWN Burst-3 activation ("[Burst Stage 3
  entry]" = after B2 fires, before B3 fires - Fienn's in-game reading,
  2026-07-24): self Attack Damage +52.14% for 10 sec. Encoded on
  own_burst_activate, not full_burst_enter: the two are numerically
  identical for a B3 unit's own nuke (same timestamp, inclusive buff
  window - see tests/test_burst_cycle_buff_timing.py), but
  full_burst_enter would also pay out on cycles where a DIFFERENT B3 unit
  bursts instead of her.
- Regenerative Energy Armament: Mjolnir (skills[2], her burst):
  - self ATK +63.36% for 10 sec.
  - burst nuke: 2953.84% of final ATK (default attack type).

Not modeled / deferred (handle later, needs engine work):
- Warm Up (skills[0]): Charge Speed +10% per Full Charge, up to 5 stacks (+50%).
  Deferred, not approximated as a steady +50%: at 5 stacks it is consumed and
  removed to trigger the weapon transform, so it never actually holds max.
- The weapon transform itself (skills[0]): at max Warm Up the weapon changes to
  "Electric Power, Fully Full Charge" (9.45%/shot, 120 ammo, gains Pierce, ends
  when the magazine empties, then removes 100% ammo). This is a CHARGE-COUNT-
  triggered transform - the engine's segment primitive can't anchor on it. This
  is her main DPS; deferred wholesale.
- Over Energy (skills[1]): after 12 normal attacks in the transformed state,
  Over Energy +5% (to 100%); each 100% advances a stage granting Max HP
  (+2/+3/+7/+10.5%). Gated on the deferred transform AND a normal-attack count
  (no such trigger); Max HP is also inert for damage. Deferred.
- Mjolnir's stage bonus (skills[2]): "934.76% of final ATK x Over Energy stage as
  additional damage" to the nearest enemy. Scales with the deferred Over Energy
  stage, so it is 0 without the loop. Deferred.
"""
from app.skill_rules._helpers import buff_rule, max_hp_scaled_atk_rule


SKILL_VALUE_MANIFESTS = {
    "laplace-ultimate-hero": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_laplace_ultimate_hero",
        "keys": {
            "electric_power_full_full_charge": ("skills", 0),
            "over_energy": ("skills", 1),
            "regenerative_energy_armament_mjolnir": ("skills", 2),
        },
    },
}


def laplace_ultimate_hero_burst_percent(values):
    return float(values["regenerative_energy_armament_mjolnir"]["description_value_03"])


def build_laplace_ultimate_hero_rules(values, caster_max_hp):
    s1 = values["electric_power_full_full_charge"]
    s2 = values["over_energy"]
    burst = values["regenerative_energy_armament_mjolnir"]

    battle_start_atk_pct = float(s1["description_value_01"]) / 100  # Max HP의 4.05%

    fb_attack_damage = float(s2["description_value_06"]) / 100  # 52.14%
    fb_attack_damage_dur = float(s2["description_value_07"])     # 10 sec

    burst_atk = float(burst["description_value_01"]) / 100  # 63.36%
    burst_atk_dur = float(burst["description_value_02"])     # 10 sec

    return [
        max_hp_scaled_atk_rule("battle_start", battle_start_atk_pct, "self", None, caster_max_hp),
        # 스킬텍스트의 [버스트 3단계 진입 시] = 그녀 자신이 B3를 쏘는 순간
        # (Fienn 실측 2026-07-24). own_burst_activate는 넉이 기록되기 전에 발동해
        # 이 버프가 그녀의 버스트딜에 곱해지고, 그녀가 버스트하지 않은 사이클엔
        # 지급되지 않는다 (full_burst_enter는 후자를 못 막는다).
        buff_rule("own_burst_activate", [("attack_damage_up", fb_attack_damage, "self", fb_attack_damage_dur)]),
        buff_rule("own_burst_activate", [("atk_percent", burst_atk, "self", burst_atk_dur)]),
    ]
