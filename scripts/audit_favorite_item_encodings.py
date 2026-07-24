#!/usr/bin/env python
"""Audit how every encoded Nikke treats its Favorite Item (애장품).

WHY: a Favorite Item is per-user investment, so a public deck recommender must
model the base unit and the Favorite-Item unit as separate candidates and pick
between them from the user's roster. Several early encodings instead baked the
Favorite-Item build into the base slug (the manifest reads the "dollskills"
array) because the encoder owned the item - correct for that account, wrong for
everyone else. This script finds those, plus the reverse gap: units whose
Favorite Item exists in the collected data but is not encoded at all.

WHEN TO RUN: after onboarding a Nikke, after collecting new character data, and
before shipping roster-driven Favorite-Item selection. It reads only committed
source and collected data - it changes nothing.

VERDICTS (per base unit):
  paired       base + "-signature" encoded, base reads skills - correct
  baked        single encoding reading dollskills - non-owners OVERESTIMATED
  unencoded-fi Favorite Item in the data, no encoding reads it - owners
               UNDERESTIMATED
  no-favorite  the source modelled Favorite Items and this unit has none
  no-data      the data cannot answer (file missing, or the source does not
               record Favorite Items) - NOT evidence of absence

Exit code is 1 when any unit lands in `baked` or `unencoded-fi`, so this can
gate a commit once the backlog is cleared.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.skill_rules.registry import ENCODED_SLUGS  # noqa: E402
from app.skill_rules.registry import get_skill_value_manifest  # noqa: E402
from app.skill_values import DATA_DIR, load_character_data  # noqa: E402

SLUG_MAP_TS = REPO / "frontend" / "src" / "lib" / "resourceIdSlugMap.ts"

ACTIONABLE = ("baked", "unencoded-fi")


def parse_slug_map(path=SLUG_MAP_TS):
    """The frontend's identity map and its two ownership tables.

    Parsed with regexes rather than imported (it is TypeScript); the backend
    drift test test_resource_id_slug_map.py parses the same literals, so a
    rename that breaks one breaks the other loudly.
    """
    text = path.read_text(encoding="utf-8")

    def between(marker, end):
        assert marker in text, f"marker {marker!r} not found in {path}"
        return text.split(marker, 1)[1].split(end, 1)[0]

    id_to_slug = {
        int(i): s
        for i, s in re.findall(
            r"(\d+):\s*'([a-z0-9-]+)'", between("Record<number, string> = {", "\n}")
        )
    }
    owned = {
        int(i)
        for i in re.findall(
            r"^\s*(\d+),", between("SIGNATURE_OWNED: ReadonlySet<number> = new Set([", "])"),
            re.M,
        )
    }
    dual = set(
        re.findall(
            r"'([a-z0-9-]+)'",
            between("DUAL_SLOT_BASES: ReadonlySet<string> = new Set([", "])"),
        )
    )
    return id_to_slug, owned, dual


def reads_dollskills(slug):
    """Whether this slug's manifest sources any value from the Favorite-Item
    array. None when the slug has no manifest (not loadable from user data)."""
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    return any(array == "dollskills" for array, _ in manifest["keys"].values())


def has_favorite_item(slug, data_dir):
    """Whether the collected data for this slug carries Favorite-Item skills.

    Returns None - undecidable - rather than False whenever the data cannot
    answer: no manifest, no file, or a source that does not record Favorite
    Items at all. The "dollskills" key ABSENT means the source is silent (the
    ShiftyPad schema has no such key, and older dotgg captures omit it); the key
    present but null means the source modelled it and found none. Collapsing
    those two would silently declare 21 units Favorite-Item-free on no evidence.
    """
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    try:
        data = load_character_data(
            manifest["source"], manifest.get("data_slug", slug), data_dir
        )
    except (FileNotFoundError, OSError):
        return None
    if "dollskills" in data:
        return bool(data["dollskills"])
    return _lootandwaifus_favorite_item(slug, data_dir)


def _lootandwaifus_favorite_item(slug, data_dir):
    """Second opinion for a unit whose own source is silent about Favorite Items.

    lootandwaifus always emits the key, so its file settles the question when one
    exists under the SAME slug. Matched exactly and never by prefix: "laplace"
    and "laplace-ultimate-hero" are different units, and a loose match would
    inherit the base unit's Favorite Item.
    """
    path = Path(data_dir) / "lootandwaifus" / f"char_{slug}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if "dollskills" not in data:
        return None
    return bool(data["dollskills"])


def audit(data_dir=DATA_DIR):
    """One record per base unit, sorted by verdict severity then slug."""
    encoded = set(ENCODED_SLUGS)
    id_to_slug, owned_ids, dual_bases = parse_slug_map()
    slug_to_id = {slug: rid for rid, slug in id_to_slug.items()}

    bases = sorted(s for s in encoded if not s.endswith("-signature"))
    records = []
    for base in bases:
        signature = f"{base}-signature"
        paired = signature in encoded
        base_fi = reads_dollskills(base)
        favorite = has_favorite_item(base, data_dir)

        if paired:
            verdict = "paired"
        elif favorite is None:
            verdict = "no-data"
        elif base_fi:
            verdict = "baked"
        elif favorite:
            verdict = "unencoded-fi"
        else:
            verdict = "no-favorite"

        rid = slug_to_id.get(base)
        records.append(
            {
                "slug": base,
                "verdict": verdict,
                "resource_id": rid,
                "mapped": rid is not None,
                "in_dual_slot_bases": base in dual_bases,
                "signature_owned": rid in owned_ids if rid is not None else False,
                "base_reads_dollskills": base_fi,
                "has_favorite_item": favorite,
            }
        )

    order = {v: i for i, v in enumerate(
        ("baked", "unencoded-fi", "no-data", "paired", "no-favorite"))}
    records.sort(key=lambda r: (order[r["verdict"]], r["slug"]))
    return records


def format_report(records):
    lines = []
    by_verdict = {}
    for r in records:
        by_verdict.setdefault(r["verdict"], []).append(r)

    headings = {
        "baked": "BAKED — 애장품 빌드가 base 슬러그에 박혀 있음 (미보유 유저 과대평가)",
        "unencoded-fi": "UNENCODED — 애장품이 데이터에 있으나 인코딩 안 됨 (보유 유저 과소평가)",
        "no-data": "NO DATA — 소스가 애장품을 기록하지 않아 판정 불가 (부재 증거 아님)",
        "paired": "PAIRED — base + -signature 양쪽 인코딩됨 (정상)",
        "no-favorite": "NO FAVORITE — 애장품 없음 (조치 불필요)",
    }
    for verdict in ("baked", "unencoded-fi", "no-data", "paired", "no-favorite"):
        rows = by_verdict.get(verdict, [])
        lines.append(f"\n## {headings[verdict]}  [{len(rows)}]")
        if not rows:
            lines.append("  (없음)")
            continue
        for r in rows:
            rid = r["resource_id"] if r["resource_id"] is not None else "―"
            flags = []
            if not r["mapped"]:
                flags.append("맵미등록")
            if verdict == "paired":
                if not r["in_dual_slot_bases"]:
                    flags.append("DUAL_SLOT_BASES누락")
                flags.append("소유=" + ("O" if r["signature_owned"] else "X"))
            suffix = ("  " + " ".join(flags)) if flags else ""
            lines.append(f"  {r['slug']:<34} id={rid!s:<5}{suffix}")

    actionable = sum(len(by_verdict.get(v, [])) for v in ACTIONABLE)
    lines.append(f"\n조치 필요 합계: {actionable}개 유닛")
    return "\n".join(lines)


def main():
    # The report is Korean; a cp949 console (Windows default here) cannot encode
    # it and would abort mid-print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR,
        help="collected-data root (default: repo data/)",
    )
    parser.add_argument("--json", action="store_true", help="emit records as JSON")
    args = parser.parse_args()

    records = audit(args.data_dir)
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        print(format_report(records))

    actionable = sum(1 for r in records if r["verdict"] in ACTIONABLE)
    return 1 if actionable else 0


if __name__ == "__main__":
    sys.exit(main())
