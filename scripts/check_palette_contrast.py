"""Check RapiLab's palette against WCAG contrast thresholds.

Text needs 4.5:1; anything whose edge is what identifies a control needs 3:1.
Purely decorative dividers are exempt - they are listed with a threshold of 0
so the number stays visible without pretending to pass a bar it never had.

This exists because eyeballing a dark palette does not work. It caught two
defects while the monochrome-red identity was being designed: a border grey
that looked fine at 1.74:1, and white-on-red at 3.80:1.

The values below are the ones
docs/superpowers/specs/2026-08-06-monochrome-red-identity-design.md specifies.
Re-run it whenever one is tuned - `--border` in particular sits just above its
threshold, so small changes to it or to `--surface-2` break the floor.

Run:  python scripts/check_palette_contrast.py
"""


def srgb_to_lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    lo, hi = sorted((a, b))
    return (hi + 0.05) / (lo + 0.05)


GROUNDS = {"bg": "#0a0a0a", "surface": "#111111", "surface-2": "#1a1a1a"}

# (label, colour, needed ratio, what it is)
FOREGROUNDS = [
    ("text", "#f2f2f2", 4.5, "body text"),
    ("text-muted", "#9e9e9e", 4.5, "secondary text"),
    ("accent", "#ff2233", 4.5, "emphasis / error text"),
    # A decorative divider is not what identifies a control, so it is exempt
    # from the 3:1 floor. Listed to keep the number honest, not to pass.
    ("rule", "#2e2e2e", 0.0, "decorative divider (exempt)"),
    ("border", "#666666", 3.0, "component edge"),
    ("border-strong", "#8a8a8a", 3.0, "emphasised edge"),
    ("star", "#ffc93c", 4.5, "breakthrough stars (game data)"),
    ("favorite", "#ff8a3d", 4.5, "favourite-item heart (game data)"),
]


def main():
    width = max(len(name) for name, *_ in FOREGROUNDS) + 2
    header = f"{'':{width}}" + "".join(f"{g:>12}" for g in GROUNDS)
    print(header)
    print("-" * len(header))
    for name, colour, need, what in FOREGROUNDS:
        cells = ""
        for ground in GROUNDS.values():
            r = ratio(colour, ground)
            mark = "ok" if r >= need else "LOW"
            cells += f"{r:>8.2f} {mark:<3}"
        print(f"{name:{width}}{cells}  (needs {need}) - {what}")

    print("\nGrounds are barely separated by design - the borders carry depth:")
    names = list(GROUNDS)
    for i in range(len(names) - 1):
        a, b = GROUNDS[names[i]], GROUNDS[names[i + 1]]
        print(f"  {names[i]} vs {names[i+1]}: {ratio(a, b):.2f}")

    # Two surfaces are filled rather than outlined: the primary button (white)
    # and the pressed draft-slot lock (red). Whatever sits on them needs to clear
    # 4.5:1 too.
    print("\nText on filled surfaces:")
    for fg, bg, what in [
        ("#0a0a0a", "#f2f2f2", "on the primary button"),
        ("#ffffff", "#ff2233", "white on red"),
        ("#0a0a0a", "#ff2233", "near-black on red"),
    ]:
        r = ratio(fg, bg)
        print(f"  {fg} on {bg}: {r:>6.2f} {'ok' if r >= 4.5 else 'LOW'}  - {what}")

    # In this direction the borders ARE the structure, so the one on controls has
    # to clear 3:1 against the lightest ground it ever sits on.
    worst = max(GROUNDS.values(), key=luminance)
    for target, label in ((3.0, "component edge"), (4.5, "emphasised edge")):
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
