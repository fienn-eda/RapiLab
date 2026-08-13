#!/usr/bin/env python3
"""List this project's Claude Code sessions, newest first, with their IDs.

WHEN TO USE
    When you need a session ID rather than a picker - to resume from a script,
    to name a session in a note, or when the interactive picker cannot reach a
    conversation and `claude --resume <id>` is the way in.

WHY IT EXISTS
    The /resume picker is the only built-in listing and it needs a terminal, so
    there is no way to see what conversations exist from a script or a log. The
    transcripts are plain JSONL on disk and carry their own titles, so reading
    them directly answers the question without a session.

    A transcript's title is on an "ai-title" line, which is absent for sessions
    that ended before one was generated. Those fall back to their first real
    user message, so every session gets a recognizable label.

SAFETY
    Read-only.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
DEFAULT_PROJECT = "C--Users-fienn-Desktop-RapiLab"


def label_of(path):
    """The session's own title, or its opening user message if it never got one."""
    title = first_user = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"ai-title"' in line:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") == "ai-title":
                    title = entry.get("aiTitle")
            elif first_user is None and '"type":"user"' in line:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                content = entry.get("message", {}).get("content")
                # Hook and attachment turns arrive as user messages wrapped in
                # tags; they name the harness, not what the session was about.
                if isinstance(content, str) and content.strip() and not content.lstrip().startswith("<"):
                    first_user = " ".join(content.split())
    return title or first_user or "(no title)"


def main():
    ap = argparse.ArgumentParser(description="List Claude Code sessions for this project")
    ap.add_argument("-n", "--limit", type=int, default=20, help="how many to show (default 20)")
    ap.add_argument("--project", default=DEFAULT_PROJECT,
                    help="directory under ~/.claude/projects to read")
    ap.add_argument("--width", type=int, default=70, help="truncate labels to this width")
    args = ap.parse_args()

    directory = PROJECTS / args.project
    if not directory.is_dir():
        print("no such project directory: %s" % directory, file=sys.stderr)
        print("available:", file=sys.stderr)
        for d in sorted(os.listdir(PROJECTS)):
            print("  %s" % d, file=sys.stderr)
        return 1

    rows = [(f.stat().st_mtime, f.stem, label_of(f)) for f in directory.glob("*.jsonl")]
    rows.sort(reverse=True)

    for mtime, session_id, label in rows[:args.limit]:
        stamp = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
        print("%s  %s  %s" % (stamp, session_id, label[:args.width]))

    print()
    print("%d of %d sessions. Resume with: claude --resume <id>"
          % (min(args.limit, len(rows)), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
