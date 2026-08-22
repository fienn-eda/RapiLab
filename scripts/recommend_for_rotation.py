"""저장된 레이드 회차 보스에 대고 추천을 돌려 결과를 읽을 수 있게 찍는다.

앱을 띄우지 않고 **앱과 같은 경로로** 같은 답을 받아 보려는 도구다. 두 모드를
앱과 같은 함수로 돈다:

- `raid` (앱의 「전부 최적화」) — `recommend_from_draft`로 5덱을 배분한다.
  `num_decks`는 API에서 **최대 5**로 막혀 있으므로 이 모드에 「20등」은 없다.
- `single` (앱의 「단일 덱」) — `search_best_decks`로 상위 N덱을 줄 세운다.
  「어떤 조합이 말이 되나」를 훑는 건 이쪽이다.

보스 값은 `data/raid-rotations.json`(회차 공지에서 읽어 둔 것)에서 오고, 공지에
없는 값은 **앱의 기본값**을 그대로 쓴다 - 그래야 여기 숫자가 Fienn이 앱에서 보는
숫자와 같다. 방어력이 그 예다: 솔로와 유니온 보스가 값이 다르므로 공유 기본값
하나로는 한쪽이 틀린다(`RecommendPanel.SOLO_RAID_DEFAULT_ENEMY_DEF`).

**코어 타격은 기본이 꺼짐이다.** 공지가 말해 주는 값이 아니라 그 보스를 관측해서
나오는 값이고(`core_diameter_px`도 같은 계열), 켜면 MG 딜의 상당 부분이 코어
보너스로 들어와 순위가 움직인다. 켜고 보려면 `--core-hittable`.

한글 이름이 섞이므로 결과는 **UTF-8 파일**로 쓴다 - 이 저장소의 콘솔은 cp949라
찍으면 깨진다(`--out`으로 경로 지정).

Usage (any cwd):
    python3 scripts/recommend_for_rotation.py --rotation solo-40
    python3 scripts/recommend_for_rotation.py --rotation solo-40 \
        --exclude season-excludes.txt --mode both --top-n 20
"""
import argparse
import json
import sys
import time
import unicodedata
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.deck_allocation import recommend_from_draft  # noqa: E402
from app.deck_search import (BossProfile, RANKING_MAX_PASSES,  # noqa: E402
                             character_of, search_best_decks)
from app.display_names import DISPLAY_NAMES  # noqa: E402
from app.elements import weakness_of  # noqa: E402
from app.raid_simulator import FullBurstConvergenceWarning  # noqa: E402
from app.sim_pool import SimPool  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402

# 앱이 솔로 레이드 보스에 쓰는 기본 방어력. 유니온 보스는 다른 값이라 공유하지
# 않는다(frontend/src/components/RecommendPanel.tsx의 같은 이름 상수).
SOLO_RAID_DEFAULT_ENEMY_DEF = 31784.0
ELEMENTS = ("Fire", "Water", "Wind", "Iron", "Electric")


def boss_element_for(weakness):
    """이 속성이 약점인 보스의 본인 속성.

    `BossProfile.element`는 보스 **자신의** 속성인데 공지와 화면은 **약점**으로
    말한다(프론트의 `bossElementFor`가 같은 변환을 한다). 표를 여기 다시 쓰지
    않고 공개 함수 `weakness_of`를 뒤집어 찾는다 - 두 표가 어긋날 자리를 안
    만든다.
    """
    for element in ELEMENTS:
        if weakness_of(element) == weakness:
            return element
    raise SystemExit(f"약점 속성을 모르겠다: {weakness!r}")


def name(slug):
    return DISPLAY_NAMES.get(slug) or slug


