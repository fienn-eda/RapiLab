"""Detect nikkes released since the committed directory snapshot.

A newly released Nikke is dropped silently by the roster pipeline: it is not
in tools/collect-blablalink/nikke-directory.json, so assemble_roster skips it
and the frontend never gets a name to warn about. The only existing signal is
an unknown_name_codes counter in the server log that nobody reads, and it only
counts units you already own. This script watches the public directory instead,
so a release is noticed whether or not you pulled the unit.

It never modifies the repository: the fresh dump goes to data/cache/, and
refreshing the committed snapshot stays a deliberate step of onboarding.

Findings are reported with a Windows toast because the scheduled run has no
console anyone reads. Failures toast too - a check that dies quietly is worse
than no check, because you would believe you were covered.

When to use: automatically, from the daily scheduled task registered by
scripts/schedule_new_nikke_check.ps1. Run it by hand to check right now.

Usage:
    python3 scripts/check_new_nikkes.py                 # fetch + compare + toast
    python3 scripts/check_new_nikkes.py --offline FILE   # compare FILE, no fetch
    python3 scripts/check_new_nikkes.py --dry-run        # print, never toast

Exit: 0 nothing new, 1 new SSR found, 2 the check itself failed.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "tools" / "collect-blablalink" / "nikke-directory.json"
COLLECT_DIR = ROOT / "tools" / "collect-blablalink"
SCRATCH = ROOT / "data" / "cache" / "new-nikke-check"
FRESH = SCRATCH / "fresh-directory.json"
LOG = SCRATCH / "last-run.log"
TOAST = ROOT / "scripts" / "notify_toast.ps1"

# Raid content is SSR-only - assemble_roster filters the same way - so a new
# R/SR is not something to act on.
RAID_RARITY = "SSR"
TOAST_NAME_LIMIT = 3


def load_committed():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def new_entries(committed, fresh):
    """Entries whose resource_id is absent from the committed snapshot.

    Keyed on resource_id, not name: a rename is not a release, and an entry
    disappearing from the directory is not something we act on."""
    known = {e["resource_id"] for e in committed}
    return [e for e in fresh if e["resource_id"] not in known]


def new_ssr(entries):
    return [e for e in entries if e.get("original_rare") == RAID_RARITY]


def describe(entry):
    return (f"{entry['resource_id']:>5}  {entry.get('name_en')}  "
            f"[{entry.get('original_rare')} {entry.get('class')} "
            f"{entry.get('corporation')}]")


def toast_body(entries):
    names = [e.get("name_en") for e in entries]
    if len(names) <= TOAST_NAME_LIMIT:
        return ", ".join(names)
    shown = ", ".join(names[:TOAST_NAME_LIMIT])
    return f"{shown} 외 {len(names) - TOAST_NAME_LIMIT}명"


def toast(title, body):
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(TOAST),
         "-Title", title, "-Body", body],
        check=True,
    )


def fetch_directory():
    """Dump the live public directory to the scratch path. Never writes to the
    committed snapshot: --out points into data/cache/.

    The scheduled task has no console, so a plain check=True (whose
    CalledProcessError carries only the exit code) would leave the toast and
    log saying nothing about what actually broke - e.g. collect.js's own
    COLLECT_ERROR: no Chrome/Edge executable found; set CHROME_PATH. Capture
    the child's output and fold its stderr into the raised error so both
    destinations say what failed."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["node", "collect.js", "--directory", "--headless", "--out", str(FRESH)],
        cwd=str(COLLECT_DIR), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"collect.js failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return FRESH


def run(fresh_path=None, dry_run=False, notify=toast):
    path = Path(fresh_path) if fresh_path else fetch_directory()
    fresh = json.loads(Path(path).read_text(encoding="utf-8"))
    committed = load_committed()

    added = new_entries(committed, fresh)
    ssr = new_ssr(added)
    # Keyed on resource_id (not `e in ssr`): ssr entries are plain dicts, so a
    # membership scan there does an O(n) value-equality check per entry
    # instead of using the unique key we already established above.
    ssr_ids = {e["resource_id"] for e in ssr}
    for e in added:
        label = "NEW  " if e["resource_id"] in ssr_ids else "new (non-SSR, ignored)  "
        print(label + describe(e))
    print(f"{len(fresh)} nikkes live, {len(committed)} in the snapshot, "
          f"{len(added)} new ({len(ssr)} SSR)")

    if not ssr:
        return 0
    print("\nOnboarding: run the /onboard-new-nikkes skill — it collects, drafts an\n"
          "encoding plan for your approval, then implements/tests/docs/merges the\n"
          "approved units (the only manual step is approving the plan).")
    if not dry_run:
        notify("신규 니케 감지", toast_body(ssr))
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--offline", metavar="FILE",
                   help="compare this directory dump instead of fetching a fresh one")
    p.add_argument("--dry-run", action="store_true",
                   help="print what would be reported, never show a toast")
    args = p.parse_args()
    try:
        return run(args.offline, args.dry_run, toast)
    except Exception as exc:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        LOG.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        first_line = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        if not args.dry_run:
            try:
                toast("신규 니케 점검 실패", first_line[:200])
            except Exception:
                pass  # a failing toast must not hide the original failure
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
