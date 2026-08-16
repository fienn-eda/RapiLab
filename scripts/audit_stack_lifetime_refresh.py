"""Which timed resource stacks would change if their lifetime REFRESHED?

WHY: NIKKE's "X, stacks up to N time(s) and lasts for D sec" clause is ONE
timer the whole stack shares - every new stack restarts D for all of them, so
the count climbs toward the cap while consecutive fills stay inside D (the
Raven ruling, Fienn 2026-07-17; re-confirmed on Maiden: Ice Rose in the range,
2026-08-17). Read as N independent D-second timers instead, a counter settles
at "fills per lifetime" and a cap the game reaches every fight is never
touched. `ResourceBuff.lifetime_refreshes` encodes the right rule.

This answers the only question that decides whether a unit is affected: does
the semantic CHANGE the count? It does not when fills already arrive fast
enough to hold the cap under the independent-timer rule, and it does not when
they are so far apart that the chain breaks anyway. So the audit reports both
the count and the damage, and a unit is only worth opening when one moves.

It reports in two parts, because the bug has two hiding places:

1. A TEXT census of every encoded bullet pairing "stacks up to N" with a
   duration. This is the part that catches a stack encoded as OVERLAPPING
   `buff_rule` instances rather than a resource - Rosanna: Signature's Frenzy
   and Centi's Field Discussion are both that shape, and both were written off
   with "the cap is not reachable", which is per-stack-expiry arithmetic.
   "stacks up to N ... continuously" is a permanent accumulation and belongs on
   `lifetime=None`, so it is excluded.
2. An ENGINE check of the resource-backed ones: the count under each rule, and
   the damage.

It does not decide anything. A row that moves is a question for Fienn's range
test, not a licence to flip the flag.

The counts come from the engine's own `SquadContext.resource_count` over the
fill timeline a real 180-second deck simulation produces - never a
reimplementation (docs/insights.md: measurement scripts must ask the module).
The damage half wraps `resource_count` itself rather than flipping the flag on
each buff, because a resource's lifetime also travels inside the gate tuples
that decide nukes and damage typing, and those call sites take no flag -
Laplace's Hero Vision has NO buff at all, only a gate.

WHEN TO RUN: after encoding a resource that pairs a `cap` with a duration, and
whenever the stack semantics are revisited.

    python scripts/audit_stack_lifetime_refresh.py
    python scripts/audit_stack_lifetime_refresh.py --census      # text half only
    python scripts/audit_stack_lifetime_refresh.py --slug modernia --verbose
    # is a resource encoded as permanent really equivalent to refreshing?
    python scripts/audit_stack_lifetime_refresh.py --slug leona \
        --assume-lifetime leona:roar:5

Exit code is 1 when any resource's count or damage moves, so it reads as a
checklist rather than a gate.
"""
import argparse
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app import roster as roster_module  # noqa: E402
from app import squad_engine  # noqa: E402
from app.deck_search import (  # noqa: E402
    BossProfile,
    deck_is_valid,
    evaluate_deck,
    feasible_orderings,
)
from app.models import UserNikkeState  # noqa: E402
from app.skill_rules import registry as skill_registry  # noqa: E402
from app.skill_values import load_character_data  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from dump_skill_text import _source_for  # noqa: E402

FIGHT_DURATION = 180.0
GRID_STEP = 0.05
# Deckmates that carry no timed-stack resource of their own, so the deck column
# reports the candidate's own effect and not a shellmate's. Keyed by the
# candidate's burst tier, so she is the only unit who can open her own tier's
# window - Zwei's and Laplace's resources are fed by their OWN burst, and a
# shellmate holding that seat silences them entirely.
SHELL_BY_TIER = {
    1: ["crown", "red-hood", "helm", "mint"],
    2: ["liter", "red-hood", "helm", "mint"],
    3: ["liter", "crown", "helm", "mint"],
}


STACK_CLAUSE = re.compile(r"[Ss]tacks? up to (\d+)")
DURATION_CLAUSE = re.compile(r"(?:lasts )?for ([\d.]+) sec")
CONTINUOUS_CLAUSE = re.compile(r"continuously")


def timed_stack_bullets():
    """(slug, array, seconds, cap, text) for every encoded bullet that pairs a
    stack cap with a duration - whatever shape the encoding gave it.

    `array` matters: a `dollskills` bullet belongs to the Favorite Item build
    only, so reporting it against the base slug would invent a bullet the base
    build never reads."""
    hits = []
    for slug in sorted(skill_registry._BUILDERS):
        source, data_slug = _source_for(slug)
        try:
            data = load_character_data(source, data_slug)
        except FileNotFoundError:
            continue
        for array in ("skills", "dollskills"):
            for skill in data.get(array) or []:
                levels = skill.get("levels") or []
                text = levels[-1] if levels and isinstance(levels[-1], str) else ""
                if source == "dotgg":
                    text = skill.get("description") or ""
                for line in text.splitlines():
                    stack = STACK_CLAUSE.search(line)
                    duration = DURATION_CLAUSE.search(line)
                    if stack and duration and not CONTINUOUS_CLAUSE.search(line):
                        cap = next(g for g in stack.groups() if g)
                        hits.append((slug, array, float(duration.group(1)), int(cap),
                                     line.strip()))
    return hits


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


