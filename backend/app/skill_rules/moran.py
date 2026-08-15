"""Moran (slug "moran") and her Favorite Item build (slug "moran-signature"), a
Burst-1 AR Defender. Collected from api.dotgg.gg.

The two builds are separate deck candidates (dual-slot); which one a user fights
with comes from their roster's per-unit `favorite_item` flag.

Base modeled (DPS-relevant): Bring It On!'s second bullet and the weapon
transform - and nothing else. Every other base effect is survivability (DEF
scaling, Perseverance, the heal, taunts) or an ally-side Damage Taken reduction,
so base Moran registers NO SkillRules at all. What the Favorite Item adds is her
entire buffer role: Leave It To Me!'s burst-cooldown reduction (slot 10) and Fair
and Square!'s squad flat ATK (slots 09/10) exist only in the dollskills array.

Bring It On!'s second bullet is identical in both builds: every 5 normal attacks
"while weapon is changed" deal 47.18% of final ATK as additional damage. "While
weapon is changed" is exactly her own transform window, so it is the
`every_during_segment` per-shot mode (the Snow White: Heavy Arms precedent),
which counts shots inside a weapon-mode segment. "As additional damage" makes it
`full_burst_bonus_eligible`.

Favorite Item modeled (DPS-relevant):
- Bring It On!'s Fervor bullet (dollskills[0] slot 04): "Cooldown of Burst Skill
  -20 sec continuously", affecting self - a standing cut to her own cooldown,
  so it goes through `get_burst_cooldown_reduction` rather than the per-cycle
  pulse. With Leave It To Me! on top her 40-sec burst comes back every ~12.5
  sec, which is the cycle Fienn measures in game (2026-07-26).
- Leave It To Me! (dollskills[1]): on Full Burst enter while in Fervor, squad
  burst-cooldown reduction.
- Fair and Square! (dollskills[2], her burst): squad ATK up as a flat bonus
  scaled off Moran's own ATK.
- Fair and Square!'s weapon transform: for 10 sec her AR becomes an
  unlimited-ammo SMG dealing 14.7% of final ATK per shot - a
  `weapon_mode_schedules` segment (see
  build_fair_and_square_weapon_mode_schedule). Infinite ammo makes an in-game
  shot count impractical to measure (Fienn 2026-07-22), and no community guide
  publishes one, so the cadence is anchored to the engine's canonical SMG rate
  (20 shots/sec) - the transform IS an SMG, so this reuses a measured constant
  rather than inventing one. burst_percent stays None (the transform is her
  burst damage, not a single nuke).

Assumption: Fervor is triggered by "Raptures appear" and is treated as always
active in a raid. Not modeled: DEF / damage-taken / Max-HP survivability buffs
(the squad "Damage Taken +" line reads as an ally-side effect, not an enemy
DPS debuff), taunts, the HP-recovery on the transform, and the HP-threshold
Perseverance effect.

"""
from app.attack_rate import rate_of_fire_for_weapon
from app.skill_rules._helpers import (
    buff_rule,
    cdr_pulse_rule,
    instant_nuke_pulse_rule,
)

SKILL_VALUE_MANIFESTS = {
    "moran": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "bring_it_on": ("skills", 0),
            "leave_it_to_me": ("skills", 1),
            "fair_and_square": ("skills", 2),
        },
        "fixtures": {
            "bring_it_on": "MORAN_BASE_BRING_IT_ON",
            "leave_it_to_me": "MORAN_BASE_LEAVE_IT_TO_ME",
            "fair_and_square": "MORAN_BASE_FAIR_AND_SQUARE",
        },
    },
    "moran-signature": {
        "source": "dotgg",
        "data_slug": "moran",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "bring_it_on": ("dollskills", 0),
            "leave_it_to_me": ("dollskills", 1),
            "fair_and_square": ("dollskills", 2),
        },
        "fixtures": {
            "bring_it_on": "MORAN_SIG_BRING_IT_ON",
            "leave_it_to_me": "MORAN_SIG_LEAVE_IT_TO_ME",
            "fair_and_square": "MORAN_SIG_FAIR_AND_SQUARE",
        },
    },
}


def build_bring_it_on_per_shot_rules(values):
    """Bring It On!'s second bullet, identical in both builds: every Nth normal
    attack landed WHILE THE WEAPON IS CHANGED deals a flat percentage of final
    ATK as additional damage.

    "While weapon is changed" is her own transform, so this is
    `every_during_segment` - the mode counts only shots inside a weapon-mode
    segment, so the rider cannot leak into her ordinary AR fire."""
    bring = values["bring_it_on"]
    nuke_percent = float(bring["description_value_02"])
    shots = int(float(bring["description_value_03"]))
    return [(shots, "every_during_segment", [
        instant_nuke_pulse_rule("per_shot", nuke_percent),
    ])]


