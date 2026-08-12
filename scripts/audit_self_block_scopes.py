"""「■ Affects self」 블록의 값이 아군에게도 지급되고 있지 않은지, 슬롯마다 실제로

흔들어 보고 확인한다.

WHY: 스코프는 값 검증이 절대 못 잡는다. 같은 스탯, 같은 숫자, 받는 사람만 다르기
때문에 슬롯 매핑 테스트도 픽스처도 전체 스위트도 전부 통과한다. 그레이브의 Plot
Spoiler가 그렇게 지냈다 - 원문이

    ■ Affects self.        Pierce 속성 / Pierce Damage / Critical Rate
    ■ Affects all allies.  Attack Damage / Pierce Damage / Max Ammo +3발

로 갈리는데 Critical Rate가 `squad`로 걸려 있었고, 그것이 그 불릿의 최대값이라
(버스트 lv1에 이미 +53.24%) 엔진 기본 크리율 15%를 덱 전원에게 68%로 올렸다.
실덱 한 판에서 덱 총딜 15%였다.

기존 `audit_target_scopes.py`는 이것을 구조적으로 못 잡는다: 그것은 좁은 타게팅
*문구*를 나열할 뿐 어느 효과가 어느 블록 소속인지 모르고, self 스코프를 하나라도
내보내는 모듈은 통과시킨다(그레이브는 Pierce 덕에 통과했다).

HOW: 문구를 읽어 판정하지 않는다 - 슬롯 값을 하나씩 바꿔 넣고 규칙을 실제로
발사해서, **아군의 총합이 따라 움직이는지**를 본다. 움직이면 그 슬롯은 아군에게
지급되는 것이고, 그 슬롯이 원문의 self 블록에 있으면 불일치다. 이 방식은
`drop_tokens`로 슬롯 번호가 재매핑된 유닛에서도 성립한다 - 조립된 값에 손을
대므로 인코딩이 보는 번호를 그대로 쓴다.

한계 (읽고 판단할 것):
  - 조건이 걸린 규칙은 이 합성 컨텍스트에서 발동하지 않을 수 있고, 그러면 그
    슬롯은 관측되지 않는다(`관측 안 됨`으로 표시). 없다는 뜻이 아니다.
  - `_BUILDERS`가 내는 규칙만 본다. per-shot / periodic / scheduled-nuke 빌더는
    범위 밖이다.
  - 「self and 2 allies on both sides」 같은 위치 기반 타게팅은 squad 근사가
    정당하다고 문서화돼 있으므로(references/engine-capabilities.md) 불일치로
    세지 않고 참고로만 적는다.

WHEN TO RUN: 니케를 인코딩한 뒤, 스코프를 건드린 뒤, 새 데이터를 수집한 뒤.

불일치가 하나라도 있으면 exit 1.

    python scripts/audit_self_block_scopes.py
    python scripts/audit_self_block_scopes.py --slug grave   # 하나만
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.effects import EffectRegistry
from app.skill_rules import registry as skill_registry
from app.skill_values import (DATA_DIR, _NUMBER, load_character_data,
                              load_weapon_data, assemble_skill_values)
from app.user_roster import _weapon_stats
from app.squad_engine import SquadContext, SquadMember, fire_trigger
from app.supported_units import supported_units

# 대상을 선언하는 자리는 두 층이다: `■`로 시작하는 블록 머리말과, 그 블록 안에서
# 다시 대상을 바꾸는 `Affects ...:` 라벨(타키나의 "Affects targets hit:" 처럼).
# 안쪽 라벨을 안 보면 시전자 블록 안의 적 디버프를 시전자 한정으로 잘못 읽는다.
BLOCK_HEAD = re.compile(r"■\s*([^\n<]*)|^\s*(Affects [^:\n]+):", re.MULTILINE)
PLACEHOLDER = re.compile(r"\{description_value_(\d+)\}")
# 이 블록의 값은 시전자에게만 간다. 뒤에 다른 말이 붙은 머리말("Affects self and
# 2 allies...")은 시전자 한정이 아니므로 정확히 이것만 본다.
SELF_ONLY = re.compile(r"^affects self\.?$", re.IGNORECASE)

ALLY = "__audit_ally__"
LEVELS = {"skill1": 10, "skill2": 10, "burst": 10}
# 시전자 스탯은 조립 계층이 넣어 주는 것이라 여기서 직접 채운다. 값 자체는
# 아무래도 좋다 - 흔들리는지만 보기 때문이다.
CASTER_STATS = {"caster_atk": 100000.0, "caster_def": 20000.0,
                "caster_max_hp": 1000000.0}


def _blocks_of(text):
    """[(머리말, 시작위치, 끝위치)] - 블록이 없으면 통째로 하나."""
    marks = list(BLOCK_HEAD.finditer(text))
    if not marks:
        return [("", 0, len(text))]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        head = (m.group(1) or m.group(2) or "").strip()
        out.append((head, m.end(), end))
    return out


def _block_at(blocks, position):
    for head, start, end in blocks:
        if start <= position < end:
            return head
    return ""


def slot_blocks(slug, manifest, key, index):
    """인코딩 슬롯 번호 -> 그 값이 적힌 블록의 머리말.

    dotgg/shiftypad는 설명문의 `{description_value_NN}` 자리가 토큰이고,
    lootandwaifus는 레벨 텍스트에 박힌 숫자 자체가 토큰이다. 어느 쪽이든
    `drop_tokens`를 먼저 걷어낸 뒤 1부터 다시 번호를 매기는 규칙은 같다
    (app/skill_values.py).
    """
    source = manifest["source"]
    array, idx = manifest["keys"][key]
    data = load_character_data(source, manifest.get("data_slug", slug), DATA_DIR)
    skill = data[array][idx]
    dropped = set(manifest.get("drop_tokens", {}).get(key, ()))

    if source in ("dotgg", "shiftypad"):
        text = skill.get("description") or ""
        blocks = _blocks_of(text)
        # 설명문에 나오는 순서가 곧 토큰 순서다. 빈 슬롯은 조립에서 빠지므로
        # 여기서도 뺀다.
        level_dict = skill["levels"][LEVELS["skill1"] - 1]
        nonempty = {k for k, v in level_dict.items() if v != ""}
        positions = [(m.start(), f"description_value_{int(m.group(1)):02d}")
                     for m in PLACEHOLDER.finditer(text)]
        positions = [(p, k) for p, k in positions if k in nonempty]
        if not dropped:
            # 네이티브 키가 그대로 살아 있다.
            return {k: _block_at(blocks, p) for p, k in positions}
        kept = [(p, k) for i, (p, k) in enumerate(positions) if i not in dropped]
        return {f"description_value_{i + 1:02d}": _block_at(blocks, p)
                for i, (p, k) in enumerate(kept)}

    text = skill["levels"][LEVELS["skill1"] - 1]
    blocks = _blocks_of(text)
    positions = [m.start() for m in _NUMBER.finditer(text)]
    kept = [p for i, p in enumerate(positions) if i not in dropped]
    return {f"description_value_{i + 1:02d}": _block_at(blocks, p)
            for i, p in enumerate(kept)}


def observe(slug, values, tier, element):
    """규칙을 발사해 (스탯 -> (시전자 총합, 아군 총합))을 관측."""
    built = skill_registry._BUILDERS[slug](values)
    rules = built[0] if isinstance(built, tuple) else built
    context = SquadContext([
        SquadMember(slug, burst_tier=tier, element=element),
        SquadMember(ALLY, burst_tier=3 if tier != 3 else 1, element="Fire"),
    ])
    reg = EffectRegistry()
    for trigger in sorted({rule.trigger for rule in rules}):
        fire_trigger(trigger, {slug: rules}, context, reg, time=1.0)
    stats = {effect.stat for effect, _ in reg._entries}
    caster = {"slug": slug, "element": element}
    ally = {"slug": ALLY, "element": "Fire"}
    return {stat: (reg.total_for(stat, caster, now=1.0),
                   reg.total_for(stat, ally, now=1.0))
            for stat in stats}


def audit_slug(slug, meta):
    """이 슬러그의 불일치 목록과 관측 못 한 슬롯 목록."""
    manifest = skill_registry.get_skill_value_manifest(slug)
    if manifest is None:
        return [], [], "매니페스트 없음"
    try:
        base_values = assemble_skill_values(slug, manifest, LEVELS)
    except (KeyError, IndexError, FileNotFoundError) as exc:
        return [], [], f"값 조립 실패: {exc!r}"
    for key in base_values:
        base_values[key] = dict(base_values[key])
    # 무기 스탯을 읽는 빌더가 있다(차지시간에서 등가 버프를 유도하는 쪽). 스텁을
    # 세우면 그 유도가 거짓이 되므로 진짜 무기 데이터를 조립 계층과 같은 방식으로
    # 넣는다.
    extra = dict(CASTER_STATS)
    try:
        weapon = _weapon_stats(load_weapon_data(manifest, slug, DATA_DIR))
        if weapon is not None:
            extra["caster_weapon_stats"] = weapon
    except (FileNotFoundError, KeyError, ValueError):
        pass
    values = {**base_values, **extra}
    try:
        base = observe(slug, values, meta["burst_tier"], meta["element"])
    except Exception as exc:  # 빌더가 이 합성 컨텍스트를 못 견디는 경우
        return [], [], f"규칙 발사 실패: {type(exc).__name__}: {exc}"

    mismatches, unobserved = [], []
    for key in base_values:
        try:
            blocks = slot_blocks(slug, manifest, key, None)
        except (KeyError, IndexError, FileNotFoundError, TypeError) as exc:
            unobserved.append((key, "*", f"블록 파싱 실패: {exc!r}"))
            continue
        for slot, head in blocks.items():
            if not SELF_ONLY.match(head or ""):
                continue
            if slot not in base_values[key]:
                continue
            shaken = {k: dict(v) for k, v in base_values.items()}
            try:
                original = float(shaken[key][slot])
            except ValueError:
                continue
            shaken[key][slot] = str(original * 2 + 1)
            try:
                after = observe(slug, {**shaken, **extra},
                                meta["burst_tier"], meta["element"])
            except Exception as exc:
                unobserved.append((key, slot, f"{type(exc).__name__}: {exc}"))
                continue
            moved_ally = [
                stat for stat in set(base) | set(after)
                if base.get(stat, (0.0, 0.0))[1] != after.get(stat, (0.0, 0.0))[1]
            ]
            moved_self = [
                stat for stat in set(base) | set(after)
                if base.get(stat, (0.0, 0.0))[0] != after.get(stat, (0.0, 0.0))[0]
            ]
            if moved_ally:
                mismatches.append((key, slot, original, sorted(moved_ally)))
            elif not moved_self:
                unobserved.append((key, slot, "이 컨텍스트에서 아무 효과도 안 냈다"))
    return mismatches, unobserved, None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", help="이 슬러그 하나만 본다")
    parser.add_argument("--verbose", action="store_true",
                        help="관측 못 한 슬롯과 건너뛴 슬러그도 전부 출력")
    args = parser.parse_args()

    by_slug = {u["slug"]: u for u in supported_units()}
    slugs = [args.slug] if args.slug else sorted(skill_registry.ENCODED_SLUGS)

    total_mismatch, skipped, unobserved_count = [], [], 0
    for slug in slugs:
        meta = by_slug.get(slug)
        if meta is None:
            skipped.append((slug, "supported_units에 없다"))
            continue
        mismatches, unobserved, why = audit_slug(slug, meta)
        if why:
            skipped.append((slug, why))
            continue
        unobserved_count += len(unobserved)
        if mismatches:
            total_mismatch.append((slug, mismatches))
        if args.verbose and unobserved:
            print(f"[관측 안 됨] {slug}")
            for key, slot, why in unobserved:
                print(f"    {key}.{slot}: {why}")

    print(f"\n검사한 슬러그 {len(slugs) - len(skipped)}개 "
          f"(건너뜀 {len(skipped)}, 관측 안 된 self 슬롯 {unobserved_count})")

    if not total_mismatch:
        print("「Affects self」 블록의 값이 아군에게 새는 곳은 없다.")
    else:
        print(f"\n=== 불일치 {sum(len(m) for _, m in total_mismatch)}건 ===")
        print("원문이 시전자 한정이라고 적은 값인데 아군의 총합이 따라 움직인다.\n")
        for slug, mismatches in total_mismatch:
            print(f"{slug}")
            for key, slot, value, stats in mismatches:
                print(f"    {key}.{slot} (={value}) -> 아군이 받는 스탯: {', '.join(stats)}")
            print()

    if args.verbose and skipped:
        print("=== 건너뛴 슬러그 ===")
        for slug, why in skipped:
            print(f"  {slug}: {why}")

    return 1 if total_mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
