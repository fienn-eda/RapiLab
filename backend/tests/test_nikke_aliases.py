"""프론트 별명 표(nikkeAliases.ts)가 화면에 뜨는 슬러그와 어긋나지 않게 잡는다.

별명 표는 손으로 채우는 파일이고, 어긋나도 화면에는 아무 표시가 나지 않는다 -
키가 낡으면 그 별명이 조용히 아무것도 안 맞히고, 줄이 빠지면 그 니케만 별명
검색이 안 된다. 그래서 새 니케를 인코딩할 때 이 파일에 줄을 추가하는 일을
사람의 기억이 아니라 이 테스트가 강제한다(nikke-skill-encoding 스킬의 마무리
단계도 같은 것을 말한다).

기준이 ENCODED_SLUGS가 아니라 `supported_units()`인 이유: 유저가 팔레트에서
보는 것이 그 목록이고, 별명은 그 목록에서 니케를 찾자고 있는 것이다. 모드
변형의 base(브래디·신데렐라: 크리스탈 웨이브·디젤: 윈터 스위츠)는 자신은
인코딩되지 않았지만 화면에는 뜬다.
"""
import re
from pathlib import Path

from app.skill_rules.registry import MODE_VARIANTS
from app.supported_units import supported_units

ALIAS_FILE = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "src" / "lib" / "nikkeAliases.ts"
)

TABLE_START = "export const NIKKE_ALIASES: Record<string, readonly string[]> = {"


def _alias_keys() -> set[str]:
    """표에 적힌 슬러그들. 이 테스트는 파일의 literal 텍스트를 파싱하므로,
    선언 줄이 바뀌면 조용히 빈 집합이 되지 않고 여기서 크게 실패한다."""
    text = ALIAS_FILE.read_text(encoding="utf-8")
    assert TABLE_START in text, (
        f"{ALIAS_FILE}에서 {TABLE_START!r}를 찾지 못했다 - 선언이 바뀌었다면 "
        "이 마커도 같이 고쳐야 한다."
    )
    body = text.split(TABLE_START, 1)[1].split("\n}", 1)[0]
    return set(re.findall(r"^\s*'([a-z0-9-]+)':", body, re.M))


def test_the_alias_table_lists_exactly_the_units_on_screen():
    keys = _alias_keys()
    on_screen = {unit["slug"] for unit in supported_units()}

    missing = sorted(on_screen - keys)
    stale = sorted(keys - on_screen)

    assert not missing, (
        f"별명 표에 줄이 없는 니케: {missing}. 새로 인코딩했다면 "
        f"{ALIAS_FILE.name}에 `'슬러그': [],  // 한글 이름` 줄을 추가할 것 - "
        "별명은 나중에 채워도 되지만 줄이 없으면 채울 자리도 없다."
    )
    assert not stale, (
        f"화면에 없는 슬러그가 별명 표에 남아 있다: {stale}. 오타이거나, "
        "인코딩이 빠지면서 낡은 줄이다."
    )


def test_the_table_is_parsed_at_all():
    """위 단언은 양쪽이 다 비어도 통과한다 - 파싱이 죽지 않았음을 따로 고정한다."""
    assert len(_alias_keys()) > 50


def _alias_rows() -> list[tuple[str, list[str]]]:
    """(슬러그, 별명들). 빈 배열도 그대로 돌려준다."""
    text = ALIAS_FILE.read_text(encoding="utf-8")
    body = text.split(TABLE_START, 1)[1].split("\n}", 1)[0]
    rows = []
    for slug, inside in re.findall(r"^\s*'([a-z0-9-]+)':\s*\[(.*?)\],", body, re.M):
        rows.append((slug, re.findall(r"'([^']+)'", inside)))
    return rows


def _family(slug: str) -> str:
    """이 슬러그가 가리키는 '같은 니케'의 대표.

    애장품 변형(`-signature`)과 모드 변형(MODE_VARIANTS)은 한 니케의 다른
    빌드다 - 유저가 부르는 이름도 당연히 같으므로, 별명이 겹치는 것은 충돌이
    아니라 정상이다(브래디 셋이 다 「빵순이」인 것처럼).
    """
    base = slug.removesuffix("-signature")
    for parent, variants in MODE_VARIANTS.items():
        if base == parent or base in variants:
            return parent
    return base


def test_an_alias_never_points_at_two_different_nikkes():
    """한 별명이 서로 다른 니케를 가리키면 검색이 아무것도 좁히지 못한다.

    별명은 그 하나를 부르려고 쓰는 말이라, 둘이 나오면 표가 틀린 것이다.
    """
    owner: dict[str, tuple[str, str]] = {}
    clashes = []
    for slug, aliases in _alias_rows():
        for alias in aliases:
            family = _family(slug)
            if alias in owner and owner[alias][0] != family:
                clashes.append(f"{alias}: {owner[alias][1]} vs {slug}")
            else:
                owner.setdefault(alias, (family, slug))

    assert not clashes, f"한 별명이 다른 니케를 가리킨다: {clashes}"


def test_that_check_would_notice_a_real_clash():
    """위 단언은 같은 니케의 변형을 눈감아 준다 - 그 관대함이 아무것이나
    통과시키는 수준이 아님을 고정한다."""
    assert _family("moran-signature") == _family("moran")
    assert _family("bready-lingering") == _family("bready")
    assert _family("moran") != _family("bready")