def season_subset(specs, path):
    """제외 목록(한글 표시명, 한 줄에 하나, `#`은 주석)을 뺀 로스터.

    「같은 캐릭터인가」는 `character_of`가 답한다 - 문자열 접두사로는 「브래디(지딜)」
    (같은 캐릭터의 모드 변형)과 「레이(가칭)」(다른 캐릭터)이 안 갈린다.
    못 찾은 이름이 하나라도 있으면 멈춘다: 제외했다고 믿은 유닛이 편성에 들어간
    결과는 아무것도 안 말한다.
    """
    by_name = {}
    for slug, korean in DISPLAY_NAMES.items():
        if korean:
            key = unicodedata.normalize("NFC", korean).replace(" ", "")
            by_name.setdefault(key, []).append(slug)
    wanted = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
    wanted = [n for n in wanted if n and not n.startswith("#")]
    characters, missing = set(), []
    for n in wanted:
        slugs = by_name.get(unicodedata.normalize("NFC", n).replace(" ", ""))
        if not slugs:
            missing.append(n)
            continue
        characters.update(character_of(s) for s in slugs)
    if missing:
        raise SystemExit(f"제외 목록에서 못 찾은 이름: {', '.join(missing)}")
    return [u for u in specs if character_of(u.slug) not in characters]


def find_boss(rotation_id, boss_index):
    doc = json.loads((ROOT / "data" / "raid-rotations.json").read_text(encoding="utf-8"))
    for rot in doc["rotations"]:
        if rot["id"] == rotation_id:
            if boss_index >= len(rot["bosses"]):
                raise SystemExit(f"{rotation_id}에 보스가 {len(rot['bosses'])}마리뿐이다")
            return rot, rot["bosses"][boss_index]
    known = ", ".join(r["id"] for r in doc["rotations"])
    raise SystemExit(f"회차 {rotation_id!r}를 모른다. 아는 것: {known}")


