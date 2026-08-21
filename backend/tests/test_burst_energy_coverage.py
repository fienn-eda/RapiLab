"""인코딩된 유닛 전부가 발당 게이지 에너지를 갖는가.

이 가드가 없으면 `burstGen` 없는 무기 파일 하나가 그 유닛을 추천에서 통째로
지우는데, 제외는 에러가 아니라 보고라 스위트가 초록인 채로 지나간다.
`test_hit_rate_bullets_are_encoded.py`와 같은 계열이다.
"""
from app.skill_rules.registry import ENCODED_SLUGS
from app.skill_values import load_weapon_data
from app.skill_rules.registry import BURST_ENERGY_FALLBACK, get_skill_value_manifest


def test_every_encoded_slug_has_burst_gauge_energy():
    missing = []
    for slug in sorted(ENCODED_SLUGS):
        manifest = get_skill_value_manifest(slug)
        if manifest is None:
            continue
        try:
            weapon = load_weapon_data(manifest, slug)
        except FileNotFoundError:
            continue          # 무기 파일 자체가 없는 유닛은 이미 제외 대상이다
        if weapon.get("burstGen") is None and slug not in BURST_ENERGY_FALLBACK:
            missing.append(slug)
    assert missing == [], (
        f"게이지 에너지가 없는 인코딩 유닛: {missing}. "
        f"registry.BURST_ENERGY_FALLBACK에 원본 값을 적거나 무기 파일을 다시 뽑아라.")