class _Watcher:
    """Capture, from one real simulation, both the ResourceSpecs the engine
    built and the SquadContexts that hold the fill timeline."""

    def __init__(self, assume=None):
        self.specs = {}
        self.contexts = []
        # (slug, resource, seconds): give a resource encoded as PERMANENT the
        # duration its skill text states, under the refreshing rule - the test
        # for "a permanent accumulation reproduces the refresh exactly".
        self.assume = assume
        self._orig_init = squad_engine.SquadContext.__init__
        # roster.py imports the getter by name, so THAT binding is the one a
        # simulation actually reads.
        self._orig_specs = roster_module.get_resource_specs

    def __enter__(self):
        watcher = self

        def patched_init(ctx, *args, **kwargs):
            watcher._orig_init(ctx, *args, **kwargs)
            watcher.contexts.append(ctx)

        def patched_specs(slug, skill_values):
            specs = watcher._orig_specs(slug, skill_values)
            if specs and watcher.assume:
                a_slug, a_name, a_seconds = watcher.assume
                for spec in specs:
                    if slug == a_slug and spec.name == a_name:
                        for buff in spec.buffs:
                            buff.lifetime = a_seconds
                            buff.lifetime_refreshes = True
            if specs:
                watcher.specs[slug] = specs
            return specs

        squad_engine.SquadContext.__init__ = patched_init
        roster_module.get_resource_specs = patched_specs
        return self

    def __exit__(self, *exc):
        squad_engine.SquadContext.__init__ = self._orig_init
        roster_module.get_resource_specs = self._orig_specs

    def fills_for(self, slug, name):
        best, best_ctx = [], None
        for ctx in self.contexts:
            fills = ctx.resource_fills.get((slug, name), [])
            if len(fills) > len(best):
                best, best_ctx = fills, ctx
        return best, best_ctx


class _GlobalRefresh:
    """Make EVERY finite-lifetime read use the refreshing rule, by wrapping
    `resource_count` itself.

    Flipping `ResourceBuff.lifetime_refreshes` reaches only the count-scaled
    BUFF path. A resource's lifetime also travels in the 4-tuples that gate
    nukes and damage typing (`resource_gate`), and those call sites pass no
    such flag, so a unit whose resource exists only to answer a gate would
    measure as "no effect" for the wrong reason."""

    def __init__(self):
        self._original = squad_engine.SquadContext.resource_count

    def __enter__(self):
        original = self._original

        def patched(ctx, slug, name, time, cap, lifetime=None, lifetime_refreshes=False):
            return original(ctx, slug, name, time, cap, lifetime,
                            lifetime_refreshes=lifetime is not None)

        squad_engine.SquadContext.resource_count = patched
        return self

    def __exit__(self, *exc):
        squad_engine.SquadContext.resource_count = self._original


def _deck_for(slug, boss, shell_override=None):
    """A valid deck seating `slug`, or None. See SHELL_BY_TIER for why the
    shell depends on her tier."""
    solo, excluded = load_roster([_nikke(slug)])
    if excluded or not solo:
        return None
    shell = shell_override or SHELL_BY_TIER[solo[0].burst_tier]
    shell = [s for s in shell if s != slug]
    specs, excluded = load_roster([_nikke(s) for s in shell + [slug]])
    if excluded:
        return None
    for ordering in feasible_orderings(specs):
        if deck_is_valid(ordering) and slug in {u.slug for u in ordering}:
            return ordering
    return None


def _counts(ctx, slug, name, cap, lifetime, refreshes):
    steps = int(FIGHT_DURATION / GRID_STEP) + 1
    return [
        ctx.resource_count(slug, name, i * GRID_STEP, cap, lifetime,
                           lifetime_refreshes=refreshes)
        for i in range(steps)
    ]


