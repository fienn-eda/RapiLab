"""SkillRule encoding of Rapi: Red Hood's "Battlefield Assessment" (skills[0]),
"Attachable Projectiles" (skills[1]), and "Power of Inheritance" (skills[2])
from lootandwaifus.com slug "rapi-red-hood".

Whether she becomes a Burst-1 stand-in ("Combat Assist") depends on whether
another Burst 1 ally is already in the deck - re-using the same
no_other_burst_tier_allies condition Anis: Star's rules use, since combination
search needs this evaluated per-deck, not hardcoded to one roster.

Modeled from Attachable Projectiles (both permanent battle-start self effects):
- Projectile Explosion Damage ▲ 100.6% continuously - boosts her
  projectile_explosion-typed burst nuke (Power of Inheritance is a Projectile
  Explosion keyword skill, see registry's _BURST_DAMAGE_TYPES).
- "Applies Elemental Advantage damage to Electric Code enemies continuously" -
  she is Fire (advantaged vs Wind only), so this GRANTS her an advantage she
  does not naturally have: a self element_advantage_grant gated on
  boss_is_element("Electric"). raid_simulator's element_bonus_for reads that
  stat and hands the damage formula 1.1 instead of 1.0, exactly the multiplier
  natural advantage would give. It is deliberately NOT other_elemental_bonus
  ("Superior Code Damage"), which the formula only pays out to a unit that
  ALREADY has advantage - modelling the grant that way made it self-cancelling.
  Because the grant is real advantage, any Superior Code bonus she carries
  (e.g. an overload line) correctly applies on top of it.

The 120-normal-attack launcher (Attachable Projectiles' second effect) is a
scheduled_nukes pair, not a SkillRule - see
build_attachable_projectiles_scheduled_nukes. Fienn's confirmed semantics
(2026-07-19): every time the shot counter reaches the requirement a
projectile attaches (counter resets), attachments ACCUMULATE, and every
pending attachment explodes together on the next Full Burst entry. The Stage
3 burst (Power of Inheritance) lowers the requirement by 60 for 10s and grants
a windowed Projectile Attachment Damage Up rider - see
build_power_of_inheritance_rules.

The Stage 1 branch (the "rapi-red-hood-b1" seat - see MODE_VARIANTS/
VARIANT_BURST_TIERS in registry.py) deals no damage at all: her own burst
cooldown down 20s (so she re-bursts every cycle from cycle 2 on, standing in
for Burst 1) and a squad flat ATK buff worth 18.01% of her own ATK (Crown's
caster-ATK precedent) - see build_power_of_inheritance_stage1_rules.

Not modeled / deferred:
- Power of Inheritance's Explosion Radius buff (Stage 1 and Stage 3) - no
  engine stat represents blast radius, so it stays deferred.
"""
from app.effects import Effect, Pulse
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule
from app.squad_engine import (
    SkillRule,
    boss_is_element,
    has_status,
    no_other_burst_tier_allies,
    not_condition,
)

# "rapi-red-hood-b1" is the same owned character seated in her Combat Assist
# (Burst-1 stand-in) role instead of her nominal Burst 3 - see MODE_VARIANTS/
# VARIANT_BURST_TIERS in registry.py. Its manifest is identical to the base
# entry except data_slug/dotgg_slug, which point weapon-stat/skill-value
# loading back at the one real character record (Fienn, 2026-07-19).
SKILL_VALUE_MANIFESTS = {
    "rapi-red-hood": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rapi_red_hood",
        "keys": {
            "battlefield_assessment": ("skills", 0),
            "attachable_projectiles": ("skills", 1),
            "power_of_inheritance": ("skills", 2),
        },
        "fixtures": {
            "battlefield_assessment": "VALUES",
        },
    },
    "rapi-red-hood-b1": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rapi_red_hood",
        "data_slug": "rapi-red-hood",
        "dotgg_slug": "rapi-red-hood",
        "keys": {
            "battlefield_assessment": ("skills", 0),
            "attachable_projectiles": ("skills", 1),
            "power_of_inheritance": ("skills", 2),
        },
        "fixtures": {
            "battlefield_assessment": "VALUES",
        },
    },
}


