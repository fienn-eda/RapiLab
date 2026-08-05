"""Build the app's bundled web font from Naver's NanumSquare Neo variable font.

Why this script exists
----------------------
NanumSquare Neo's variable `wght` axis does not follow the CSS convention.
Measured against the family's own static masters (contour area of a cap "H" and
a Hangul syllable - this help prints through a cp949 console, so the syllable
is not spelled out here):

    visual weight   static usWeightClass   variable axis value
    Light           350                    100
    Regular         400                    300
    Bold            700                    500
    ExtraBold       800                    700
    Heavy           900                    900

A browser maps a CSS `font-weight` straight onto the `wght` axis, so shipping
the font as-is renders `font-weight: 400` body text at axis 400 - heavier than
the family's own Regular, nearly Bold - and `font-weight: 700` as ExtraBold.
The whole UI comes out too heavy.

This script rewrites the axis so CSS weights land on the weights they name:
it moves the font's default to the Regular master, relabels the user-facing
axis to 300..900, and installs an `avar` segment map carrying each CSS weight
to its intended visual weight. Weights in between interpolate smoothly, which
is what the app's 500/550/600/650 rules want.

Usage
-----
    python scripts/build_app_font.py                # build from the default source
    python scripts/build_app_font.py --source PATH  # build from another copy
    python scripts/build_app_font.py --check        # verify the built font, don't write

The output is committed, so this only needs re-running when the upstream font
is updated.

Licence: NanumSquare Neo is Naver's, under the SIL Open Font License (full text
in frontend/public/fonts/OFL.txt). Embedding and redistribution are permitted;
selling the font file by itself is not. The OFL reserves the name "Nanum" /
"나눔" for the original, so this build also renames the family to RapiLab Sans -
a Modified Version may not present a Reserved Font Name to its users. The
notice travels with the font in frontend/public/fonts/NOTICE.txt.
"""

import argparse
import os
import sys

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._f_v_a_r import NamedInstance
from fontTools.varLib import instancer

