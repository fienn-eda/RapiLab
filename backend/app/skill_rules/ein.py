"""Ein (slug "ein"), a Burst-3 Electric SR attacker. Collected from
lootandwaifus.com (no dotgg copy exists).

Her damage is her Near Feathers: summoned entities that attack the boss on their
own, faster the more of them are alive. The skill text alone is misleading -
"Activates when Near Feather is summoned ... Deals 90.81%" reads as one hit per
summon, but the feathers PERSIST and keep attacking. The real mechanics come
from a client datamine plus Fienn's own video measurement (2026-07-17):

- Six feathers max. Battle start summons F1-F4; her burst summons F1-F6, and
  re-summoning an existing feather resets both its lifetime and its attack
  cooldown.
- Lifetimes from each summon: F1 unlimited, F2 38s, F3 32s, F4 26s, F5/F6 10s.
- A feather attacks every 8 sec, reduced 16% per feather alive beyond the first
  (additive: 6 feathers -> 8 * (1 - 0.16*5) = 1.6s each).

Modeled (DPS-relevant):
- Feather Shot's Near Feather Attack (90.81% of final ATK as true damage) on the
  precomputed feather schedule (`scheduled_nukes`) - see `_feather_hit_times`.
  True damage ignores DEF, so this is a large, DEF-independent share of her
  output.
- Feather Shot's self Charge Damage +80% for 1 round on every Full Charge
  (per-shot trigger + RoundGrant).
- Feather Standby's self ATK +70.12% for 10 sec on entering Burst Stage 3. She
  IS the Burst-3 slot, so that instant is her own burst activation.
- Feather-All Range (her burst): self True Damage +55.3% and Charge Damage
  +140.68% for 10 sec, plus a 300.02% true-damage nuke. "10 enemy units with the
  highest final DEF" collapses to the single raid boss, so it lands once. The
  text says "as true damage", not "as additional damage", so it is NOT
  Full-Burst-Bonus eligible (Fienn's text rule).

Assumptions (documented, not from the skill text):
- ATTACK THROTTLE. With 6 feathers the formula demands a hit every 0.267s, but
  Fienn's recording shows hits 0.3s apart - 31 of them in a Full Burst, the
  first 0.8s after FB entry. Modeled as a floor of 0.3s between feather hits,
  which reproduces that count exactly (0.8 + 30*0.3 = 9.8s < 10s window). The
  throttle only binds at 6 feathers; at 5 the formula already asks for 0.58s.
- The additive reading of the -16% is what matches the recording. Multiplicative
  (8 * 0.84^5 = 3.35s) predicts ~18 hits per Full Burst against 31 observed.
- The 0.8s startup lag is applied after every summon event, including battle
  start; only the post-burst lag was actually measured.
- Only the 6-feather window was measured directly. Lower feather counts use the
  formula unverified.

Not modeled / deferred:
- Feather targeting ("1 random enemy unit") - the solo raid has one boss.
"""
from app.skill_rules._helpers import buff_rule, round_buff_rule

SKILL_VALUE_MANIFESTS = {
    "ein": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_ein",
        "keys": {
            "feather_standby": ("skills", 0),
            "feather_shot": ("skills", 1),
            "feather_all_range": ("skills", 2),
        },
        # skill1's "Burst Skill Stage 3" is prose, not a value slot.
        "drop_tokens": {"feather_standby": (1,)},
    },
}

MAX_FEATHERS = 6
# Per-feather lifetime in seconds from its summon, F1..F6; None = unlimited.
FEATHER_LIFETIMES = (None, 38.0, 32.0, 26.0, 10.0, 10.0)
# Feathers 1-4 exist from battle start; 5-6 only ever arrive with her burst.
BATTLE_START_FEATHERS = 4
BASE_ATTACK_COOLDOWN = 8.0
COOLDOWN_REDUCTION_PER_EXTRA_FEATHER = 0.16
# Both measured from Fienn's Full Burst recording (2026-07-17).
SUMMON_STARTUP_LAG = 0.8
MIN_HIT_INTERVAL = 0.3


