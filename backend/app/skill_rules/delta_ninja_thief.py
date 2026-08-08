"""Delta: Ninja Thief (slug "delta-ninja-thief"), a Burst-2 Water MG defender.
Values from ShiftyPad; effect text cross-read from lootandwaifus.

Modeled (DPS-relevant):
- Ninjutsu Acid Bomb (skills[0]):
  - on Full Burst enter, all enemies Damage Taken +12% for 15 sec. Squad scope,
    the engine's shape for an enemy debuff - every attacker collects it.
  - on her own burst, self ATK +15.04% for 10 sec. "Affects self", read
    literally: the squad does not get this one.
  - on her own burst, Ninjutsu Hyper Acid Bomb, Damage Taken +8% for 10 sec on
    "enemies within attack range nearest to the crosshair". The solo raid has
    one boss and she is shooting it, so the targeting resolves to that boss;
    modeled as a squad-scope enemy debuff like the bullet above.
- Secret Technique: Ninja Overdrive (skills[2], her burst, cd 40):
  - 170% of final ATK as DISTRIBUTED damage (`_BURST_DAMAGE_TYPES`), so squad
    `distributed_damage_up` buffs - including her own, below - reach it.
  - squad Distributed Damage +20% for 10 sec. This is a DPS buff, not a
    defensive one; it lands only on distributed-typed instances, which in a
    deck means her own burst plus any other distributed dealer (Scarlet: Black
    Shadow, Phantom, Quency, Bready, Milk).
  - squad ATK +15% of HER ATK for 10 sec, as `flat_atk` off `caster_atk`.

Not modeled / deferred:
- All of Ninjutsu Camouflage (skills[1]). Every bullet is survivability: the
  battle-start branch is a Max-HP shield or a single-target-attack dodge, the
  200-normal-attack bullet is another shield, and Ninjutsu Injection /
  Ninjutsu IFAK are lifesteal and a stored group heal. The AMOUNTS are not
  damage; the IFAK heal's OCCURRENCE is, which is why she is in
  `HEAL_PROVIDER_SLUGS` - a deck-mate whose bullet arms on any ally healing
  (Crown) sees her.
- Her shield reaches only herself ("Affects self"), so it is in
  `SELF_ONLY_SHIELD_SLUGS`, NOT `SHIELD_PROVIDER_SLUGS`: a shield consumer like
  Naga asks whether a shield was placed in front of IT, and Delta's never is.
- The burst's two status-gated riders, "Next shield's HP +20.13%" and "Maximum
  Accumulation of Ninjutsu IFAK +20.13%". Both scale a survivability quantity
  the engine does not model, so there is nothing for them to scale.
- Attract (the taunt). The engine has no aggro model, and the taunt gates only
  the shield bullets above.
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "delta-ninja-thief": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_delta_ninja_thief",
        "keys": {
            "ninjutsu_acid_bomb": ("skills", 0),
            "ninjutsu_camouflage": ("skills", 1),
            "ninja_overdrive": ("skills", 2),
        },
    },
}


def ninja_overdrive_burst_percent(values):
    return float(values["ninja_overdrive"]["description_value_05"])


def build_delta_ninja_thief_rules(values):
    acid = values["ninjutsu_acid_bomb"]
    overdrive = values["ninja_overdrive"]
    caster_atk = values["caster_atk"]

    acid_bomb = float(acid["description_value_01"]) / 100
    acid_bomb_duration = float(acid["description_value_02"])
    self_atk = float(acid["description_value_03"]) / 100
    self_atk_duration = float(acid["description_value_04"])
    hyper_acid_bomb = float(acid["description_value_05"]) / 100
    hyper_duration = float(acid["description_value_06"])

    distributed = float(overdrive["description_value_01"]) / 100
    distributed_duration = float(overdrive["description_value_02"])
    squad_atk = float(overdrive["description_value_03"]) / 100 * caster_atk
    squad_atk_duration = float(overdrive["description_value_04"])

    return [
        buff_rule("full_burst_enter", [
            ("damage_taken_up", acid_bomb, "squad", acid_bomb_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("atk_percent", self_atk, "self", self_atk_duration),
            ("damage_taken_up", hyper_acid_bomb, "squad", hyper_duration),
            ("distributed_damage_up", distributed, "squad", distributed_duration),
            ("flat_atk", squad_atk, "squad", squad_atk_duration),
        ]),
    ]
