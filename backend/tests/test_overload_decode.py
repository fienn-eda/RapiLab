from app.overload_decode import decode_option


def test_decode_option_splits_type_and_level():
    # 700 TT LL: measured on ShiftyPad gear (probe 2026-07-19).
    assert decode_option(7000811) == (8, 11)   # type 8, level 11
    assert decode_option(7001002) == (10, 2)   # type 10, level 2
    assert decode_option(7000905) == (9, 5)


def test_decode_option_empty_slot_is_none():
    assert decode_option(0) is None


def test_decode_option_rejects_a_non_overload_id():
    # Anything not 700-prefixed and 7 digits is not an overload option.
    assert decode_option(3111001) is None   # an equip tid
    assert decode_option(123) is None
