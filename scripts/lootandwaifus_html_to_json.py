"""Convert saved lootandwaifus.com character pages (data/lootandwaifus/*.html)
into per-character JSON (data/lootandwaifus/*.json), mirroring the dotgg JSON
field names so both sources read the same way.

lootandwaifus renders the real numbers inline per level (no
`description_value_NN` placeholder structure like dotgg), so each skill here
carries the cleaned description TEXT for all 10 levels rather than value-slot
dicts. Metadata (name, weapon, element, class, burst tier, burst cooldown) is
read from the character-info tags and the burst skill's cooldown tag.

When to use: after collecting/refreshing HTML with the same `curl -A` the
data-sources reference documents, run this to get compact, machine-readable JSON
next to the HTML. Re-runnable and idempotent.

Usage:
    python scripts/lootandwaifus_html_to_json.py            # convert every *.html
    python scripts/lootandwaifus_html_to_json.py --slug mint  # just one
    python scripts/lootandwaifus_html_to_json.py --dry-run   # parse + summarize, write nothing

Output is a one-line summary per file (name / weapon / element / burst / skill
names + cooldowns). On a parse gap it prints a WARN line and still writes what it
found (fields it couldn't read are null), so a site markup change is visible
rather than silently producing wrong data.
"""
import argparse
import html as ihtml
import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "lootandwaifus"

# The weapon icon's alt is sometimes the full name, sometimes the code - accept
# both.
WEAPON_CODES = {
    "Rocket Launcher": "RL", "Sniper Rifle": "SR", "Assault Rifle": "AR",
    "Machine Gun": "MG", "Submachine Gun": "SMG", "Shotgun": "SG",
    "RL": "RL", "SR": "SR", "AR": "AR", "MG": "MG", "SMG": "SMG", "SG": "SG",
}
ELEMENTS = {"Fire", "Water", "Wind", "Iron", "Electric"}
CLASSES = {"Attacker", "Defender", "Supporter"}
MANUFACTURERS = {"Elysion", "Missilis", "Tetra", "Pilgrim", "Abnormal"}


def _clean(text: str) -> str:
    """Strip a level-description paragraph's markup to plain text: <br> -> newline,
    drop remaining tags, unescape entities, collapse runs of spaces/tabs."""
    text = text.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", ihtml.unescape(text)).strip()


def _character_info_alts(raw: str) -> list[str]:
    """`alt="..."` values inside the character-info block (element/weapon/class/
    burst/manufacturer tags), sliced out so we don't pick up nav or ad icons."""
    start = raw.find('id="character-info"')
    end = raw.find('id="skills"', start)
    block = raw[start:end] if start != -1 and end != -1 else raw
    return re.findall(r'alt="([^"]+)"', block)