def _attack_cooldown(feather_count):
    """One feather's seconds-per-attack with `feather_count` alive."""
    reduction = COOLDOWN_REDUCTION_PER_EXTRA_FEATHER * (feather_count - 1)
    return BASE_ATTACK_COOLDOWN * (1 - reduction)


def _hit_interval(feather_count):
    """Seconds between feather hits from the squad's point of view: N feathers
    each attacking every `_attack_cooldown(N)` land N times per that window,
    never closer together than the observed throttle."""
    if feather_count <= 0:
        return None
    return max(_attack_cooldown(feather_count) / feather_count, MIN_HIT_INTERVAL)


def _summon_times(context, slug="ein"):
    """When feathers appear: battle start (F1-F4) and every Ein burst (F1-F6)."""
    return [0.0] + sorted(context.burst_times.get(slug, []))


def _feather_count_at(time, summons):
    """How many feathers are alive at `time`, from each feather's most recent
    summon and its own lifetime."""
    alive = 0
    for index in range(MAX_FEATHERS):
        # F5/F6 skip the battle-start summon; the rest take every summon.
        times = [t for t in summons if index < BATTLE_START_FEATHERS or t > 0.0]
        past = [t for t in times if t <= time]
        if not past:
            continue
        lifetime = FEATHER_LIFETIMES[index]
        if lifetime is None or time < max(past) + lifetime:
            alive += 1
    return alive


def _feather_hit_times(context, fight_duration, slug="ein"):
    """Every moment a Near Feather lands a hit. Deterministic: summons come from
    battle start plus Ein's burst times, and the cadence follows from how many
    feathers those leave alive. A summon resets every feather's attack cooldown,
    so each summon restarts the rhythm after the startup lag."""
    summons = _summon_times(context, slug)
    hits = []
    for index, summon in enumerate(summons):
        next_summon = summons[index + 1] if index + 1 < len(summons) else fight_duration
        window_end = min(next_summon, fight_duration)
        time = summon + SUMMON_STARTUP_LAG
        while time < window_end:
            hits.append(time)
            interval = _hit_interval(_feather_count_at(time, summons))
            if interval is None:
                break
            time += interval
    return hits


def feather_all_range_burst_percent(values):
    return float(values["feather_all_range"]["description_value_07"])


def build_ein_rules(values):
    standby = values["feather_standby"]
    all_range = values["feather_all_range"]

    self_atk = float(standby["description_value_02"]) / 100
    self_atk_duration = float(standby["description_value_03"])
    true_damage = float(all_range["description_value_02"]) / 100
    true_damage_duration = float(all_range["description_value_03"])
    charge_damage = float(all_range["description_value_04"]) / 100
    charge_damage_duration = float(all_range["description_value_05"])

    return [
        # She is the Burst-3 slot, so "entering Burst Skill Stage 3" is her cast.
        buff_rule("own_burst_activate", [
            ("atk_percent", self_atk, "self", self_atk_duration),
            ("true_damage_up", true_damage, "self", true_damage_duration),
            ("charge_damage_bonus", charge_damage, "self", charge_damage_duration),
        ]),
    ]


def build_ein_per_shot_rules(values):
    """Feather Shot: Charge Damage +80% for the next 1 round, on every Full
    Charge. SR shots are all full charges, so this fires every shot."""
    shot = values["feather_shot"]
    charge_damage = float(shot["description_value_03"]) / 100
    rounds = int(float(shot["description_value_04"]))
    return [(1, "every", [
        round_buff_rule("per_shot", [("charge_damage_bonus", charge_damage, "self")], shots=rounds),
    ])]


def build_ein_scheduled_nukes(values):
    """The Near Feather attacks - her main damage, as true damage."""
    shot = values["feather_shot"]
    percent = float(shot["description_value_02"])
    return [{
        "schedule": _feather_hit_times,
        "percent": percent,
        "damage_type": "true",
    }]
