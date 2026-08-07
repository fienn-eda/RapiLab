"""명중률 불릿을 가진 슬러그는 그 명중률을 실제로 내보내야 한다.

`hit_rate`는 2026-08-07에 소비자를 얻었지만(`accuracy.core_hit_rate`), 그날
**어느 skill_rules 모듈도 그 스탯을 등록하지 않고 있었다** - 15개 슬러그가 전부
docstring에 「Hit Rate는 엔진이 안 읽는다」고 적어 둔 채였다. 「엔진 능력이
풀렸다」와 「그 능력을 쓰는 유닛이 있다」는 다른 사실이고, 스위트는 그 차이를
못 봤다. 이 대조가 그 자리를 메운다: 데이터에 `Hit Rate ▲/▼` 줄이 있는데 그
슬러그를 만드는 모듈이 `hit_rate`를 한 번도 안 쓰면 여기서 빨개진다.

**슬러그 단위**의 대조다 - 한 유닛의 명중 불릿이 둘인데 하나만 인코딩해도 통과한다
(도로시: 세렌디피티가 실제로 그렇다). 불릿 단위까지 세려면 원문 파싱이 인코딩
자체와 같은 판단을 해야 하므로, 여기서는 「통째로 빠진 유닛」만 잡고 부분 보류는
각 모듈 docstring의 몫으로 둔다.
"""
import importlib
import inspect
import pkgutil

import pytest

import app.skill_rules as _skill_rules_package
from app.skill_rules.provider_scan import hit_rate_bullet_slugs, unreadable_slugs


def _modules_by_slug():
    """slug -> the module that declares it, via its colocated
    SKILL_VALUE_MANIFESTS (the same walk registry.get_skill_value_manifest
    does)."""
    owners = {}
    for info in pkgutil.iter_modules(_skill_rules_package.__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"app.skill_rules.{info.name}")
        for slug in getattr(module, "SKILL_VALUE_MANIFESTS", {}):
            owners[slug] = module
    return owners


# Slugs whose Hit Rate is deliberately not emitted, each with the reason. Empty
# today: every collected Hit Rate bullet reached an encoding on 2026-08-07.
# Growing this set is a decision to record, not a way to quiet the test.
KNOWN_UNENCODED_HIT_RATE = {}


@pytest.fixture(scope="module")
def owners():
    return _modules_by_slug()


def test_every_slug_with_a_hit_rate_bullet_emits_the_stat(owners):
    unreadable = unreadable_slugs()
    missing = []
    for slug in sorted(hit_rate_bullet_slugs() - unreadable):
        if slug in KNOWN_UNENCODED_HIT_RATE:
            continue
        module = owners.get(slug)
        if module is None:
            continue  # no manifest = not loadable from user data anyway
        if '"hit_rate"' not in inspect.getsource(module):
            missing.append((slug, module.__name__))
    assert not missing, (
        "these units have a Hit Rate bullet in the collected data but their "
        f"module never registers the stat: {missing}"
    )


def test_the_scan_finds_the_units_we_know_carry_hit_rate():
    """A scan that quietly matched nothing would make the test above vacuous."""
    found = hit_rate_bullet_slugs()
    for slug in ("jill-valentine", "dorothy-serendipity", "mast-romantic-maid",
                 "quency-escape-queen", "modernia"):
        assert slug in found, slug


def test_known_unencoded_entries_still_have_a_hit_rate_bullet():
    """A reason recorded for a unit that no longer has such a bullet is stale."""
    stale = set(KNOWN_UNENCODED_HIT_RATE) - hit_rate_bullet_slugs()
    assert not stale, f"no Hit Rate bullet in the data any more: {sorted(stale)}"
