"""Is every timed stack read on the clock its skill text gives it?

WHY: NIKKE's "X, stacks up to N time(s) and lasts for D sec" clause is ONE
timer the whole stack shares - every new stack restarts D for all of them, so
the count climbs toward the cap while consecutive fills stay inside D (the
Raven ruling, Fienn 2026-07-17; re-confirmed on Maiden: Ice Rose in the range,
2026-08-17). Read as N independent D-second timers instead, a counter settles
at "fills per lifetime" and a cap the game reaches every fight is never
touched. `ResourceSpec.lifetime` + `lifetime_refreshes` encode the right rule.

Every affected encoding was corrected on 2026-08-17, so this now reads as a
GUARD: it reports each resource's declared clock beside what the discarded
reading would have made of the same fill timeline, and what that would cost in
damage. A row where the two counts differ is a row where the declaration is
load-bearing - if one ever drifts back, the number here moves.

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
The damage half rewrites what the resources REGISTER rather than any one
buff, because a count is also read by the gates that decide a nuke or a damage
typing - Laplace's Hero Vision has no buff at all, only gates, and measuring
her any other way reads "no effect" for the wrong reason.

WHEN TO RUN: after encoding a resource that pairs a `cap` with a duration, and
whenever the stack semantics are revisited.

    python scripts/audit_stack_lifetime_refresh.py
    python scripts/audit_stack_lifetime_refresh.py --census      # text half only
    python scripts/audit_stack_lifetime_refresh.py --slug modernia --verbose
    # is a resource encoded as permanent really equivalent to refreshing?
    python scripts/audit_stack_lifetime_refresh.py --slug leona \
        --assume-lifetime leona:roar:5

Exit code is 1 when a resource's count would change under the OTHER reading
while its spec has not declared the shared clock - i.e. when an encoding still
owes the question an answer.
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
                        spec.lifetime = a_seconds
                        spec.lifetime_refreshes = True
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


class _PerStackExpiry:
    """Read every timed stack the OLD way - each stack on its own clock -
    by rewriting the semantics the resources registered.

    This is the counterfactual now that the clock belongs to the ResourceSpec
    and every read path honours it: the question is no longer "what would
    refreshing buy" but "what would the discarded reading cost", which is the
    same number from the other side and stays meaningful as a guard."""

    def __init__(self):
        self._original = squad_engine.SquadContext.register_resource

    def __enter__(self):
        original = self._original

        def patched(ctx, slug, spec):
            original(ctx, slug, spec)
            if spec.lifetime is not None:
                ctx.resource_semantics[(slug, spec.name)] = (spec.lifetime, False)

        squad_engine.SquadContext.register_resource = patched
        return self

    def __exit__(self, *exc):
        squad_engine.SquadContext.register_resource = self._original


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
    """The count over the fight under ONE rule.

    The context answers with the resource's registered clock and ignores the
    arguments, which is the point of registering it - so the counterfactual
    column has to swap the registration for the length of the walk rather than
    pass a different lifetime and be quietly overruled."""
    steps = int(FIGHT_DURATION / GRID_STEP) + 1
    key = (slug, name)
    registered = ctx.resource_semantics.get(key)
    ctx.resource_semantics[key] = (lifetime, refreshes)
    try:
        return [ctx.resource_count(slug, name, i * GRID_STEP, cap) for i in range(steps)]
    finally:
        if registered is None:
            ctx.resource_semantics.pop(key, None)
        else:
            ctx.resource_semantics[key] = registered


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

    print(f"{'slug':<30} {'resource':<22} cap  life  refreshes  "
          f"per-stack max/mean  shared max/mean  differs")
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
            if spec.lifetime is None:
                continue
            fills, ctx = watcher.fills_for(slug, spec.name)
            if not fills:
                print(f"{slug:<30} {spec.name:<22} -- no fills in this deck --")
                continue
            plain = _summary(_counts(ctx, slug, spec.name, spec.cap, spec.lifetime, False))
            shared = _summary(_counts(ctx, slug, spec.name, spec.cap, spec.lifetime, True))
            differs = (abs(plain["max"] - shared["max"]) > 1e-9
                       or abs(plain["mean"] - shared["mean"]) > 1e-9)
            if differs and not spec.lifetime_refreshes:
                moved.append(slug)
            print(f"{slug:<30} {spec.name:<22} {spec.cap:>3.0f} {spec.lifetime:>5.1f}  "
                  f"{str(spec.lifetime_refreshes):<9}  "
                  f"{plain['max']:>4.1f}/{plain['mean']:>5.2f}          "
                  f"{shared['max']:>4.1f}/{shared['mean']:>5.2f}      "
                  f"{'YES' if differs else 'no'}")
            if args.verbose:
                times = [round(t, 2) for t, _ in sorted(fills)]
                gaps = [round(b - a, 2) for a, b in zip(times, times[1:])]
                print(f"    fills({len(times)}): {times[:14]}"
                      f"{' ...' if len(times) > 14 else ''}")
                print(f"    gaps: {gaps[:13]}{' ...' if len(gaps) > 13 else ''}")

    print("\nWhat per-stack expiry would cost, every read path (gates included):")
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
            with _PerStackExpiry():
                after = evaluate_deck(deck, boss)
        her_before = sum(e["damage"] for e in before["damage_log"] if e["slug"] == slug)
        her_after = sum(e["damage"] for e in after["damage_log"] if e["slug"] == slug)
        deck_delta = (after["total_damage"] / before["total_damage"] - 1) * 100
        own_delta = (her_after / her_before - 1) * 100 if her_before else float("nan")
        print(f"  {slug:<32} own {own_delta:+7.2f}%   deck {deck_delta:+7.2f}%")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
