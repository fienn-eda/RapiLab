"""아르카나 x 이사벨: 풀 버스트를 줄이는 Burst 3만이 수레바퀴 게이트를 연다.

아르카나의 조건부 불릿 셋(The Magician / Strength / Death)은 풀 버스트 종료 시에
그녀가 아직 수레바퀴(Wheel of Fortune) 상태인지 묻는다. 그녀는 버스트 스테이지 2에서
시전하고 그 상태는 10초짜리이므로, 표준 10초 창에서는 창이 끝날 때 이미 만료돼 있다.
창을 5초로 줄이는 이사벨(Full Burst Time -5 sec)과 같은 사이클에 터질 때만 조건이
성립한다.

대조군 채움은 `moran`이 아니라 `brid-silent-track`이다: 아르카나와 같은 Burst 2로
확인됐지만(`ENCODED_SLUGS`), moran의 실제 버스트 티어는 1(`data/lootandwaifus/
char_moran.json`의 "burst": 1)이라 그녀로 바꿔치기하면 덱 형태가 (1,2,2)에서
(2,1,2)로 바뀌어 사이클 타이밍째로 달라진다 - 원인이 아르카나의 부재가 아니라 덱
모양이 되어버린다. brid-silent-track은 Burst 2·`skill_cooldown_reduction_percent`
없음·`FULL_BURST_DURATION_DELTA`에 없음을 모두 만족한다. 그녀에게 스쿼드 범위
효과가 없는 건 아니다 - Wind Code 대상 Damage Taken 디버프가 둘(Ignition
Sequence·Journey Ahead) 있지만 이 테스트의 보스(Iron)에서는 게이트가 안 열려
둘 다 죽어 있고, 대신 자기 버스트(Full Throttle)의 스쿼드 flat ATK는 게이팅 없이
그대로 이사벨/네온에게 꽂힌다. 그래도 대조군으로 쓸 수 있는 건 방향 때문이다:
그 flat ATK는 "아르카나 없음" 쪽 기준선을 끌어올려서, 테스트 1의 배수는 오히려
**보수적**(실제보다 작게 측정)이 되고 테스트 2의 비율은 임계값에서 더 멀어진다
(실측 0.98x가 그 증거) - 즉 이 대조군은 두 테스트 모두 통과 쪽으로도 실패 쪽으로도
치우치지 않고, 오히려 스스로에게 불리한 방향으로 여유를 깎아 먹는다.
"""
from app.deck_search import BossProfile, evaluate_deck
from app.models import UserNikkeState
from app.user_roster import load_roster

BOSS = BossProfile(enemy_def=0, fight_duration=60.0, element="Iron",
                   gauge_charge_time=2.4, core_hittable=False,
                   part_destructible=False, effective_range_band=None)

# 아르카나와 같은 Burst 2이고, 스킬 쿨감도 FULL_BURST_DURATION_DELTA 항목도 없는
# 대조군 채움 (moran이 아닌 이유는 위 모듈 독스트링 참고).
CONTROL_B2 = "brid-silent-track"


def _specs(slugs):
    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in slugs
    ]
    specs, excluded = load_roster(states)
    assert not excluded, f"not usable: {excluded}"
    by_slug = {s.slug: s for s in specs}
    # 좌석 순서를 직접 고정한다: feasible_orderings로 탐색시키면 테스트가 좌석
    # 선택에 의존하게 된다.
    return [by_slug[slug] for slug in slugs]


def _run(slugs):
    return evaluate_deck(_specs(slugs), BOSS)


def _damage(result, slug, source=None):
    return sum(e["damage"] for e in result["damage_log"]
               if e["slug"] == slug and (source is None or e["source"] == source))


def _periodic_ticks(result, slug):
    return len([e for e in result["damage_log"]
                if e["slug"] == slug and e["source"] == "periodic"])


def test_the_bullets_land_when_isabel_opens_the_cycle():
    """이사벨이 창을 5초로 줄이면 아르카나의 수레바퀴가 풀 버스트 종료까지 살아남아
    Magician/Strength/Death가 발동한다."""
    with_isabel = _run(["liter", "arcana", "crown", "isabel", "cinderella"])
    without_arcana = _run(["liter", CONTROL_B2, "crown", "isabel", "cinderella"])
    # Strength(자ATK 180% flat) + Magician(공댐 +180%)을 받은 이사벨의 딜이
    # 아르카나를 뺀 같은 자리 대비 크게 높아야 한다.
    # 실측 비율 3.36x (128,405,128 vs 38,199,965) - 1.5x는 "효과 없음"(~1.0x)과
    # 실측값 사이에 넉넉한 여유를 둔다.
    assert _damage(with_isabel, "isabel") > _damage(without_arcana, "isabel") * 1.5


def test_the_bullets_do_not_land_behind_a_burst3_that_keeps_the_window_at_ten_seconds():
    """네온: 비전 아이도 전기 B3라 Magician/Strength의 대상 조건은 만족하지만,
    풀 버스트를 줄이지 않으므로 아르카나의 게이트가 열리지 않는다."""
    result = _run(["liter", "arcana", "crown", "neon-vision-eye", "cinderella"])
    baseline = _run(["liter", CONTROL_B2, "crown", "neon-vision-eye", "cinderella"])
    # 이 assert가 지키는 것: 창을 줄이는 아군이 없으면 전기 B3 캐리(네온)가
    # Magician/Strength를 받지 않는다는 것 - 받았다면 ratio가 1.2를 훌쩍 넘었을 것.
    # 실측 비율 0.98x (148,697,449 vs 151,770,286, 1.0 미만인 건 대조군 brid의
    # 스쿼드 flat ATK가 아르카나의 무조건 불릿보다 커서다) - 1.2x는 실측값 위에 여유를 둔다.
    ratio = _damage(result, "neon-vision-eye") / _damage(baseline, "neon-vision-eye")
    assert ratio < 1.2, (
        "네온이 Magician/Strength를 받고 있다 - 이사벨 없이 게이트가 열렸다는 뜻")


def test_isabel_pointed_feather_ticks_more_often_with_arcana_seated():
    """The Magician의 스킬 2 쿨감(-75%, 15초)이 이사벨의 Pointed Feather에 닿는다."""
    with_arcana = _run(["liter", "arcana", "crown", "isabel", "cinderella"])
    without_arcana = _run(["liter", CONTROL_B2, "crown", "isabel", "cinderella"])

    # 실측 8틱 vs 3틱. 절대 하한(>= 6)만으로는 아르카나와 무관한 변화로 이사벨이
    # 더 자주 틱해도 통과한다 - 비교(> without_arcana)를 같이 걸어야 원인이
    # 아르카나라는 것까지 고정된다. 절대 하한은 그 쿨감이 -75%에서 -10%처럼
    # 약해지는 회귀를 잡는다(3보다 크기만 한 값으로는 못 잡는 규모).
    with_ticks = _periodic_ticks(with_arcana, "isabel")
    without_ticks = _periodic_ticks(without_arcana, "isabel")
    assert with_ticks >= 6
    assert with_ticks > without_ticks
