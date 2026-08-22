"""Check RapiLab's palette against WCAG contrast thresholds.

Text needs 4.5:1; anything whose edge is what identifies a control needs 3:1.
Purely decorative dividers are exempt - they are listed with a threshold of 0
so the number stays visible without pretending to pass a bar it never had.

This exists because eyeballing a dark palette does not work. It caught two
defects while the monochrome-red identity was being designed: a border grey
that looked fine at 1.53:1 against --surface-2, and white-on-red at 3.80:1.

The values are read from frontend/src/index.css's :root block at run time, so
this always checks the palette as it currently stands, not a copy of it. If a
token below is renamed or removed there, this script fails loudly instead of
quietly grading against a stale number. Re-run it whenever a token is tuned -
`--border` in particular sits just above its threshold, so small changes to
it or to `--surface-2` break the floor.

Run:  python scripts/check_palette_contrast.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_CSS = REPO_ROOT / "frontend" / "src" / "index.css"


def srgb_to_lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_rgb(colour):
    """Accept a '#rrggbb' string or an (r, g, b) tuple, return the tuple."""
    if isinstance(colour, str):
        h = colour.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    return colour


def to_hex(rgb):
    return "#" + "".join(f"{round(c):02x}" for c in rgb)


def luminance(colour):
    r, g, b = to_rgb(colour)
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    lo, hi = sorted((a, b))
    return (hi + 0.05) / (lo + 0.05)


def blend(fg_rgb, alpha, bg_rgb):
    """Alpha-composite a translucent colour over an opaque ground, in sRGB space.

    Rounds to the whole-number channel values the rendered pixel actually has,
    since that is the colour a contrast ratio is ever judged against.
    """
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg_rgb, bg_rgb))


def parse_rgba(value):
    match = re.match(
        r"rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)",
        value.strip(),
    )
    if not match:
        print(f"error: could not parse rgba() value: {value!r}", file=sys.stderr)
        sys.exit(1)
    r, g, b, a = (float(x) for x in match.groups())
    return (r, g, b), a


GROUND_TOKENS = {"bg": "bg", "surface": "surface", "surface-2": "surface-2"}

# (label, token name in :root, needed ratio, what it is)
FOREGROUNDS = [
    ("text", "text", 4.5, "body text"),
    ("text-muted", "text-muted", 4.5, "secondary text"),
    ("accent", "accent", 4.5, "emphasis / error text"),
    # A decorative divider is not what identifies a control, so it is exempt
    # from the 3:1 floor. Listed to keep the number honest, not to pass.
    ("rule", "rule", 0.0, "decorative divider (exempt)"),
    ("border", "border", 3.0, "component edge"),
    ("border-strong", "border-strong", 3.0, "emphasised edge"),
    ("star", "star", 4.5, "breakthrough stars (game data)"),
    ("favorite", "favorite-item", 4.5, "favourite-item heart (game data)"),
]

# Filled surfaces referenced directly, beyond GROUND_TOKENS/FOREGROUNDS above.
FILLED_SURFACE_TOKENS = [
    "primary",
    "primary-contrast",
    "accent",
    "accent-contrast",
    "accent-soft",
    "accent-on-light",
    # 상자를 걷은 뒤 버튼이 서는 바닥. 반투명이라 얹히는 곳마다 값이 달라지므로
    # accent-soft와 같이 바닥별로 합성해서 잰다.
    "raised",
    "raised-hover",
]


def required_tokens():
    names = set(GROUND_TOKENS.values())
    names.update(token for _, token, _, _ in FOREGROUNDS)
    names.update(FILLED_SURFACE_TOKENS)
    return sorted(names)


def load_tokens(required):
    """Parse the :root block's custom properties out of index.css, by name.

    Fails loudly instead of falling back to a stale copy of the palette: if a
    token this script depends on has been renamed or removed, that is exactly
    the change this check exists to catch, so it must not print "ok" anyway.
    """
    if not INDEX_CSS.is_file():
        print(f"error: {INDEX_CSS} not found", file=sys.stderr)
        sys.exit(1)
    text = INDEX_CSS.read_text(encoding="utf-8")
    match = re.search(r":root\s*\{(.*?)\}", text, re.S)
    if not match:
        print(f"error: no :root block found in {INDEX_CSS}", file=sys.stderr)
        sys.exit(1)
    found = dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", match.group(1)))
    missing = [name for name in required if name not in found]
    if missing:
        print(
            f"error: {INDEX_CSS} no longer defines: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return {name: found[name].strip() for name in required}


def main():
    tokens = load_tokens(required_tokens())
    grounds = {label: tokens[name] for label, name in GROUND_TOKENS.items()}

    width = max(len(name) for name, *_ in FOREGROUNDS) + 2
    header = f"{'':{width}}" + "".join(f"{g:>12}" for g in grounds)
    print(header)
    print("-" * len(header))
    for name, token_name, need, what in FOREGROUNDS:
        colour = tokens[token_name]
        cells = ""
        for ground in grounds.values():
            r = ratio(colour, ground)
            mark = "ok" if r >= need else "LOW"
            cells += f"{r:>8.2f} {mark:<3}"
        print(f"{name:{width}}{cells}  (needs {need}) - {what}")

    # 2026-08-22까지는 여기에 "the borders carry depth"라고 적혀 있었다. 이제는
    # 반대다 - 채움이 구조를 지고 상자는 걷혔다. 그런데 이 단들은 여전히 좁고,
    # 좁은 것이 게으름이 아니라 아래 두 하한 때문이다: --surface-2를 한 칸만
    # 올려도 accent가 4.5를, --border가 3.0을 잃는다. 그래서 분리는 단을 벌려서가
    # 아니라 탭 패널이 채움을 놓아 그 위의 것들이 떠오르게 해서 얻는다.
    print("\nGrounds are close by necessity - see index.css for why they cannot open up:")
    names = list(grounds)
    for i in range(len(names) - 1):
        a, b = grounds[names[i]], grounds[names[i + 1]]
        print(f"  {names[i]} vs {names[i+1]}: {ratio(a, b):.2f}")

    # Three surfaces are filled rather than outlined: the primary button (white),
    # the pressed draft-slot lock (red), and the roster tab's top-roll gear row,
    # which flips to --primary. Whatever sits on them needs to clear 4.5:1 too -
    # including translucent fills, composited over the ground they are painted on
    # before the ratio is taken.
    #
    # The gear row is why --accent-on-light exists: plain --accent measures 3.39
    # there and fails, which nobody noticed until the row was drawn (2026-08-15).
    # It is listed so the next palette change re-checks it instead of trusting
    # that one hand calculation.
    print("\nText on filled surfaces:")
    filled = [
        (tokens["primary-contrast"], tokens["primary"], "on the primary button"),
        (tokens["accent-contrast"], tokens["accent"], "near-black on red"),
        (tokens["accent-on-light"], tokens["primary"],
         "top-roll value on the flipped gear row"),
    ]
    accent_soft_rgb, accent_soft_alpha = parse_rgba(tokens["accent-soft"])
    for ground_label, ground_hex in grounds.items():
        composite = blend(accent_soft_rgb, accent_soft_alpha, to_rgb(ground_hex))
        what = f"accent on accent-soft, over --{ground_label}"
        filled.append((tokens["accent"], composite, what))

    # 버튼 라벨이 앉는 바닥. --raised는 어느 면 위에도 얹힐 수 있으므로 세 바닥
    # 전부에서 재고, 라벨로 실제 쓰이는 두 색을 본다. 여기가 LOW로 떨어지면
    # 오버레이 알파를 올릴 것이 아니라 라벨 색을 --text로 올려야 한다 -
    # 바닥을 밝히면 그 위의 --border가 3:1을 잃는다.
    for label_token in ("text", "text-muted"):
        for raised_token in ("raised", "raised-hover"):
            raised_rgb, raised_alpha = parse_rgba(tokens[raised_token])
            for ground_label, ground_hex in grounds.items():
                composite = blend(raised_rgb, raised_alpha, to_rgb(ground_hex))
                what = f"{label_token} on {raised_token}, over --{ground_label}"
                filled.append((tokens[label_token], composite, what))

    for fg, bg, what in filled:
        r = ratio(fg, bg)
        fg_label = fg if isinstance(fg, str) else to_hex(fg)
        bg_label = bg if isinstance(bg, str) else to_hex(bg)
        mark = "ok" if r >= 4.5 else "LOW"
        print(f"  {fg_label} on {bg_label}: {r:>6.2f} {mark}  - {what}")

    # 상자는 걷혔지만 컨트롤의 가장자리는 남는다 - 사람이 값을 치거나 고르는
    # 칸은 테두리가 곧 「여기가 컨트롤이다」라서, 채움만으로는 3:1을 못 만든다
    # (--surface-2 위의 --raised는 1.18이다). 그 선은 여전히 가장 밝은 바닥에서
    # 3:1을 넘어야 한다.
    worst = max(grounds.values(), key=luminance)
    for target, label in ((3.0, "component edge"), (3.0, "emphasised edge")):
        grey = next(
            g for g in range(256) if ratio(f"#{g:02x}{g:02x}{g:02x}", worst) >= target
        )
        print(
            f"\nLightest ground is {worst}; a neutral grey needs "
            f"#{grey:02x}{grey:02x}{grey:02x} or lighter-still to reach "
            f"{target}:1 ({label})."
        )


if __name__ == "__main__":
    main()
