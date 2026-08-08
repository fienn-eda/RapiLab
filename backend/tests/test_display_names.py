"""The Korean display-name table (`app/display_names.py`) and how
`supported_units()` prefers it.

The table is hand-authored and allowed to be incomplete for units the engine does
not support - an unfilled slug falls back to the source data's English name, so
filling it is incremental and never a regression. Coverage is required only of the
ENCODED slugs: those are the ones the deck builder puts on screen, and a committed
snapshot carries the official Korean name for each, so leaving one in English is an
oversight rather than work not yet done.
"""
import json

import app.supported_units as su
from app.display_names import DISPLAY_NAMES
from app.skill_rules.registry import ENCODED_SLUGS, MODE_VARIANTS
from app.supported_units import supported_units
from tests.test_resource_id_directory import SNAPSHOT, _mapped_entries


def test_every_table_key_is_a_slug_the_catalog_lists():
    """A typo'd key is silently dead weight - it would never match a slug, so
    the name it carries would never show and nobody would notice."""
    listed = {u["slug"] for u in supported_units()}
    strangers = sorted(set(DISPLAY_NAMES) - listed)
    assert not strangers, f"display names for slugs the catalog does not list: {strangers}"


def test_a_characters_mode_candidates_are_named_apart():
    """A character the engine fans into several candidates has them ALL in the
    roster at once - measured: every MODE_VARIANTS base does - so two of them
    can land on the bench together. That is the "Bready, Bready" this table
    exists to end, and only distinct names end it."""
    for base, variants in MODE_VARIANTS.items():
        named = [(v, DISPLAY_NAMES.get(v)) for v in variants if DISPLAY_NAMES.get(v)]
        names = [n for _, n in named]
        assert len(names) == len(set(names)), \
            f"{base}'s candidates share a name: {named}"


def _owned_character(slug):
    """The one owned character a slug stands for - the mirror of the roster's
    own resolution. A MODE_VARIANTS candidate stands for its base, and a
    Favorite Item build stands for the unit that equips it."""
    for base, variants in MODE_VARIANTS.items():
        if slug in variants:
            return base
    return slug.removesuffix("-signature")


def test_two_different_characters_never_share_a_name():
    """Uniqueness is scoped to the character, NOT global. A base and its
    "-signature" build never appear together (the roster resolves to one or the
    other - measured: no roster holds both), so naming both '헬름' is right:
    the heart, not the name, says which build is in play. Two DIFFERENT
    characters sharing a name is still a typo worth catching."""
    by_name = {}
    for slug, name in DISPLAY_NAMES.items():
        if name:
            by_name.setdefault(name, []).append(slug)
    crossed = {
        name: slugs for name, slugs in by_name.items()
        if len({_owned_character(s) for s in slugs}) > 1
    }
    assert not crossed, f"one name across different characters: {crossed}"


def _official_name_by_slug() -> dict[str, str]:
    """한국 서버 공식 표기를 슬러그로 찾을 수 있게 뒤집은 것.

    이름은 `nikke-directory.json`의 `name_ko`에서 온다 — ShiftyPad가 로케일별로
    따로 서빙하는 캐릭터 목록을 그대로 받아 둔 것이라, 이 표를 채울 때 음차를
    유추할 필요가 없다(`tools/collect-blablalink/korean-names.js`).
    """
    if not SNAPSHOT.exists():
        return {}
    entries = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    by_id = {e["resource_id"]: e["name_ko"] for e in entries if e.get("name_ko")}
    return {
        slug: by_id[resource_id]
        for resource_id, slug in _mapped_entries().items()
        if resource_id in by_id
    }


def test_every_encoded_slug_is_named_in_korean():
    """인코딩된 슬러그는 곧 화면에 뜨는 유닛이다. 영문 폴백은 지원하지 않는 ~95기를
    위한 안전망이지 인코딩을 끝낸 유닛의 상태가 아니므로, 새 인코딩은 이 표에 한
    줄을 더할 때까지 끝난 것이 아니다."""
    official = _official_name_by_slug()
    unnamed = {
        slug: official.get(_owned_character(slug), "(스냅샷에 공식 표기 없음)")
        for slug in sorted(ENCODED_SLUGS)
        if not DISPLAY_NAMES.get(slug)
    }
    assert not unnamed, (
        "인코딩됐는데 한글 이름이 없는 슬러그 (슬러그: 한국 서버 공식 표기): "
        f"{unnamed}. 표기는 그대로 쓰되 구분자는 이 표의 관례인 ': '로 적고, "
        "모드 변형은 접미사로 서로 다르게 쓴다."
    )


def test_the_catalog_prefers_the_table_over_the_source_name(monkeypatch):
    monkeypatch.setattr(su, "DISPLAY_NAMES", {"crown": "크라운"})
    units = {u["slug"]: u for u in supported_units()}
    assert units["crown"]["name"] == "크라운"


def test_an_unfilled_entry_falls_back_to_the_source_name(monkeypatch):
    """An empty string is "not translated yet", not a name - filling the table
    one unit at a time must never blank a label."""
    monkeypatch.setattr(su, "DISPLAY_NAMES", {"crown": ""})
    units = {u["slug"]: u for u in supported_units()}
    assert units["crown"]["name"] == "Crown"


def test_a_mode_variant_takes_its_own_name_not_the_bases(monkeypatch):
    """The merged owned entry copies its first candidate's metadata, so a
    naive implementation would hand the base's name to the candidate too (or
    vice versa) and re-create the collision the table exists to remove."""
    monkeypatch.setattr(su, "DISPLAY_NAMES", {
        "bready": "브레디",
        "bready-lingering": "브레디 (잔류)",
        "bready-recommended": "브레디 (권장)",
    })
    units = {u["slug"]: u for u in supported_units()}
    assert units["bready"]["name"] == "브레디"
    assert units["bready-lingering"]["name"] == "브레디 (잔류)"
    assert units["bready-recommended"]["name"] == "브레디 (권장)"