DEFAULT_SOURCE = os.path.join(
    os.path.expanduser("~"),
    "Documents",
    "Fonts",
    "NaverNanumSquareNeo",
    "NanumSquareNeo",
    "NanumSquareNeo-Variable.ttf",
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(
    REPO_ROOT, "frontend", "public", "fonts", "NanumSquareNeo-Variable.woff2"
)

# The visual weight each master carries, named the way CSS names it, paired with
# where that weight actually sits on the source font's axis. Measured, not
# assumed - see the module docstring.
WEIGHT_MAP = [
    # (css weight, source axis value, name)
    (300, 100, "Light"),
    (400, 300, "Regular"),
    (700, 500, "Bold"),
    (800, 700, "ExtraBold"),
    (900, 900, "Heavy"),
]

CSS_DEFAULT = 400  # which CSS weight is the font's default instance

# The OFL reserves "Nanum" / "나눔" for the upstream font, so a Modified Version
# must not present that name to users. nameID 0 (copyright) is deliberately
# absent here - it credits NAVER and Sandoll and is left untouched.
RENAMED_STRINGS = {
    1: "RapiLab Sans",  # Family
    4: "RapiLab Sans",  # Full name
    16: "RapiLab Sans",  # Typographic family
    6: "RapiLabSans-Regular",  # PostScript name
    3: "RapiLab Sans; derived from NanumSquare Neo",  # Unique ID
    21: "RapiLab Sans",  # WWSFamily - a family-name record OSes read, same as 1/4/16
}


def _normalize(value, lo, default, hi):
    """Map an axis value into OpenType's [-1, 0, 1] normalized space."""
    if value < default:
        return (value - default) / (default - lo)
    if value > default:
        return (value - default) / (hi - default)
    return 0.0


def _rename_family(font):
    """Replace the family-facing name records with RapiLab Sans.

    Iterates each nameID's existing platform/encoding/language records rather
    than writing a fixed (3, 1, 0x409) triple, so no stale Mac or Korean-locale
    record is left behind still reading "NanumSquare Neo" / "나눔스퀘어 네오".
    """
    name_table = font["name"]
    for name_id, value in RENAMED_STRINGS.items():
        triples = {
            (rec.platformID, rec.platEncID, rec.langID)
            for rec in name_table.names
            if rec.nameID == name_id
        }
        for platform_id, plat_enc_id, lang_id in triples:
            name_table.setName(value, name_id, platform_id, plat_enc_id, lang_id)


def build(source):
    """Return the retuned font, ready to save."""
    font = TTFont(source)

    # This font's STAT carries an AxisValue whose AxisIndex points past its
    # design-axis array, which makes the instancer raise. It gets rebuilt below.
    if "STAT" in font:
        del font["STAT"]

    design_default = dict((css, axis) for css, axis, _ in WEIGHT_MAP)[CSS_DEFAULT]
    axis = font["fvar"].axes[0]
    design_lo, design_hi = axis.minValue, axis.maxValue

    # Move the font's default to the Regular master. `avar` is required to hold
    # the default fixed (it must map 0 to 0), so the default has to be right
    # before the segment map can carry everything else.
    font = instancer.instantiateVariableFont(
        font, {"wght": (design_lo, design_default, design_hi)}, updateFontNames=False
    )

    css_lo = WEIGHT_MAP[0][0]
    css_hi = WEIGHT_MAP[-1][0]

    segments = {}
    for css_weight, design_value, _ in WEIGHT_MAP:
        from_norm = _normalize(css_weight, css_lo, CSS_DEFAULT, css_hi)
        to_norm = _normalize(design_value, design_lo, design_default, design_hi)
        segments[from_norm] = to_norm

    # Relabel the user-facing axis in CSS weights. Everything past this point
    # speaks CSS; `avar` does the translating.
    axis = font["fvar"].axes[0]
    axis.minValue, axis.defaultValue, axis.maxValue = css_lo, CSS_DEFAULT, css_hi

    avar = font.get("avar")
    if avar is None:
        from fontTools.ttLib import newTable

        avar = newTable("avar")
        avar.segments = {}
        font["avar"] = avar
    avar.segments["wght"] = segments

    # Named instances must sit inside the relabelled range, so they move too.
    # Their names were already right: 400 really is this family's Regular.
    name_to_id = {}
    for inst in font["fvar"].instances:
        name_to_id[font["name"].getDebugName(inst.subfamilyNameID)] = inst.subfamilyNameID
    instances = []
    for css_weight, _, label in WEIGHT_MAP:
        inst = NamedInstance()
        inst.subfamilyNameID = name_to_id[label]
        inst.coordinates = {"wght": css_weight}
        instances.append(inst)
    font["fvar"].instances = instances

    font["OS/2"].usWeightClass = CSS_DEFAULT

    buildStatTable(
        font,
        [
            {
                "tag": "wght",
                "name": "Weight",
                "values": [
                    {
                        "value": css_weight,
                        "name": label,
                        # The default weight is elided from composed style names.
                        "flags": 0x2 if css_weight == CSS_DEFAULT else 0,
                    }
                    for css_weight, _, label in WEIGHT_MAP
                ],
            }
        ],
    )

    _rename_family(font)

    font.flavor = "woff2"
    return font


def _ink(font, char="H"):
    """Filled area of a glyph, normalized to the em square - a weight proxy."""
    from fontTools.pens.areaPen import AreaPen

    glyphs = font.getGlyphSet()
    pen = AreaPen(glyphs)
    glyphs[font.getBestCmap()[ord(char)]].draw(pen)
    return abs(pen.value) / (font["head"].unitsPerEm ** 2)


def _instance_ink(path, weight, drop_stat=False):
    font = TTFont(path)
    if drop_stat and "STAT" in font:
        del font["STAT"]
    return _ink(instancer.instantiateVariableFont(font, {"wght": weight}, updateFontNames=False))


def check(path, source):
    """Confirm the built font's transform carries each CSS weight to the design
    position WEIGHT_MAP names for it.

    Compares contour area at the built font's CSS weight against the source
    font instanced at WEIGHT_MAP's paired design value, so a default-move,
    `avar` segment, or relabel that drifts from what WEIGHT_MAP claims cannot
    pass silently. It cannot catch WEIGHT_MAP itself being wrong: both sides
    of the comparison read the same constant, so a mismeasured design value
    would print `ok` for every row while the built font still renders the
    wrong master.
    """
    ok = True
    for css_weight, design_value, label in WEIGHT_MAP:
        got = _instance_ink(path, css_weight)
        want = _instance_ink(source, design_value, drop_stat=True)
        hit = abs(got - want) < 1e-4
        ok = ok and hit
        print(
            f"  css {css_weight:<4} ({label:<10}) -> ink {got:.4f}  "
            f"expected {want:.4f}  {'ok' if hit else 'MISMATCH'}"
        )
    return ok


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"NanumSquareNeo-Variable.ttf to build from (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--output", default=OUTPUT, help=f"where to write the woff2 (default: {OUTPUT})"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the already-built font at --output instead of rebuilding",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.source):
        print(
            f"error: source font not found at {args.source}\n"
            "Download NanumSquare Neo from https://hangeul.naver.com/font and pass "
            "--source, or place it at the default path.",
            file=sys.stderr,
        )
        return 1

    if args.check:
        if not os.path.isfile(args.output):
            print(f"error: nothing built at {args.output}", file=sys.stderr)
            return 1
        print(f"checking {args.output}")
        return 0 if check(args.output, args.source) else 1

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    font = build(args.source)
    font.save(args.output)
    size = os.path.getsize(args.output)
    src_size = os.path.getsize(args.source)
    print(
        f"wrote {args.output}\n"
        f"  {src_size / 1e6:.2f} MB ttf -> {size / 1e6:.2f} MB woff2 "
        f"({size / src_size:.0%})"
    )
    print("verifying:")
    return 0 if check(args.output, args.source) else 1


if __name__ == "__main__":
    raise SystemExit(main())
