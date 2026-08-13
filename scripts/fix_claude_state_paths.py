#!/usr/bin/env python3
r"""Repoint Claude Code's stored state at the project folder after it is renamed.

WHEN TO USE
    Right after renaming the project's top-level folder - as the step that
    follows ~/Desktop/rename-project-to-rapilab.ps1, which renames the folder
    itself and the outside settings that name it. Run --check any time /resume
    or the background-agent list misbehaves after a rename.

WHY IT EXISTS
    Renaming the folder leaves the DIRECTORY NAMES under ~/.claude/projects/
    stale, and the rename script fixes those. But the old path is also frozen
    INSIDE the state files, where a directory rename cannot reach:

      1. Every line of every session transcript carries a "cwd" field naming the
         directory that turn ran in. 173,632 of them on 2026-08-14.
      2. ~/.claude/jobs/<id>/state.json carries "cwd", "originCwd" and
         "linkScanPath". The last one points at the transcript through the
         ~/.claude/projects directory NAME, so after a rename it names a file
         that does not exist and opening that job from the list fails.

    Two spellings of the same path are stored, and they share no substring:

      C:\Users\fienn\Desktop\NikkeDeckBuilder     the real folder path
      C--Users-fienn-Desktop-NikkeDeckBuilder     the ~/.claude/projects dir name

    Searching for one finds none of the other. Both are handled here.

    Substitution is anchored to the path prefix, never the bare folder name: an
    old path can already contain the NEW name as an inner segment (there was a
    ...\dist\RapiLab\_internal\webview), and a bare-name replace corrupts it.

SAFETY
    Only path-bearing FIELDS are rewritten. Old paths quoted in message bodies
    and tool output are left alone - those record what was true at the time, and
    rewriting them would falsify the history. On this machine that was 313,985
    mentions left untouched against 173,632 fields fixed.

    Transcripts of live sessions are skipped. Every rewritten line is re-parsed
    as JSON, line counts and byte deltas are checked against what the
    substitution predicts, and each file is replaced atomically. Backs up
    ~/.claude before applying unless --no-backup. --revert undoes it exactly.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

DEFAULT_OLD_ROOT = r"C:\Users\fienn\Desktop\NikkeDeckBuilder"
DEFAULT_NEW_ROOT = r"C:\Users\fienn\Desktop\RapiLab"

CLAUDE = Path.home() / ".claude"
PROJECTS = CLAUDE / "projects"
SESSIONS = CLAUDE / "sessions"
JOBS = CLAUDE / "jobs"

# Job state keys whose VALUE is a path. Everything else in state.json - detail,
# intent, output - is prose about that run and stays as written.
JOB_PATH_KEYS = ('"cwd"', '"originCwd"', '"linkScanPath"')

# Matches the same keys in either file layout: transcripts are minified
# ("cwd":"...") and job state is pretty-printed ("cwd": "...").
PATH_FIELD_RE = re.compile(rb'"(cwd|originCwd|linkScanPath)"\s*:\s*"([^"]*)"')


def project_dir_name(root):
    """~/.claude/projects/ names a project by its path with non-alphanumerics dashed."""
    return re.sub(r"[^A-Za-z0-9]", "-", root)


def as_json_text(path):
    """The path as it literally appears inside a JSON file - backslashes doubled."""
    return path.replace("\\", "\\\\")


def live_session_ids():
    ids = set()
    for f in SESSIONS.glob("*.json"):
        try:
            ids.add(json.loads(f.read_text(encoding="utf-8"))["sessionId"])
        except Exception:
            continue
    return {i for i in ids if i}


def transcripts(root_dir=PROJECTS, prefix=None):
    """Every .jsonl under the project's directories, nested ones included.

    Subagent transcripts live one level deeper, at
    <session-id>/subagents/agent-*.jsonl. Globbing only the top level silently
    leaves those behind - 79,291 cwd values on the first pass here.
    """
    if not root_dir.is_dir():
        return
    for d in sorted(os.listdir(root_dir)):
        if prefix and not d.startswith(prefix):
            continue
        for dirpath, _, filenames in os.walk(root_dir / d):
            for fn in sorted(filenames):
                if fn.endswith(".jsonl"):
                    yield Path(dirpath) / fn


def owning_session(path):
    """The session a transcript belongs to.

    A subagent transcript is named agent-<hash>.jsonl, so the owner is the
    session-id directory above it, not the filename.
    """
    stem = path.stem
    for candidate in [stem, *path.parts]:
        if len(candidate) == 36 and candidate.count("-") == 4:
            return candidate
    return stem


def substitute(data, needle, replacement):
    """Replace and prove nothing but the intended spans moved."""
    hits = data.count(needle)
    if hits == 0:
        return data, 0, None
    out = data.replace(needle, replacement)
    if out.count(b"\n") != data.count(b"\n"):
        return data, 0, "line count changed"
    if len(out) - len(data) != hits * (len(replacement) - len(needle)):
        return data, 0, "unexpected byte delta"
    for before, after in zip(data.split(b"\n"), out.split(b"\n")):
        if before == after or not after.strip():
            continue
        try:
            json.loads(after.decode("utf-8"))
        except Exception as exc:
            return data, 0, "rewritten line is no longer valid JSON: %s" % exc
    return out, hits, None


def write_atomically(path, data):
    """Replace the file's bytes, keeping its modification time.

    The /resume picker orders conversations by recency, so a rewrite that
    restamps every transcript scrambles that order into one indistinguishable
    block. Preserving mtime keeps a migration invisible to everything that
    sorts by it.
    """
    stat = path.stat()
    tmp = path.with_suffix(path.suffix + ".tmp-pathfix")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    os.utime(path, (stat.st_atime, stat.st_mtime))


TIMESTAMP_RE = re.compile(rb'"timestamp":"(\d{4}-\d{2}-\d{2}T[0-9:.\-]+Z?)"')


def restore_mtimes(new_root, live, dry_run):
    """Rebuild transcript modification times from the timestamps inside them.

    Recovery for a rewrite that did not preserve mtime. A transcript records the
    wall-clock time of every turn, so its own last timestamp is a truer "when
    was this conversation last active" than the filesystem's - which any tool
    that rewrites the file destroys.
    """
    prefix = project_dir_name(new_root)
    fixed = skipped = untimed = 0
    for path in transcripts(prefix=prefix):
        if owning_session(path) in live:
            skipped += 1
            continue
        stamps = TIMESTAMP_RE.findall(path.read_bytes())
        if not stamps:
            untimed += 1
            continue
        latest = max(s.decode().rstrip("Z") for s in stamps)
        try:
            when = datetime.datetime.fromisoformat(latest).replace(
                tzinfo=datetime.timezone.utc).timestamp()
        except ValueError:
            untimed += 1
            continue
        if abs(path.stat().st_mtime - when) < 1:
            continue
        fixed += 1
        if not dry_run:
            os.utime(path, (when, when))
    print("  %d restamped, %d already correct or live, %d without timestamps"
          % (fixed, skipped, untimed))
    return fixed


def fix_transcripts(old_root, new_root, live, dry_run):
    needle = b'"cwd":"' + as_json_text(old_root).encode()
    replacement = b'"cwd":"' + as_json_text(new_root).encode()
    prefix = project_dir_name(new_root)

    touched = total = skipped = 0
    failures = []
    for path in transcripts(prefix=prefix):
        if owning_session(path) in live:
            if path.read_bytes().count(needle):
                skipped += 1
                print("  SKIP (live session)  %s" % path.name)
            continue
        data = path.read_bytes()
        out, hits, err = substitute(data, needle, replacement)
        if err:
            failures.append((path, err))
            print("  FAIL  %s -- %s" % (path.name, err))
        elif hits:
            touched += 1
            total += hits
            if not dry_run:
                write_atomically(path, out)
    return touched, total, skipped, failures


def fix_job_state(old_root, new_root, dry_run):
    subs = [
        (as_json_text(old_root), as_json_text(new_root)),
        (project_dir_name(old_root), project_dir_name(new_root)),
    ]
    touched = fields = 0
    for path in sorted(JOBS.glob("*/state.json")):
        original = path.read_text(encoding="utf-8")
        out_lines, changed = [], []
        for line in original.split("\n"):
            if any(line.lstrip().startswith(k + ":") for k in JOB_PATH_KEYS):
                new_line = line
                for old, new in subs:
                    new_line = new_line.replace(old, new)
                if new_line != line:
                    changed.append(line.lstrip().split(":")[0])
                line = new_line
            out_lines.append(line)
        if not changed:
            continue
        updated = "\n".join(out_lines)
        json.loads(updated)
        print("  %s  %s" % (path.parent.name, ", ".join(changed)))
        touched += 1
        fields += len(changed)
        if not dry_run:
            write_atomically(path, updated.encode("utf-8"))
    return touched, fields


def check(old_root):
    """Report any path FIELD still naming the old folder, anywhere under ~/.claude."""
    marker = Path(old_root).name.encode()
    stale = []
    for dirpath, dirnames, filenames in os.walk(CLAUDE):
        dirnames[:] = [d for d in dirnames if "-backup-" not in d]
        for fn in filenames:
            if not fn.endswith((".json", ".jsonl")):
                continue
            fp = Path(dirpath) / fn
            try:
                data = fp.read_bytes()
            except OSError:
                continue
            if marker not in data:
                continue
            for m in PATH_FIELD_RE.finditer(data):
                if marker in m.group(2):
                    stale.append((fp.relative_to(CLAUDE), m.group(1).decode(),
                                  m.group(2).decode("utf-8", "replace")))
    if stale:
        print("STALE PATH FIELDS: %d" % len(stale))
        for rel, key, val in stale[:20]:
            print("  %s  %s = %s" % (rel, key, val))
        if len(stale) > 20:
            print("  ... and %d more" % (len(stale) - 20))
    else:
        print("clean - no cwd / originCwd / linkScanPath names the old folder")

    name = marker.decode()
    config = Path.home() / ".claude.json"
    print("~/.claude.json mentions of %s: %d" % (name, config.read_bytes().count(marker)))
    print("project dirs still named with %s: %d"
          % (name, len([d for d in os.listdir(PROJECTS) if name in d])))
    return 1 if stale else 0


def verify_backup(backup_dir, old_root, new_root):
    """Prove the rewrite moved only the intended bytes, against a pre-change copy.

    Applying the same substitution to the backup must reproduce the live file
    byte for byte. Anything else means something other than the cwd prefix moved.
    """
    backup = Path(backup_dir)
    # Accept either a backup this script made (<dir>/projects/...) or a bare
    # copy of ~/.claude/projects.
    if (backup / "projects").is_dir():
        backup = backup / "projects"
    if not backup.is_dir():
        print("no such backup directory: %s" % backup)
        return 1
    needle = b'"cwd":"' + as_json_text(old_root).encode()
    replacement = b'"cwd":"' + as_json_text(new_root).encode()
    prefix = project_dir_name(new_root)

    checked = mismatched = badjson = missing = 0
    for backup_path in transcripts(root_dir=backup, prefix=prefix):
        rel = backup_path.relative_to(backup)
        live_path = PROJECTS / rel
        if not live_path.exists():
            print("  gone from live tree: %s" % rel)
            missing += 1
            continue
        expected = backup_path.read_bytes().replace(needle, replacement)
        actual = live_path.read_bytes()
        checked += 1
        if expected != actual:
            # A live session keeps appending, so a pure suffix growth is fine.
            if not actual.startswith(expected):
                print("  BYTE MISMATCH: %s" % rel)
                mismatched += 1
            continue
        for n, line in enumerate(actual.split(b"\n"), 1):
            if not line.strip():
                continue
            try:
                json.loads(line.decode("utf-8"))
            except Exception as exc:
                print("  BAD JSON: %s line %d -- %s" % (rel, n, exc))
                badjson += 1
                break
    print("checked %d transcripts; %d byte mismatches; %d unparseable; %d absent"
          % (checked, mismatched, badjson, missing))
    return 0 if not (mismatched or badjson) else 1


def make_backup(destination):
    dest = Path(destination)
    if dest.exists():
        print("backup already exists, reusing: %s" % dest)
        return dest
    print("backing up %s -> %s ..." % (PROJECTS, dest))
    shutil.copytree(PROJECTS, dest / "projects")
    shutil.copytree(JOBS, dest / "jobs")
    print("backup done")
    return dest


def main():
    ap = argparse.ArgumentParser(
        description="Repoint Claude Code's stored state after the project folder is renamed",
    )
    ap.add_argument("--old-root", default=DEFAULT_OLD_ROOT, help="path the state still names")
    ap.add_argument("--new-root", default=DEFAULT_NEW_ROOT, help="path it should name")
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    ap.add_argument("--revert", action="store_true", help="undo: rewrite new-root back to old-root")
    ap.add_argument("--check", action="store_true", help="only report stale path fields, then exit")
    ap.add_argument("--restore-mtimes", action="store_true",
                    help="rebuild transcript mtimes from their own timestamps, then exit")
    ap.add_argument("--verify-backup", metavar="DIR",
                    help="prove a completed run touched only the intended bytes")
    ap.add_argument("--backup-dir", help="where to copy state before applying")
    ap.add_argument("--no-backup", action="store_true", help="apply without copying state first")
    args = ap.parse_args()

    if args.check:
        return check(args.old_root)
    if args.verify_backup:
        return verify_backup(args.verify_backup, args.old_root, args.new_root)
    if args.restore_mtimes:
        print("restoring transcript mtimes%s:" % (" (DRY RUN)" if args.dry_run else ""))
        restore_mtimes(args.new_root, live_session_ids(), args.dry_run)
        return 0

    src, dst = (args.new_root, args.old_root) if args.revert else (args.old_root, args.new_root)
    print("mode      : %s%s" % ("REVERT" if args.revert else "FIX",
                                "  (DRY RUN)" if args.dry_run else ""))
    print("rewriting : %s  ->  %s" % (src, dst))
    print("scope     : path-bearing fields only, prefix-anchored")
    print()

    live = live_session_ids()
    if live:
        print("live sessions (skipped): %s" % ", ".join(sorted(live)))
        print()

    if not args.dry_run and not args.no_backup:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        make_backup(args.backup_dir or CLAUDE / ("state-backup-%s" % stamp))
        print()

    print("transcripts:")
    touched, total, skipped, failures = fix_transcripts(src, dst, live, args.dry_run)
    print("  %d file(s), %d cwd value(s), %d skipped" % (touched, total, skipped))
    print("job state:")
    jobs_touched, jobs_fields = fix_job_state(src, dst, args.dry_run)
    print("  %d file(s), %d field(s)" % (jobs_touched, jobs_fields))
    print()

    if failures:
        print("%d file(s) failed verification and were left untouched." % len(failures))
        return 1
    if args.dry_run:
        print("Dry run - nothing written. Re-run without --dry-run to apply.")
        return 0

    print("post-check:")
    return check(src)


if __name__ == "__main__":
    sys.exit(main())
