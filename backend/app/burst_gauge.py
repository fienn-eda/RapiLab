"""버스트 게이지가 얼마나 차는가 - 상수와 산술이 사는 한 곳.

게이지는 **대미지가 아니라 타격 수**로 찬다. 코어 히트도, 크리티컬도, 적 DEF도
게이지를 안 바꾼다(Fienn 실측 2026-08-21, docs/measurements/burst-gauge-fill.md).
타격당 값은 무기군이 아니라 **유닛별**이고 같은 RL 안에서도 15배 벌어진다.

상수를 한곳에 두는 이유는 `paths.py`와 같다 - 흩어지면 같은 날 같은 방식으로 틀린다.
"""
import bisect

# 게이지를 가득 채우는 데 필요한 에너지. 단독편성 여섯 유닛이 독립적으로 이 값을
# 준다(앨리스 5발 x 98,000 = 490,000 = 판독 156/160px; 블랑 250발 x 2,000 = 정확히
# 이 값에서 완료). UI 가로 160px가 이 값에 대응한다.
GAUGE_FULL = 500_000

# 채움 시간을 이 격자로 snap한다. 게이지가 사이클 길이를 바꾸고 사이클 길이가
# 재장전 위치를 바꿔 다시 게이지를 바꾸므로, 연속값이면 고정점이 진동할 수 있다.
# 실측 폭이 1초 가까이(덱3 2.55~3.5초)라 이 해상도로 잃는 것이 없다.
#
# 0.05가 아니라 0.1인 것은 실측이다: 표본 400덱(cascade의 FIT_SAMPLE_DECKS)에서
# 0.05는 18덱이 `MAX_FULL_BURST_PASSES`(32) 안에 안 멈추고 0.1은 3덱이다.
# **더 굵을수록 안전한 것은 아니다** - 0.2와 0.25에서도 안 멈추는 덱이 남는다.
#
# 남는 3덱은 **주기 2의 극한 순환**이다. 진짜 고정점이 격자점 둘 사이에 있으면
# 양자화된 사상에는 고정점이 아예 없으므로, 격자를 바꾸는 것으로는 어느 덱이 그
# 경계에 앉는가만 바뀐다.
#
# **그 순환의 모양은 「격자 한 칸씩 번갈아 뛴다」가 아니다**(2026-08-22 실측).
# 대체로 한 칸인데 **꼬리의 한두 사이클이 4~9칸(0.4~0.9초)까지 벌어진다** - 예를
# 들어 셋 중 하나는 비교되는 일곱 사이클 중 다섯이 정확히 한 칸이고 마지막 둘만
# 4칸·2칸이다. 이유는 채움이 **접두사 안정화**라는 성질의 뒷면이다: 이른 사이클이
# 0.1초 밀리면 그 창의 종료가 밀리고, 재장전 위상이 밀려, 뒤 사이클에서는 한
# 매거진이 통째로 경계를 넘나든다. 그래서 폭은 사이클을 따라 커진다.
#
# 이 모양이 중요한 것은 `simulate_raid`의 감쇠가 **격자 한 칸 이내일 때만** 걸리기
# 때문이다 - 오늘 3덱은 꼬리 때문에 셋 다 가드에 걸려 감쇠가 아니라
# `FullBurstConvergenceWarning`을 받는다. 현재 수치는
# `scripts/check_gauge_convergence.py`가 사이클 간격까지 찍어 준다.
GAUGE_QUANTUM_SEC = 0.1

# 이 대미지 타입으로 기록된 스킬 대미지는 게이지를 안 채운다. **미측정이다** -
# `sustained`를 쓰는 열 슬러그(아크레인저: 블랙 · 브레디 · 디젤: 윈터 스위츠 ·
# 길로틴: 윈터 슬레이어 · 질 발렌타인 · 마나 · 미하라: 본딩 체인 · 레이븐 ·
# 로잔나: 시크 오션 · 사쿠라: 블룸 인 서머)는 전부 초당 DoT라 발사체가 아니고,
# 그래서 「타격」이 아닐 가능성이 높다는 **판단**이다. 실측 하나가 이 집합을 한
# 줄로 뒤집을 수 있어야 해서 자기 이름을 갖는다.
#
# `raid_simulator.NON_CORE_DAMAGE_TYPES`와 오늘 원소가 겹쳐 보이지만 그것은
# 「코어를 맞힐 수 있는가」라는 **다른 질문**에 답한다. 재사용하면 한쪽이 바뀔 때
# 다른 쪽이 조용히 뒤집힌다. `distributed`(광역으로 분산된 개별 타격)는 DoT가
# 아니므로 여기 없다 - 채운다.
GAUGE_INERT_DAMAGE_TYPES = frozenset({"sustained"})