def parse_html(raw: str, slug: str) -> tuple[dict, list[str]]:
    warnings: list[str] = []

    name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", raw)
    name = ihtml.unescape(name_match.group(1)).strip() if name_match else None
    if not name:
        warnings.append("no <h1> name")

    alts = _character_info_alts(raw)
    element = next((a for a in alts if a in ELEMENTS), None)
    weapon = next((WEAPON_CODES[a] for a in alts if a in WEAPON_CODES), None)
    klass = next((a for a in alts if a in CLASSES), None)
    manufacturer = next((a for a in alts if a in MANUFACTURERS), None)
    burst_match = next((re.match(r"Burst (\d)", a) for a in alts if a.startswith("Burst ")), None)
    burst = burst_match.group(1) if burst_match else None
    for field, value in [("element", element), ("weapon", weapon), ("class", klass), ("burst", burst)]:
        if value is None:
            warnings.append(f"no {field}")

    titles = re.findall(r'<div class="skill-title-section[^"]*"[^>]*><h3[^>]*>([^<]+)</h3>', raw)
    titles = [ihtml.unescape(t).strip() for t in titles]
    # 3 = base skills only; 6 = a signature-weapon (애장품) unit whose page also
    # carries the "treasure" (favorite-item) versions, base first then treasure.
    if len(titles) not in (3, 6):
        warnings.append(f"expected 3 or 6 skill titles, found {len(titles)}")

    # Level-description paragraphs in document order: for each skill (base ones
    # then any treasure ones), Lv1..10 (data-level 0..9 resets per skill).
    descriptions = re.findall(r'<p class="level-description[^"]*" data-level="\d"[^>]*>(.*?)</p>', raw, re.S)
    if len(descriptions) != len(titles) * 10:
        warnings.append(f"expected {len(titles) * 10} level paragraphs, found {len(descriptions)}")

    title_positions = [m.start() for m in re.finditer(r'<div class="skill-title-section', raw)]

    def make_skill(i: int) -> dict:
        # A skill-1/2 passive puts its own cooldown inline in the h3 title
        # ("(Cooldown: 30s)"); the burst uses a separate "N sec Cooldown" tag.
        raw_title = titles[i]
        title_cd = re.search(r"\(Cooldown:\s*([\d.]+)\s*s\)", raw_title)
        if title_cd:
            cooldown = float(title_cd.group(1))
            skill_name = raw_title[:title_cd.start()].strip()
        else:
            skill_name = raw_title
            block_start = title_positions[i]
            block_end = title_positions[i + 1] if i + 1 < len(title_positions) else len(raw)
            tag_cd = re.search(r"(\d+(?:\.\d+)?)\s*sec Cooldown", raw[block_start:block_end])
            cooldown = float(tag_cd.group(1)) if tag_cd else None
        levels = [_clean(d) for d in descriptions[i * 10:(i + 1) * 10]]
        return {"name": skill_name, "cooldown": cooldown, "levels": levels}

    all_skills = [make_skill(i) for i in range(len(titles))]
    skills = all_skills[:3]
    dollskills = all_skills[3:6] if len(titles) == 6 else None
    burst_cooldown = skills[2]["cooldown"] if len(skills) == 3 else None

    data = {
        "name": name,
        "url": slug,
        "source": "lootandwaifus",
        "class": klass,
        "weapon": weapon,
        "element": element,
        "burst": burst,
        "manufacturer": manufacturer,
        "cooldown": burst_cooldown,
        "skills": skills,
        "dollskills": dollskills,
    }
    return data, warnings


def _summary(data: dict) -> str:
    skills = " | ".join(
        f"{s['name']}" + (f" (cd {s['cooldown']:g})" if s["cooldown"] else "") for s in data["skills"]
    )
    meta = f"{data['weapon']}/{data['element']}/{data['class']}/B{data['burst']}"
    if data["cooldown"]:
        meta += f" cd{data['cooldown']:g}"
    if data["dollskills"]:
        meta += " +sig"
    return f"{data['name']} [{meta}] :: {skills}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", help="convert only data/lootandwaifus/char_<slug>.html")
    ap.add_argument("--dry-run", action="store_true", help="parse and summarize, write no JSON")
    args = ap.parse_args()

    files = ([DATA_DIR / f"char_{args.slug}.html"] if args.slug
             else sorted(DATA_DIR.glob("char_*.html")))
    if not files or (args.slug and not files[0].exists()):
        print(f"no HTML found (looked in {DATA_DIR})", file=sys.stderr)
        return 1

    total_warnings = 0
    for html_path in files:
        slug = html_path.stem[len("char_"):]
        raw = html_path.read_text(encoding="utf-8")
        data, warnings = parse_html(raw, slug)
        for w in warnings:
            total_warnings += 1
            print(f"  WARN {slug}: {w}", file=sys.stderr)
        if not args.dry_run:
            out_path = html_path.with_suffix(".json")
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(("[dry] " if args.dry_run else "") + _summary(data))

    print(f"\n{len(files)} file(s), {total_warnings} warning(s)"
          + ("" if args.dry_run else f" -> wrote JSON next to each HTML in {DATA_DIR}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