def build_moran_base_rules(values):
    """Base Moran registers no combat SkillRules at all.

    Her damage comes from the transform segment and the Bring It On! rider, both
    wired outside _BUILDERS. Everything else the base kit does is survivability
    or an ally-side Damage Taken cut; the burst-cooldown reduction and the squad
    flat ATK that make her a buffer are the Favorite Item's text. Returned as an
    explicit empty list so the registry entry reads as a decision, not an
    oversight."""
    return []


def build_moran_fervor_cooldown_reduction(values):
    """Bring It On!'s Fervor bullet (Favorite Item only): "Cooldown of Burst
    Skill -20 sec continuously", affecting SELF.

    Self-scoped and permanent, so it is her cooldown rather than a per-cycle
    pulse - `registry.get_burst_cooldown_reduction`, which the scheduler reads
    before the fight starts. Leave It To Me!'s cut is the other half and stays
    a pulse: that one is squad-scoped and gated on entering Full Burst.

    Fervor itself is assumed always active in a raid ("Activates when Raptures
    appear"), the same assumption the rest of this module runs on."""
    return float(values["bring_it_on"]["description_value_04"])


def build_moran_rules(values):
    leave = values["leave_it_to_me"]
    fair = values["fair_and_square"]
    caster_atk = values["caster_atk"]
    cdr_sec = float(leave["description_value_10"])
    atk_bonus = caster_atk * float(fair["description_value_09"]) / 100
    atk_duration = float(fair["description_value_10"])

    return [
        cdr_pulse_rule("full_burst_enter", cdr_sec),
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", atk_duration)]),
    ]


# 창모드의 조준원, `accuracy.WEAPON_SPREAD_DIAMETER`와 같은 게임 단위.
#
# Fienn 인게임 판독(부계정, 2026-08-15): 변형 중 **100px**, 변형이 아닐 때 **50px**.
# 두 값이 같은 프레임·같은 창 설정·같은 명중률(그녀의 오버로드 11.81%)에서 나왔으므로
# **비만 쓰면 화면 스케일도 명중률도 약분된다** — 화면 px에서 게임 단위로 가는 일반형은
# 없고(docs/measurements/accuracy-circle-and-core-px.md에서 한 번 틀려 철회됨) 필요하지도
# 않다:
#
#     창모드_기본 = AR_기본 × (100px / 50px) = 75 × 2 = 150
#
# 교차검증 둘. 그녀의 50px에서 역산한 화면 스케일은 0.7468px/단위로 그 문서의 0.7485와
# **0.2%** 차이고, 150은 게임 데이터 값 계열(10 · 75 · 110 · 250)에 맞는 정수다.
#
# 미측정으로 남는 것: 창모드 조준원이 명중률에 **같은 방식으로** 반응하는지는 한
# 명중률에서만 재서 알 수 없다. 엔진은 다른 무기와 같게 다루므로 그녀의 실제
# 명중률에서는 판독을 정확히 재현하고, 다른 명중률에서만 갈린다.
SPEAR_MODE_SPREAD_DIAMETER = 150.0


def build_fair_and_square_weapon_mode_schedule(values, slug="moran"):
    """Fair and Square!'s weapon transform: for 10 sec her AR becomes an
    unlimited-ammo SMG dealing 14.7% of final ATK per shot.

    A `weapon_mode_schedules` segment fits cleanly - the skill grants "Unlimited
    ammunition" for exactly the transform window, and segments never reload, so
    there is no magazine to interrupt (the same reason the primitive suited
    Nayuta's Memory Incineration). The window is `end`-bounded by that duration
    rather than a measured `until_shots`: no shot count exists to anchor to
    (infinite ammo makes an in-game count impractical, and no guide publishes
    one), so the count follows from the rate and the 10-sec window.

    The cadence is the engine's canonical SMG rate (`rate_of_fire_for_weapon`,
    20 shots/sec) - the transform IS an SMG, so this is a measured weapon-class
    constant, not an invented number (Fienn approved this proxy 2026-07-22). As
    an explicit `rate_of_fire` it takes no cadence buffs, matching every other
    measurement-anchored segment; revisit if the transform's real rate is ever
    measured.

    `spread_diameter` is measured too, and it has to be DECLARED because the
    engine reads spread from the BASE weapon and never from a segment's
    hand-written `weapon` label - her transform is not core-locked (Fienn
    checked, 2026-08-15), so unlike Nayuta's she needs a diameter rather than
    `always_core_hit`. See SPEAR_MODE_SPREAD_DIAMETER for the derivation."""
    fair = values["fair_and_square"]
    profile = {
        "weapon": "SMG",
        "damage_percent": float(fair["description_value_01"]),  # 14.7
        "rate_of_fire": rate_of_fire_for_weapon("SMG"),
        "spread_diameter": SPEAR_MODE_SPREAD_DIAMETER,
    }
    window = float(fair["description_value_04"])  # unlimited-ammo duration, 10s

    def schedule(context, fight_duration):
        return [
            {"start": t, "end": t + window, "profile": profile}
            for t in context.burst_times.get(slug, [])
        ]

    return schedule
