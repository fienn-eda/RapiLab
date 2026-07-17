#!/usr/bin/env python3
"""Copy the gitignored data/ payload from the main checkout into this worktree.

WHEN TO USE
    Run this first thing in any git worktree, before measuring or running
    anything that reads data/ - API loadability, manifest coverage, "does this
    unit have weapon stats", the roster loader, the test suite.

WHY IT EXISTS
    data/dotgg/ and data/lootandwaifus/ are gitignored, and git populates a new
    worktree only from TRACKED files. So a worktree starts with no data/ at all,
    or - worse, because it looks fine - a stale subset frozen at the moment the
    worktree was cut, missing everything collected in main since.

    That silently turns absent data into wrong conclusions. On 2026-07-17 an
    Ein encoding measured her as "not API-loadable, no dotgg weapon file" and
    wrote it into two docs as fact. The file was in main the whole time; this
    worktree was 18 files behind. Syncing moved loadable from 50/58 to 54/58 -
    ein, ark-ranger-black, prika and marciana-marine-study were all only
    "missing" for the same reason.

    A missing-data result from a worktree is a worktree artifact until proven
    otherwise. This script removes the doubt.

SAFETY
    Copies only files the worktree does not already have. Never overwrites,
    never deletes, never touches the main checkout. Safe to re-run.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Gitignored directories that carry collected character data.
SYNCED_DIRS = ("data/dotgg", "data/lootandwaifus")


def _git(*args, cwd=None):
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "git %s failed (exit %d): %s"
            % (" ".join(args), result.returncode, result.stderr.strip() or "<no stderr>")
        )
    return result.stdout.strip()


def locate_checkouts():
    """(worktree_root, main_root). main_root is None when we're already in the
    main checkout - the common git dir's parent IS our root."""
    try:
        worktree_root = Path(_git("rev-parse", "--show-toplevel")).resolve()
        # --git-common-dir points at the ONE real .git, which lives in the main
        # checkout even when called from a linked worktree.
        common = Path(_git("rev-parse", "--git-common-dir")).resolve()
    except RuntimeError as exc:
        raise SystemExit("not a git repository, or git is unavailable: %s" % exc)

    main_root = common.parent
    if main_root == worktree_root:
        return worktree_root, None
    if not main_root.is_dir():
        raise SystemExit(
            "resolved the main checkout to %s, which does not exist - cannot sync"
            % main_root
        )
    return worktree_root, main_root


def plan_copies(worktree_root, main_root):
    """[(src, dest), ...] for files main has and the worktree lacks."""
    copies, missing_sources = [], []
    for rel in SYNCED_DIRS:
        source_dir = main_root / rel
        if not source_dir.is_dir():
            missing_sources.append(rel)
            continue
        for source in sorted(source_dir.iterdir()):
            if not source.is_file():
                continue
            dest = worktree_root / rel / source.name
            if not dest.exists():
                copies.append((source, dest))
    return copies, missing_sources


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--check", action="store_true",
        help="report what is missing and exit 1 if anything is, without copying "
             "(use to fail fast before taking a measurement)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="print nothing when already in sync (for unattended/startup runs)",
    )
    args = parser.parse_args(argv)

    worktree_root, main_root = locate_checkouts()
    if main_root is None:
        if not args.quiet:
            print("In the main checkout - nothing to sync.")
        return 0

    copies, missing_sources = plan_copies(worktree_root, main_root)
    for rel in missing_sources:
        print("warning: %s does not exist in the main checkout (%s) - skipped"
              % (rel, main_root), file=sys.stderr)

    if not copies:
        if not args.quiet:
            print("Already in sync with %s." % main_root)
        return 0

    if args.check:
        print("%d file(s) missing from this worktree (main: %s):"
              % (len(copies), main_root), file=sys.stderr)
        for _, dest in copies:
            print("  %s" % dest.relative_to(worktree_root), file=sys.stderr)
        print("\nRun without --check to copy them. Measurements that read data/ "
              "are unreliable until you do.", file=sys.stderr)
        return 1

    copied = 0
    for source, dest in copies:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, dest)
        except OSError as exc:
            print("error: could not copy %s -> %s: %s" % (source, dest, exc),
                  file=sys.stderr)
            return 1
        copied += 1

    print("Synced %d file(s) from %s." % (copied, main_root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
