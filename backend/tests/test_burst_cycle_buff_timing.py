"""버스트 사이클에서 어떤 트리거의 버프가 어떤 버스트 넉에 닿는가.

Fienn의 정본 로테이션(2026-07-24)에 대한 엔진의 답을 고정한다:
  게이지 충전 -> 1단계 진입 -> B1 사용 -> 2단계 진입 -> B2 사용
  -> 3단계 진입 -> B3 사용 -> 풀버스트 10초
엔진에는 "N단계 진입"이라는 별도 이벤트가 없다: `on_tier_fire`가 곧 "BN 사용"이고
`full_burst_enter`는 tier-3 발동 **직후**(`FULL_BURST_OPEN_DELAY`)에 발동한다 —
로테이션의 마지막 화살표가 순서를 갖는다는 뜻이다. 그래서 **어떤 티어든 자기 버스트
넉은 full_burst_enter 버프를 못 읽는다**. 해설은 docs/insights.md 참고.
"""
from app.effects import Effect
from app.raid_simulator import simulate_raid
from app.squad_engine import SkillRule


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats():
    return {
        "buffer": {"atk": 10000, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "attacker": {"atk": 10000, "def": 0, "max_hp": 0},
    }


def empty_rules():
    return {"buffer": [], "midtier": [], "attacker": []}


def attack_damage_rule(trigger, target_slug):
    """target_slug 본인에게 Attack Damage +50%를 영구 부여하는 룰."""

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", 0.5, "self", None, target_slug),
            applied_at=time,
        )

    return SkillRule(trigger=trigger, action=action)


def run(rules_by_slug, burst_percents, mode="auto"):
    return simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents=burst_percents,
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode=mode,
        base_crit_rate=0.0,
    )


def test_full_burst_enter_buff_misses_the_tier3_own_burst_nuke():
    """B3의 캐스트가 먼저 끝나고 **그 다음에** 풀버스트가 열리므로(로테이션 그대로),
    B3 자신의 버스트 넉은 full_burst_enter 버프를 못 읽는다. Fienn의 사격장 실측이
    이것을 확정했다(2026-07-27, docs/decisions.md)."""
    baseline = run(empty_rules(), {"attacker": 1000.0})
    rules = empty_rules()
    rules["attacker"] = [attack_damage_rule("full_burst_enter", "attacker")]
    buffed = run(rules, {"attacker": 1000.0})

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"]


def test_own_burst_activate_buff_reaches_the_tier3_own_burst_nuke():
    """own_burst_activate 룰은 넉이 기록되기 전에 발동하므로 당연히 닿는다."""
    baseline = run(empty_rules(), {"attacker": 1000.0})
    rules = empty_rules()
    rules["attacker"] = [attack_damage_rule("own_burst_activate", "attacker")]
    buffed = run(rules, {"attacker": 1000.0})

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"] * 1.5


def test_full_burst_enter_buff_misses_a_tier1_own_burst_nuke_in_auto_mode():
    """auto 모드는 tier 간 gap이 0이라 B1 넉이 B3 캐스트와 동시각인데, 풀버스트는
    그 **뒤에** 열린다 -> 여기서도 못 읽는다. manual 모드(아래)와 결론이 같아졌다:
    **자기 버스트딜에 곱해져야 하는 버프는 티어·모드와 무관하게 own_burst_activate를
    써야 한다.**"""
    baseline = run(empty_rules(), {"buffer": 1000.0}, mode="auto")
    rules = empty_rules()
    rules["buffer"] = [attack_damage_rule("full_burst_enter", "buffer")]
    buffed = run(rules, {"buffer": 1000.0}, mode="auto")

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"]


def test_full_burst_enter_buff_misses_a_tier1_own_burst_nuke_in_manual_mode():
    """manual 모드는 tier 간 0.1초 간격이라 B1 넉이 full_burst_enter보다 0.2초 먼저
    발생한다 -> 그 넉은 버프를 못 읽는다. B1/B2의 자기 버스트딜에 곱해져야 하는
    버프는 own_burst_activate를 써야 한다는 근거."""
    baseline = run(empty_rules(), {"buffer": 1000.0}, mode="manual")
    rules = empty_rules()
    rules["buffer"] = [attack_damage_rule("full_burst_enter", "buffer")]
    buffed = run(rules, {"buffer": 1000.0}, mode="manual")

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"]