def deck_lines(entry, index=None):
    head = f"{index:>3}. " if index is not None else "     "
    out = [f"{head}{entry['total_damage']:>18,.0f}   "
           + " · ".join(name(s) for s in entry["deck"])]
    share = []
    for label, key in (("버스트", "burst_damage"), ("평타", "normal_attack_damage"),
                       ("스킬", "skill_damage")):
        value = entry.get(key)
        if value and entry["total_damage"]:
            share.append(f"{label} {value / entry['total_damage'] * 100:.0f}%")
    if share:
        out.append(f"          {' / '.join(share)}")
    for key, label in (("hold_burst_slugs", "버스트 보류"),
                       ("tap_fire_slugs", "톡톡이"),
                       ("hold_fire", "홀드 파이어")):
        if entry.get(key):
            out.append(f"          {label}: "
                       + ", ".join(name(s) for s in entry[key]))
    if entry.get("seating"):
        seats = "; ".join(f"{name(s)} 옆 {', '.join(name(m) for m in mates)}"
                          for s, mates in entry["seating"].items())
        out.append(f"          자리: {seats}")
    missed = entry.get("gauge_missed_cycles")
    if missed:
        out.append(f"          버충 밀림: {missed}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(ap)
    ap.add_argument("--rotation", default="solo-40", help="회차 id (기본 solo-40)")
    ap.add_argument("--boss-index", type=int, default=0,
                    help="유니온처럼 보스가 여럿인 회차에서 몇 번째인지 (기본 0)")
    ap.add_argument("--exclude", metavar="PATH", help="안 쓸 니케의 한글 이름 목록")
    ap.add_argument("--mode", choices=["raid", "single", "both"], default="both",
                    help="raid=전부 최적화(5덱 배분) · single=단일 덱 상위 N")
    ap.add_argument("--top-n", type=int, default=20, help="single 모드 순위 길이")
    ap.add_argument("--keep-orderings", action="store_true",
                    help="같은 유닛 조합의 다른 배치도 각각 한 줄로 센다 "
                         "(기본은 조합당 최선의 배치 하나)")
    ap.add_argument("--num-decks", type=int, default=5, help="raid 모드 덱 수 (최대 5)")
    ap.add_argument("--enemy-def", type=float, default=SOLO_RAID_DEFAULT_ENEMY_DEF)
    ap.add_argument("--duration", type=float, default=180.0)
    ap.add_argument("--core-hittable", action="store_true",
                    help="코어를 실제로 때릴 수 있는 보스로 본다 (기본 꺼짐)")
    ap.add_argument("--out", default=str(ROOT / "rotation-recommendation.txt"))
    args = ap.parse_args()

    rot, boss_data = find_boss(args.rotation, args.boss_index)
    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"동기화된 로스터가 없다: {args.roster}")
    specs, _ = load_roster(states)
    full = len(specs)
    if args.exclude:
        specs = season_subset(specs, args.exclude)

    weakness = boss_data["weakness"]
    boss = BossProfile(
        element=boss_element_for(weakness),
        core_hittable=args.core_hittable,
        enemy_def=args.enemy_def,
        fight_duration=args.duration,
        part_destructible=bool(boss_data.get("part_destruction_times")),
        part_destruction_times=tuple(boss_data.get("part_destruction_times") or ()),
        spawns_adds=bool(boss_data.get("spawns_adds")),
        effective_range_band=boss_data.get("range_band"),
    )

    lines = [
        f"# {rot['title']} — {boss_data['name']}",
        f"보스 속성 {boss.element} / 약점 {weakness} · 거리 {boss.effective_range_band}"
        f" · 방어력 {boss.enemy_def:,.0f} · {boss.fight_duration:.0f}초"
        f" · 코어 타격 {'켬' if boss.core_hittable else '끔'}"
        f" · 잡몹 {'있음' if boss.spawns_adds else '없음'}"
        f" · 파츠 파괴 {list(boss.part_destruction_times) or '없음'}",
        f"로스터 사용 가능 {full}유닛"
        + (f" → 제외 후 {len(specs)}유닛" if args.exclude else ""),
        f"랭킹 패스 캡 {RANKING_MAX_PASSES} (표시되는 총딜은 고정점까지 간다)",
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FullBurstConvergenceWarning)
        if args.mode in ("raid", "both"):
            t0 = time.perf_counter()
            out = recommend_from_draft(specs, boss, num_decks=args.num_decks,
                                       draft=[], locked=set(), workers="auto")
            elapsed = time.perf_counter() - t0
            decks = out["recommended"]["decks"]
            total = sum(d["total_damage"] for d in decks)
            lines += ["", f"## 전부 최적화 — {len(decks)}덱 배분 ({elapsed:.0f}초)",
                      f"합계 {total:,.0f}"]
            for i, entry in enumerate(decks, 1):
                lines += deck_lines(entry, i)
            bench = out["recommended"].get("leftover_slugs") or []
            if bench:
                lines.append("  벤치: " + ", ".join(name(s) for s in bench))

        if args.mode in ("single", "both"):
            # 순위는 **배치 순서까지** 다른 덱을 따로 센다. 「어떤 조합이 말이 되나」를
            # 보려는 목록에서는 그게 방해다 - 같은 다섯 유닛의 순열이 상위를 통째로
            # 채운다(실측: 1~3위가 전부 같은 조합이었다). 그래서 넉넉히 뽑아
            # **유닛 집합 기준으로 접고**, 각 조합의 가장 좋은 배치만 남긴다.
            want = args.top_n * (1 if args.keep_orderings else 8)
            t0 = time.perf_counter()
            with SimPool(specs, boss, workers="auto") as pool:
                ranked = search_best_decks(specs, boss, top_n=want, pool=pool)
            elapsed = time.perf_counter() - t0
            if not args.keep_orderings:
                best_of = {}
                for entry in ranked:          # 이미 총딜 내림차순이라 첫 것이 최선이다
                    best_of.setdefault(frozenset(entry["deck"]), entry)
                ranked = list(best_of.values())[:args.top_n]
                label = f"서로 다른 조합 상위 {len(ranked)}"
            else:
                ranked = ranked[:args.top_n]
                label = f"상위 {len(ranked)} (배치 순서까지 별개로 셈)"
            lines += ["", f"## 단일 덱 — {label} ({elapsed:.0f}초)"]
            for i, entry in enumerate(ranked, 1):
                lines += deck_lines(entry, i)

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
