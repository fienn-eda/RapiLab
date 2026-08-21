"""Little Mermaid (slug "little-mermaid"), a Burst-1 SMG supporter. Base skills.

Modeled (DPS-relevant):
- Bubble Order (skills[0]): squad burst-cooldown reduction when Full Burst
  ends; squad Attack Damage up when Full Burst begins; Burst Gauge +37% each
  time allies' total ammo expended reaches 400 (see build_bubble_order_gauge_fills,
  consumed by burst_gauge.fill_times's bonus_fills).
- Bubble Wave (skills[1]): the "Bubble" enemy Damage Taken +5.05% debuff.
  It activates "when the enemy appears" (= battle start in a raid, always-on)
  and is continuous, so modeled as a permanent squad-scoped enemy debuff.
- Siren's Song (skills[2], her burst): squad Attack Damage up + self ATK up.
- Bubble Wave's Full-Burst-only periodic nuke: every 1 sec during Full Burst,
  63.36% of final ATK x 4 sequential hits (periodic_nukes during_full_burst +
  hit_count, gap #6; "as damage" - no Full Burst Bonus opt-in). See
  build_bubble_wave_fb_nuke.
- Bubble Barrage (Bubble Wave, modeled 2026-07-18): 85% x10 hits each time
  ALLIES' total ammo expended reaches 500. The squad-wide bullet counter is
  built by merging every member's shot timeline in a `scheduled_nukes`
  schedule function (`context.shot_times` holds ALL slugs, not just the
  owner's) - no engine extension needed. See
  build_bubble_barrage_scheduled_nukes.
- Siren's Song's instant partial reload ("Reloads 33.26% magazine(s)"): a
  timed squad-wide refill grant at her own burst (`get_ammo_refill_grant`).

Not modeled:
- Explosive Bubble (after 50 of her own normal attacks): it removes Bubble and
  re-applies the same 5.05% Damage Taken (plus a 3s stun), so it adds no extra
  damage over the permanent Bubble already modeled - only the stun, which isn't
  modeled. Deliberately not double-counted.

Cross-note (2026-07-19): Bubble Barrage's squad ammo-expended counter assumes
"1 shot = 1 round." Velvet's ammo pouch (100/300-round accounting) and
Cinderella: Crystal Wave's Snipe mode (a full charge accounts as 40 rounds
despite firing one shot - see cinderella_crystal_wave.py) both accelerate
ally ammo-consumption counters past that 1-shot-1-round assumption without
the sim modeling it. Neither is wired into Bubble Barrage's counter today -
revisit if a proper ammo-accounting/gauge model is ever introduced.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule

SKILL_VALUE_MANIFESTS = {
    "little-mermaid": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "bubble_order": ("skills", 0),
            "bubble_wave": ("skills", 1),
            "sirens_song": ("skills", 2),
        },
    },
}


def build_little_mermaid_rules(values):
    order = values["bubble_order"]
    wave = values["bubble_wave"]
    siren = values["sirens_song"]
    cdr_sec = float(order["description_value_01"])
    fb_attack_damage = float(order["description_value_02"]) / 100
    fb_attack_damage_duration = float(order["description_value_03"])
    bubble_damage_taken = float(wave["description_value_01"]) / 100
    burst_attack_damage = float(siren["description_value_01"]) / 100
    burst_attack_damage_duration = float(siren["description_value_02"])
    self_atk = float(siren["description_value_04"]) / 100
    self_atk_duration = float(siren["description_value_05"])

    return [
        buff_rule("battle_start", [("damage_taken_up", bubble_damage_taken, "squad", None)]),
        cdr_pulse_rule("full_burst_end", cdr_sec),
        buff_rule("full_burst_enter", [
            ("attack_damage_up", fb_attack_damage, "squad", fb_attack_damage_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration),
            ("atk_percent", self_atk, "self", self_atk_duration),
        ]),
    ]


def build_bubble_order_gauge_fills(values):
    """아군 누적 소모탄이 N발에 닿을 때마다 버스트 게이지를 X% 채운다.

    누적 카운터는 Bubble Barrage와 같은 채널(`context.shot_ammo_rounds`)이다 -
    탄약 주머니를 쓰는 아군은 한 발이 수백 발을 회계하므로 발수와 라운드는
    같지 않다.
    """
    order = values["bubble_order"]
    return [{"every_ally_rounds": float(order["description_value_04"]),
             "fraction": float(order["description_value_05"]) / 100}]


def sirens_song_refill(values):
    """Siren's Song's "Reloads 33.26% magazine(s)": a squad-wide grant at her
    own burst, not Full Burst entry - she casts it herself."""
    song = values["sirens_song"]
    return {"percent": float(song["description_value_03"]),
            "scope": "squad", "event": "own_burst"}


def build_bubble_wave_fb_nuke(values):
    """Bubble Wave's 3rd bullet: every 1 sec only during Full Burst, 63.36% of
    final ATK x 4 sequential hits ("as damage" - no Full Burst Bonus opt-in)."""
    wave = values["bubble_wave"]
    return {
        "cooldown": float(wave["description_value_04"]),
        "percent": float(wave["description_value_05"]),
        "hit_count": int(float(wave["description_value_06"])),
        "during_full_burst": True,
    }


def build_bubble_barrage_scheduled_nukes(values):
    """Bubble Wave's 4th bullet: each time the squad's TOTAL ammo expended
    reaches 500, Bubble Barrage deals 85% of final ATK x 10 sequential hits
    ("as damage" - no Full Burst Bonus opt-in). The squad-wide bullet counter
    is the merged shot timeline of every squad member (`context.shot_times`,
    the same post-pass channel Raven reads), caster included ("allies"
    includes self). A shot books what `context.shot_ammo_rounds` says it
    accounts for - one round for an ordinary magazine, hundreds for an ally
    spending from an ammo pouch. Each barrage records its hits at the moment
    the crossing bullet fires."""
    wave = values["bubble_wave"]
    threshold = float(wave["description_value_07"])
    percent = float(wave["description_value_08"])
    hit_count = int(float(wave["description_value_09"]))

    def schedule(context, fight_duration):
        merged = sorted(
            (t, rounds)
            for slug, times in context.shot_times.items()
            for t, rounds in zip(times, context.shot_ammo_rounds.get(slug, [1.0] * len(times)))
        )
        hits, expended, next_barrage = [], 0.0, threshold
        for time, rounds in merged:
            expended += rounds
            # One shot can cross several thresholds at once: a 300-round pouch
            # spend books more than one 500-round barrage's worth over time.
            while expended >= next_barrage:
                if time < fight_duration:
                    hits.extend([time] * hit_count)
                next_barrage += threshold
        return hits

    return [{"schedule": schedule, "percent": percent}]