def energy_per_hit(weapon_stats, *, full_charge):
    """이 무기의 타격 하나가 넣는 게이지 에너지.

    산탄은 펠릿이 개별로 세어진다. 풀차지 샷만 차지 배율을 받는다 - 부분 차지
    (톡톡이)는 차지 비율과 무관하게 기본값이고, 그것이 헬름을 113%와 106%로 쏜 두
    발이 합쳐 정확히 기본값 두 개였던 판독이다.

    차지 배율에 `charge_damage_percent`를 쓰는 것은 우연이 아니다 - 원본 데이터의
    `full_charge_burst_energy`가 `full_charge_damage`와 **차지 무기에서 값이 같다**.
    그 동일성은 `scripts/audit_burst_energy.py`가 지킨다.
    """
    energy = weapon_stats["burst_energy_pershot"] * weapon_stats.get("pellets_per_shot", 1)
    if not full_charge:
        return energy
    multiplier = weapon_stats.get("charge_damage_percent", 0.0) / 100
    return energy * multiplier if multiplier > 1 else energy


def quantize(seconds):
    """채움 시간을 고정점이 멈출 수 있는 격자로 내린다."""
    return round(seconds / GAUGE_QUANTUM_SEC) * GAUGE_QUANTUM_SEC


def fill_times(shots_by_slug, full_burst_ends, *, weapon_stats, fight_duration,
               ammo_rounds_by_slug=None, bonus_fills=(), speed_multiplier_at=None,
               skill_hits_by_slug=None):
    """풀 버스트가 끝난 뒤 게이지가 다시 가득 차기까지 걸리는 시간, 사이클마다.

    `shots_by_slug`는 `{슬러그: [(시각, 톡톡이 여부), ...]}`. 대미지 경로와
    직교한다 - 코어히트도 크리티컬도 ATK도 적 DEF도 여기 안 들어온다.

    `skill_hits_by_slug`(`{슬러그: [(시각, 타격 수), ...]}`)는 **무기가 쏘지
    않은** 타격이다 - 라이더(자기 타격에 얹히는 추가 대미지)·드론·오토파이어·
    주기 타격. 값은 유닛별 표가 아니라 **그 유닛 무기의 기본 에너지** 하나이고,
    세 유닛이 독립적으로 그것을 준다(헬름의 애장품 추댐 1.000x · 리버렐리오의
    5회 라이더 1.015x/1.035x · 헤비암즈의 오토파이어 1.015x; measurements/
    burst-gauge-fill.md 「정정」·「증분만으로 한 전수 검산」). 풀차지 배율은
    **그 유닛의 무기가 쏜 샷**에만 붙으므로 여기 있는 타격은 배율을 안 받고,
    탄약을 안 쓰므로 아군 누적 소모탄 카운터에 0을 기여한다.

    `bonus_fills`는 무기 타격과 다른 채움원 - 「어떤 트리거에 게이지의 X%를
    얹는다」 - 목록이다. 원소가 **어느 키를 갖는가**가 트리거 종류를 말한다.

    - `{"every_ally_rounds": N, "fraction": X}` - 아군 누적 소모탄이 N발에 닿을
      때마다(인어공주 Bubble Order, 신데렐라: 크리스탈 웨이브 Beauty-Full).
    - `{"every_own_full_charge": 슬러그, "fraction": X}` - 그 좌석의 무기가
      풀차지 샷을 쏠 때마다(헬름 애장품 Frontline Command, 매치스 맥스웰
      Output Switching Sequence). 원문이 "Full Charge attack"이라 톡톡이(부분
      차지)와 스킬이 만든 타격은 트리거가 아니고, 원문의 "Affects all allies"는
      **스쿼드 게이지에 한 번** 들어간다는 뜻이지 좌석 수만큼이 아니다 - 5를
      곱하면 헬름 한 명이 풀차지 두 발로 게이지를 채워 실측(3발)과 어긋난다.

    아래는 아군 소모탄 종류의 회계다. 소모탄 카운터는
    `ammo_rounds_by_slug`(`shots_by_slug`와 나란한 {슬러그: [발당 라운드, ...]} -
    탄약 주머니를 쓰는 아군은 한 발이 수백 라운드를 회계한다)가 센다. **이 카운터는 전투 시작부터 절대 안 빈다** - 원문이 "total ammo
    expended by allies"이고, `little_mermaid.build_bubble_barrage_scheduled_nukes`의
    기존 구현도 전 전투 타임라인을 병합해 같은 방식으로 센다. 게이지 자체는
    버스트로 비워지지만(그래서 무기 타격 에너지는 사이클마다 0에서 다시 쌓는다)
    아군 소모탄 카운터는 버스트와 무관한 별개 값이라 안 빈다 - 창이 시작되는
    시점의 **누적값**을 위상으로 이어받아야 그 창에서 처음 넘는 문턱까지의
    거리가 맞다. 창마다 0에서 다시 세면(예전 근사) 문턱이 창 길이에 육박하는
    덱(400발 문턱 vs 초당 ~118발인 덱2의 3.4초 창)에서 트리거가 거의 매번
    창 하나를 다 써야 도착해, 실측보다 한참 느린 채움 시간이 나온다
    (`scripts/quantify_ally_rounds_accounting.py`: 덱2 정상상태 ~5.5초(창-리셋)
    vs ~2.4~2.7초(누적) - 거의 두 배). 여러 충전원이 있는 덱에서는 **모두가 같은
    카운터를 공유**한다(문턱은 원마다 다르다) - 원마다 따로 세면 아군 발수를
    소스 수만큼 중복 계상한다. 한 샷이 자기 문턱을 여러 번 넘을 수 있다(주머니
    발 하나가 수백 라운드를 회계하면).

    `speed_multiplier_at`(옵션, `(슬러그, 시각) -> 배율`)은 타격당 에너지에
    곱하는 샷별 배율이다 - 「버스트 게이지 충전 속도」 스탯(아니스: 스타·
    그레이브·마나)의 스코프가 squad(모든 슬러그가 같은 값)와 self(그 슬러그만)
    둘 다 있고, 값이 전투 도중 켜지고 꺼지므로(그레이브의 Heat Emission, 마나의
    Metal σ) 창 전체에 쓰는 스칼라 하나로는 이 셋을 같은 자리에서 표현할 수
    없다. 안 주면 전부 1.0(오늘과 동일). **`bonus_fills`엔 안 걸린다 - 두 종류
    다** - 곱해지는 항이 아니라 별개로 더해지는 항이라서다(아래 루프).
    무기 타격에 이 배율이 걸리는 것은 실측(아니스: 스타의 원문 "버스트 게이지
    충전 속도")이 확정하지만, 같은 배율이 스킬이 주는 플랫 충전(예: 인어공주
    Bubble Order)에도 걸리는지는 **미측정**이다 - 지금은 안 걸리는 쪽으로 두고,
    다음 실측이 뒤집기 전까지는 이게 보수적인 기본값이다. `skill_hits_by_slug`의
    타격에는 **걸린다** - 스탯의 원문이 「버스트 게이지 충전 속도」이지 「무기
    타격의 충전 속도」가 아니므로, 타격을 가려 걸 근거가 없다.

    **무기 쪽에서 세는 단위는 샷 레코드 하나, 즉 방아쇠 하나다.** 실측이 정한
    단위는 방아쇠가 아니라 **타격**이고(measurements/burst-gauge-fill.md), 둘이
    갈리는 자리가 둘 있다. 산탄은 `energy_per_hit`이 `pellets_per_shot`을 곱해
    맞춘다.
    **관통은 아직 안 맞춘다** - 「관통으로 n개 객체를 타격하면 게이지도 n배」가
    실측에 있지만 여기서는 방아쇠 하나가 곱해지지 않은 채 한 번 세어진다.
    보류인 이유: 엔진의 관통 2인스턴스는 `pierce_hits_body_behind_core`에
    게이트돼 있고 게이지를 잰 인카운터는 그 값이 거짓이라(코어도 못 맞히는
    환경) 실측 덱들에서 관통은 애초에 발동하지 않았다. 지금 배선하면 측정되지
    않은 상호작용 위에 짓는 것이다. `docs/engine-gaps.md` 참조.

    키는 `full_burst_ends`의 인덱스에 **+1**이다. 풀 버스트 k의 종료에서 잰
    채움이 지배하는 것은 사이클 k+1이기 때문이다 - `burst_cycle`의
    `gauge_ready = time + gauge[cycle_index]`에서 `time`이 직전 풀 버스트의
    종료다. 사이클 0(개전 -> 첫 버스트)은 표에 없고 시드가 답한다: 개전 게이지
    0에서의 채움은 이 모델의 범위 밖이다.

    게이지는 **창 밖에서만** 찬다(창 안에서도 찬다는 가설은 실측으로 기각됐다 -
    그러면 다섯 덱 전부가 창 종료 전에 가득 차서 덱2의 3.7초 판독을 설명 못 한다).
    초과분은 다음 사이클로 이월되지 않는다.

    전투가 끝날 때까지 못 채우는 사이클은 **`float("inf")`로 싣는다.** 표에서
    빼면 `burst_cycle`의 `.get(cycle_index, gauge_charge_time)`이 보스 시드(2.4초)로
    떨어져 「이 사이클은 절대 못 찬다」가 「거의 모든 실덱보다 빨리 찬다」로
    뒤집히고, 그 사이클이 공짜로 터진다 - 이득을 보는 것이 하필 게이지가 느려서
    못 채우는 덱이라 편향의 방향이 이 기능의 존재 이유와 정확히 반대다. 무한대면
    스케줄러의 `fire_time = max(gauge_ready, ...)`가 무한대가 되어 그쪽의
    `fight_duration` 검사가 사이클을 제대로 끊는다.

    못 채우는 사이클은 **접미사**다 - `end`가 사이클마다 뒤로만 가므로 사이클
    k+1이 보는 타격 집합은 사이클 k가 본 집합의 부분집합이고, 아군 누적 소모탄의
    크로싱 수도 같은 이유로 줄기만 한다. 그래도 판정은 사이클마다 따로 하므로
    중간에 구멍이 나는 날에도 그 사이클 하나만 무한대가 된다.

    게이지값이 있는 좌석도 `bonus_fills`도 **하나도 없는** 입력은 예외다 - 그때는
    표가 통째로 비고 시드가 모든 사이클을 답한다. 그 경우의 「안 참」은 덱의 성질이
    아니라 **입력의 부재**이고, 그것을 무한대로 답하면 게이지 데이터를 안 주는
    호출자(손으로 만든 무기 프로필)의 전투가 사이클 0에서 끝난다. 실덱은 이
    가지에 못 들어온다: `load_roster`가 게이지값 없는 유닛을 아예 제외한다.

    아래 `fight_duration` 검사는 창 밖 적산이 전투 종료에서 멈추게 한다: 오늘의
    발사 생성기는 종료 시각을 넘겨 쏘지 않으므로(실측 175,259발 중 0발) 검사가
    걸리는 일은 없지만, 그 성질은 이 함수의 것이 아니라 호출자의 것이다.
    """
    # 게이지값이 없는 무기 프로필은 아무것도 안 채운다. 실제 유닛은 값이 없으면
    # `load_roster`가 아예 제외하므로 여기 오지 않는다 - 이 관용이 받는 것은
    # 손으로 만든 무기 프로필(테스트·스텁)뿐이다.
    per_hit = {
        slug: (energy_per_hit(stats, full_charge=False),
               energy_per_hit(stats, full_charge=True))
        for slug, stats in weapon_stats.items()
        if stats.get("burst_energy_pershot")
    }
    # 채움원이 **하나도** 없으면 표를 아예 안 낸다. 「이 덱은 못 채운다」가 아니라
    # 「잴 것이 없다」라서다 - 없는 입력을 무한대로 답하면 스케줄러가 첫 사이클
    # 뒤에 전투를 끝낸다. 실제 유닛은 게이지값이 없으면 `load_roster`가 제외하므로
    # (`_weapon_stats`가 `None`을 돌려준다) 프로덕션 덱에서는 이 가지가 안 열리고,
    # 그래서 아래 무한대가 실덱에서 약해지지 않는다.
    if not per_hit and not bonus_fills:
        return {}
    ammo_rounds_by_slug = ammo_rounds_by_slug or {}
    speed_multiplier_at = speed_multiplier_at or (lambda slug, time: 1.0)
    # (시각, 슬러그, 종류, 타격 수, 소모 라운드). `종류`는 어느 에너지를 쓰는지를
    # **이름으로** 말한다 - 스킬 타격을 톡톡이 불리언에 태우면 값은 맞지만 읽는
    # 사람이 「이건 부분 차지 샷이구나」로 틀린다.
    merged = sorted(
        [(time, slug, "tap" if is_tap else "charged", 1, rounds)
         for slug, shots in shots_by_slug.items()
         # `strict=True`: 두 목록은 같은 `shot_records`에서 나오므로 프로덕션에선
         # 항상 나란하다. 어긋나는 날 `zip`이 잘라 버리면 **게이지에서만** 샷이
         # 조용히 사라지고 대미지는 멀쩡해, 어디가 틀렸는지 알 길이 없다.
         for (time, is_tap), rounds in zip(
             shots, ammo_rounds_by_slug.get(slug) or [1.0] * len(shots),
             strict=True)]
        + [(time, slug, "skill", count, 0.0)
           for slug, hits in (skill_hits_by_slug or {}).items()
           for time, count in hits]
    )
    # 트리거 종류로 미리 갈라 둔다 - 샷마다 두 종류를 다시 판별하지 않고,
    # 아군 소모탄 원이 없는 덱은 아래 누적합도 아예 안 만든다.
    ally_round_fills = [f for f in bonus_fills if "every_ally_rounds" in f]
    full_charge_fills = [f for f in bonus_fills if "every_own_full_charge" in f]
    # 아군 누적 소모탄의 위상: 각 창의 시작(`end`) 이전에 이미 쌓인 라운드 수.
    # `merged`가 시각순이라 이분 탐색 + 누적합으로 창마다 다시 훑지 않고 구한다.
    if ally_round_fills:
        ally_round_times = [m[0] for m in merged]
        ally_round_prefix = [0.0]
        for m in merged:
            ally_round_prefix.append(ally_round_prefix[-1] + m[4])
    out = {}
    for cycle_index, end in enumerate(full_burst_ends):
        gauge = 0.0
        if ally_round_fills:
            ally_rounds = ally_round_prefix[bisect.bisect_left(ally_round_times, end)]
        # 가득 차는 순간에 덮어쓴다. 안 덮이면 그 사이클은 전투가 끝날 때까지
        # 못 채운다는 뜻이고, 무한대가 그것을 스케줄러에 말하는 방식이다.
        out[cycle_index + 1] = float("inf")
        for time, slug, kind, hits, rounds in merged:
            if time < end:
                continue
            if time >= fight_duration:
                break
            base, charged = per_hit.get(slug, (0.0, 0.0))
            # 풀차지 배율은 **그 유닛의 무기가 쏜** 샷에만 붙는다 - 톡톡이도
            # 스킬 타격도 기본값이다.
            energy = charged if kind == "charged" else base
            gauge += energy * hits * speed_multiplier_at(slug, time)
            if ally_round_fills:
                before = ally_rounds
                ally_rounds += rounds
                for fill in ally_round_fills:
                    threshold = fill["every_ally_rounds"]
                    crossings = int(ally_rounds // threshold) - int(before // threshold)
                    if crossings:
                        gauge += crossings * fill["fraction"] * GAUGE_FULL
            if kind == "charged":
                # 「자신이 풀차지로 공격할 때마다」 - 그 좌석의 무기가 쏜 풀차지
                # 샷 하나에 한 번. 「아군 전체」는 스쿼드 게이지에 한 번 들어가는
                # 것이지 좌석 수만큼이 아니다.
                for fill in full_charge_fills:
                    if slug == fill["every_own_full_charge"]:
                        gauge += fill["fraction"] * GAUGE_FULL
            if gauge >= GAUGE_FULL:
                out[cycle_index + 1] = quantize(time - end)
                break
    return out