def build_battlefield_assessment_rules(values: dict) -> list[SkillRule]:
    own_burst_tier = int(values["description_value_01"])
    cooldown_reduction_sec = float(values["description_value_04"])
    self_atk_up = float(values["description_value_07"]) / 100
    self_atk_duration = float(values["description_value_08"])
    # "Damage to Interruption Parts", not Damage to Parts - a gimmick zone, not
    # a destructible part. See test_parts_vs_interruption_parts.
    interruption_parts_up = float(values["description_value_09"]) / 100
    damage_to_parts_duration = float(values["description_value_10"])
    squad_attack_damage_up = float(values["description_value_05"]) / 100
    squad_attack_damage_duration = float(values["description_value_06"])

    no_burst1_ally = no_other_burst_tier_allies(own_burst_tier)

    def assess_formation(context, caster_slug, time, registry):
        if no_burst1_ally(context, caster_slug):
            context.set_status(caster_slug, "Combat Assist")
        else:
            context.clear_status(caster_slug, "Combat Assist")

    def combat_assist_branch(context, caster_slug, time, registry):
        registry.add_pulse(
            Pulse(
                stat="burst_cooldown_reduction_sec",
                value=cooldown_reduction_sec,
                scope="squad",
                source_slug=caster_slug,
            )
        )
        registry.add(
            Effect(
                "attack_damage_up",
                squad_attack_damage_up,
                "squad",
                squad_attack_damage_duration,
                caster_slug,
            ),
            applied_at=time,
        )

    def self_buff_branch(context, caster_slug, time, registry):
        registry.add(
            Effect("atk_percent", self_atk_up, "self", self_atk_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect(
                "damage_to_interruption_parts_up", interruption_parts_up, "self",
                damage_to_parts_duration, caster_slug
            ),
            applied_at=time,
        )

    in_combat_assist = has_status("Combat Assist")
    not_in_combat_assist = not_condition(in_combat_assist)

    return [
        SkillRule(trigger="battle_start", action=assess_formation),
        SkillRule(trigger="full_burst_end", action=assess_formation),
        SkillRule(trigger="full_burst_enter", condition=in_combat_assist, action=combat_assist_branch),
        SkillRule(trigger="full_burst_enter", condition=not_in_combat_assist, action=self_buff_branch),
    ]


# 부착 타격 하나가 게이지에 넣는 에너지. **그녀의 MG값(500)이 아니다** - 부착형
# 유탄은 MG가 아니라 **런처로 발사되는 발사체**이고, 「스킬이 만드는 타격은 그 유닛
# 무기의 기본값을 준다」를 세운 실측 셋(헬름 애장품 추댐 · 리버렐리오 라이더 ·
# 헤비암즈 오토파이어)은 전부 자기 무기와 **같은 종류**의 타격이라 이 경우를 안
# 덮는다.
#
# 실측이 값을 가둔다(Fienn, 2026-08-22, docs/measurements/burst-gauge-fill.md):
# 단독편성 840발(= 유탄 정확히 7개)에서 7번째 부착 **직전은 미달 · 직후는 완충**
# 이므로 `840 x 500 + 7X >= 500,000`과 `840 x 500 + 6X < 500,000`이 X를
# [11,429, 13,333)로 가두고, 부착 **직전** 게이지 174px(176px 척도)이 그것을
# **[12,150, 12,623]**으로 좁힌다. 그 범위 안에서 RL 무기군에 실재하는 값은
# 12,500 하나다(수집 86정: 2,250 · 7,500 · 12,500 · 14,000 x6 · 14,500 ·
# 15,000 x2 · 18,200 · 34,500).
#
# **라피의 데이터에는 근거가 없다** - 그녀의 `detail`엔 `shot_detail`이 MG 하나
# 뿐이고(`burst_energy_pershot=500`) 유탄 레코드가 아예 없어서, 이 값은 실측으로만
# 정해진다. 더 정밀한 판독이 오면 이 상수 하나만 고치면 된다.
ATTACHMENT_GAUGE_ENERGY = 12_500


def build_attachable_projectiles_rules(values: dict) -> list[SkillRule]:
    projectile_attachment_up = float(values["description_value_01"]) / 100
    projectile_explosion_up = float(values["description_value_02"]) / 100
    return [
        buff_rule("battle_start", [
            ("projectile_explosion_damage_up", projectile_explosion_up, "self", None),
        ]),
        buff_rule("battle_start", [
            ("projectile_attachment_damage_up", projectile_attachment_up, "self", None),
        ]),
        buff_rule("battle_start", [
            ("element_advantage_grant", 1.0, "self", None),
        ], condition=boss_is_element("Electric")),
    ]


def build_attachable_projectiles_scheduled_nukes(
    values: dict, slug: str = "rapi-red-hood", stage3_requirement_cut: bool = True,
) -> list[dict]:
    """The 120-normal-attack projectile launcher (Fienn semantics, 2026-07-19):
    every time the shot counter reaches the requirement it fires an attaching
    projectile (attachment damage lands at that shot's time, counter resets),
    attachments ACCUMULATE, and every pending attachment explodes together on
    the next Full Burst entry (one explosion hit per attachment). The Stage 3
    burst lowers the requirement by 60 for 10s (windows from own burst times);
    the B1 variant bursts in Stage 1, so it passes stage3_requirement_cut=False
    and keeps the flat 120. Attachment/explosion hits are damage-typed so the
    matching Damage-Up stats (S2's permanent 150.72%/100.6%, the Stage 3
    burst's windowed 421.2%) multiply them in phase 2 - nothing is folded into
    the percents here."""
    proj = values["attachable_projectiles"]
    burst = values["power_of_inheritance"]
    base_requirement = int(float(proj["description_value_03"]))
    attach_percent = float(proj["description_value_04"])
    explosion_percent = float(proj["description_value_05"])
    requirement_cut = int(float(burst["description_value_14"])) if stage3_requirement_cut else 0
    cut_duration = float(burst["description_value_15"])

    def attach_times(context, fight_duration):
        shots = context.shot_times.get(slug, [])
        windows = [(t, t + cut_duration)
                   for t in context.burst_times.get(slug, [])]
        times, count = [], 0
        for t in shots:
            count += 1
            requirement = base_requirement - (
                requirement_cut if any(s <= t < e for s, e in windows) else 0)
            if count >= requirement:
                times.append(t)
                count = 0
        return times

    def explosion_times(context, fight_duration):
        entries = [start for start, _end in context.full_burst_windows]
        times = []
        for attached_at in attach_times(context, fight_duration):
            next_entry = next((s for s in entries if s > attached_at), None)
            if next_entry is not None:
                times.append(next_entry)
        return times

    return [
        {"schedule": attach_times, "percent": attach_percent,
         "damage_type": "projectile_attachment",
         "gauge_energy": ATTACHMENT_GAUGE_ENERGY},
        # 폭발은 선언하지 않는다 - 원문이 "When entering Full Burst, the
        # projectiles explode"라 창 **안**에서 터지고 게이지는 창 밖에서만 찬다.
        # 값을 붙이면 세어지지 않는 타격에 붙는 것이라 조용히 죽는 코드가 된다.
        {"schedule": explosion_times, "percent": explosion_percent,
         "damage_type": "projectile_explosion"},
    ]


def build_power_of_inheritance_rules(values: dict) -> list[SkillRule]:
    """Stage 3 rider: Projectile Attachment Damage ^ 421.2% for 10s on her own
    burst. (The requirement cut rides inside the launcher schedule above; the
    Explosion Radius branch stays deferred - radius is not modeled.)"""
    burst = values["power_of_inheritance"]
    return [
        buff_rule("own_burst_activate", [
            ("projectile_attachment_damage_up",
             float(burst["description_value_11"]) / 100, "self",
             float(burst["description_value_12"])),
        ]),
    ]


def build_power_of_inheritance_stage1_rules(values: dict) -> list[SkillRule]:
    """Power of Inheritance used in Stage 1 (the B1-variant seat, where
    Combat Assist holds): no damage - self burst-cooldown down 20s (so she
    re-bursts every cycle from cycle 2 on) and all allies gain flat ATK worth
    18.01% of HER attack for 10s (Crown's caster-ATK precedent). Explosion
    Radius stays deferred (not modeled)."""
    burst = values["power_of_inheritance"]
    caster_atk = values["caster_atk"]
    return [
        cdr_pulse_rule("own_burst_activate",
                       float(burst["description_value_02"]), scope="self"),
        buff_rule("own_burst_activate", [
            ("flat_atk", caster_atk * float(burst["description_value_05"]) / 100,
             "squad", float(burst["description_value_06"])),
        ]),
    ]


def power_of_inheritance_stage3_burst_percent(values: dict) -> float:
    """The Stage 3 branch's "Deals X% of final ATK as additional damage" -
    only correct when NOT in Combat Assist (i.e. a Burst 1 ally is present),
    which is the case in Fienn's actual deck. Stage 1's own damage isn't
    modeled since that branch doesn't apply here."""
    return float(values["description_value_08"])