def _summary(counts):
    return {
        "max": max(counts) if counts else 0.0,
        "mean": sum(counts) / len(counts) if counts else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", help="audit only this slug")
    parser.add_argument("--element", default="Water")
    parser.add_argument("--enemy-def", type=float, default=8000.0,
                        help="a DEF-carrying boss: at DEF 0 true damage is worth nothing")
    # A Hit Rate stack is worth exactly nothing against a boss with no core, so
    # measuring one that way reads "no effect" whatever the truth is
    # (docs/insights.md, the sweep-boss trap). Both gates default ON here.
    parser.add_argument("--no-core", action="store_true", help="boss has no hittable core")
    parser.add_argument("--core-diameter", type=float, default=48.89,
                        help="core size in px - the SECOND gate hit rate needs")
    parser.add_argument("--shell", help="comma-separated deckmates, overriding SHELL_BY_TIER")
    parser.add_argument("--assume-lifetime", metavar="SLUG:RESOURCE:SECONDS",
                        help="give a PERMANENT-encoded resource its stated duration, "
                             "refreshing - tests whether permanence reproduces it")
    parser.add_argument("--verbose", action="store_true", help="print the fill timeline")
    parser.add_argument("--census", action="store_true",
                        help="print the text census only, and skip the simulations")
    args = parser.parse_args()

    bullets = timed_stack_bullets()
    if args.slug:
        bullets = [b for b in bullets if b[0] == args.slug]
    print(f"TEXT CENSUS - {len(bullets)} bullet(s) pairing a stack cap with a duration, "
          f"across {len({b[0] for b in bullets})} slug(s).")
    print("Each is this rule's business; check how its encoding holds the count.\n")
    for slug, array, seconds, cap, text in bullets:
        print(f"  {slug:<30} {array:<10} {cap:>3} x {seconds:>5.1f}s  {text[:78]}")
    if args.census:
        return 1 if bullets else 0

    if "lifetime_refreshes" not in inspect.signature(
            squad_engine.SquadContext.resource_count).parameters:
        print("\nThe engine half of this audit needs SquadContext.resource_count's "
              "`lifetime_refreshes` parameter, which landed with the Maiden: Ice Rose "
              "fix. Nothing to compare against on this checkout.")
        return 2
    print()

    boss = BossProfile(element=args.element, core_hittable=not args.no_core,
                       core_diameter_px=args.core_diameter,
                       enemy_def=args.enemy_def, fight_duration=FIGHT_DURATION)
    shell = args.shell.split(",") if args.shell else None
    slugs = [args.slug] if args.slug else sorted(skill_registry._RESOURCE_SPEC_BUILDERS)

    print(f"{'slug':<30} {'resource':<20} {'stat':<28} cap  life  "
          f"plain max/mean  refresh max/mean  moves")
    moved = []
    for slug in slugs:
        # The deck is built INSIDE the watcher: roster.py builds the
        # ResourceSpecs while assembling unit specs, before any simulation runs.
        with _Watcher() as watcher:
            deck = _deck_for(slug, boss, shell)
            if deck is None:
                print(f"{slug:<30} -- no valid deck --")
                continue
            evaluate_deck(deck, boss)
        for spec in watcher.specs.get(slug, []):
            for buff in spec.buffs:
                if buff.lifetime is None:
                    continue
                fills, ctx = watcher.fills_for(slug, spec.name)
                if not fills:
                    print(f"{slug:<30} {spec.name:<20} {buff.stat:<28} "
                          f"-- no fills in this deck --")
                    continue
                plain = _summary(_counts(ctx, slug, spec.name, spec.cap, buff.lifetime, False))
                fresh = _summary(_counts(ctx, slug, spec.name, spec.cap, buff.lifetime, True))
                differs = (abs(plain["max"] - fresh["max"]) > 1e-9
                           or abs(plain["mean"] - fresh["mean"]) > 1e-9)
                if differs:
                    moved.append(slug)
                print(f"{slug:<30} {spec.name:<20} {buff.stat:<28} "
                      f"{spec.cap:>3.0f} {buff.lifetime:>5.1f}  "
                      f"{plain['max']:>4.1f}/{plain['mean']:>5.2f}     "
                      f"{fresh['max']:>4.1f}/{fresh['mean']:>5.2f}      "
                      f"{'YES' if differs else 'no'}"
                      f"{'  (refreshing already)' if buff.lifetime_refreshes else ''}")
                if args.verbose:
                    times = [round(t, 2) for t, _ in sorted(fills)]
                    gaps = [round(b - a, 2) for a, b in zip(times, times[1:])]
                    print(f"    fills({len(times)}): {times[:14]}"
                          f"{' ...' if len(times) > 14 else ''}")
                    print(f"    gaps: {gaps[:13]}{' ...' if len(gaps) > 13 else ''}")

    print("\nDamage under the refreshing rule, every read path (gates included):")
    for slug in slugs:
        deck = _deck_for(slug, boss, shell)
        if deck is None:
            continue
        before = evaluate_deck(deck, boss)
        if args.assume_lifetime:
            a_slug, a_name, a_seconds = args.assume_lifetime.split(":")
            with _Watcher(assume=(a_slug, a_name, float(a_seconds))):
                after = evaluate_deck(_deck_for(slug, boss, shell), boss)
        else:
            with _GlobalRefresh():
                after = evaluate_deck(deck, boss)
        her_before = sum(e["damage"] for e in before["damage_log"] if e["slug"] == slug)
        her_after = sum(e["damage"] for e in after["damage_log"] if e["slug"] == slug)
        deck_delta = (after["total_damage"] / before["total_damage"] - 1) * 100
        own_delta = (her_after / her_before - 1) * 100 if her_before else float("nan")
        if abs(deck_delta) > 0.005 or abs(own_delta) > 0.005:
            moved.append(slug)
        print(f"  {slug:<32} own {own_delta:+7.2f}%   deck {deck_delta:+7.2f}%")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
