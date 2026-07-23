"""Measure the QUALITY contribution of the expensive from-scratch passes.

Profiling showed the two draft-ignoring `scratch` passes are ~90% of the
complete-draft cost. This asks: what do they BUY? For a given draft, how much
higher is the combined total from the global from-scratch search vs the cheap
warm (draft-seeded) local search? If small, the safety net can be shrunk nearly
for free; if large, it earns its cost — and that decides the optimization path.

Uses the same allocate_decks internals as recommend_from_draft:
  scratch = allocate_decks(roster, draft=None)   -> global optimum (draft-independent)
  warm    = allocate_decks(roster, draft=D)      -> improve FROM draft D (local)
  s       = allocate_decks(drafted25, draft=None)-> best of the 25 drafted (draft-independent)
  w       = allocate_decks(drafted25, draft=D)   -> reshuffle drafted, local
  baseline= draft D scored as-is (best intra-tier ordering per deck)

scratch and s are draft-independent (they ignore the grouping), so they're
computed ONCE; only warm/w/baseline vary per draft scenario.

Scenarios (same 25 units, so scratch/s are shared):
  perfect   : draft = the OPT allocation's own 5 decks
  scrambled : OPT's 25 units, cyclically shuffled among same-tier slots (shape
              preserved -> feasible; pairings wrong -> a realistic user mistake)

MUST stay under `if __name__ == "__main__":` (Windows spawn re-imports workers).

Usage:  python3 scripts/measure_scratch_delta.py [--units N]
"""
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
import app.deck_allocation as da  # noqa: E402


def _nikke(slug, rng):
    # VARIED stats (seeded) to simulate real investment spread — uniform stats
    # make every unit interchangeable, which hides scratch's main value (finding
    # a benched strong unit). atk drives damage most; skill levels add spread.
    atk = rng.uniform(25_000, 95_000)
    lvl = rng.choice([10, 7, 5])
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": atk, "def_": 3_000.0,
        "skill_levels": {"skill1": lvl, "skill2": lvl, "burst": lvl},
    })


def _atk_of(unit):
    # For picking "strong"/"weak" units; UserNikkeState-derived spec keeps atk.
    return getattr(unit, "atk", 0.0) or 0.0


def _combined_baseline(decks, boss):
    return sum(da._best_ordering_summary(deck, boss)["total_damage"] for deck in decks)


def _scramble(decks):
    """Cyclically shift units among same-tier slots across decks: each deck keeps
    its tier counts (shape preserved -> feasible) but unit pairings change."""
    new = [list(d) for d in decks]
    for tier in (1, 2, 3):
        slots = [(di, pos) for di, d in enumerate(decks)
                 for pos, u in enumerate(d) if u.burst_tier == tier]
        units = [decks[di][pos] for di, pos in slots]
        rotated = units[1:] + units[:1]
        for (di, pos), u in zip(slots, rotated):
            new[di][pos] = u
    return new


def _weak_swap(opt_decks, bench, atk):
    """Simulate a draft that benched strong units: in each deck swap its
    strongest unit for the weakest same-tier bench unit (shape preserved).
    Returns the new decks, or None if no feasible swap pool exists."""
    new = [list(d) for d in decks_copy(opt_decks)]
    pool = list(bench)
    for deck in new:
        pos = max(range(len(deck)), key=lambda i: atk[deck[i].slug])
        tier = deck[pos].burst_tier
        cands = [b for b in pool if b.burst_tier == tier and b.slug != deck[pos].slug]
        if not cands:
            continue
        weak = min(cands, key=lambda b: atk[b.slug])
        pool.remove(weak)
        pool.append(deck[pos])
        deck[pos] = weak
    return new


def decks_copy(decks):
    return [list(d) for d in decks]


def _timed(label, fn):
    t0 = time.perf_counter()
    out = fn()
    dt = time.perf_counter() - t0
    total = da._combined(out)
    print(f"  {label:26s} {dt:6.1f}s  combined={total/1e9:.4f}B", flush=True)
    return out, total


def _report(name, draft, drafted, boss, specs, opt, s_best, W):
    print(f"\n[scenario: {name}]", flush=True)
    base = _combined_baseline(draft, boss)
    print(f"  {'baseline (as-is)':26s} {'':6s}  combined={base/1e9:.4f}B", flush=True)
    try:
        _, warm = _timed("warm (full, from draft)", lambda: da.allocate_decks(specs, boss, draft=draft, workers=W))
        _, w = _timed("w (drafted25, from draft)", lambda: da.allocate_decks(drafted, boss, draft=draft, workers=W))
    except da.InfeasibleDraft as e:
        print(f"  INFEASIBLE draft ({e}) - skipping", flush=True)
        return
    recommended = max(opt, warm, s_best)   # recommend_from_draft folds within_draft in
    print(f"  --- deltas ---", flush=True)
    print(f"    scratch vs warm        : {(opt-warm)/warm*100:+.2f}%   (global full search over warm)", flush=True)
    print(f"    s vs w (within tier)   : {(s_best-w)/w*100:+.2f}%   (global-of-25 over w)", flush=True)
    print(f"    warm vs baseline       : {(warm-base)/base*100:+.2f}%   (cheap warm alone)", flush=True)
    print(f"    recommended vs baseline: {(recommended-base)/base*100:+.2f}%   (full pipeline)", flush=True)
    print(f"    recommended vs warm-only: {(recommended-warm)/warm*100:+.2f}%   (EXTRA the scratch passes buy)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--units", type=int, default=78)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    W = "auto"
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # console cp949 can't encode some chars
    except Exception:
        pass

    rng = random.Random(args.seed)
    slugs = [u["slug"] for u in supported_units()][:args.units]
    states = [_nikke(s, rng) for s in slugs]
    atk = {st.character_slug: st.atk for st in states}
    specs, excluded = load_roster(states)
    by_slug = {u.slug: u for u in specs}
    print(f"roster: {len(specs)} units (excluded {len(excluded)}), seed={args.seed}", flush=True)
    boss = BossProfile(element="Water", fight_duration=180.0)

    # --- draft-INDEPENDENT parts ---
    print("\n[fixed] draft-independent searches:", flush=True)
    scratch, opt = _timed("scratch (global, full)", lambda: da.allocate_decks(specs, boss, workers=W))
    opt_decks = [[by_slug[s] for s in d["deck"]] for d in scratch["decks"]]
    drafted = [u for deck in opt_decks for u in deck]
    _, best25 = _timed("s (best of OPT's 25)", lambda: da.allocate_decks(drafted, boss, workers=W))
    bench = [u for u in specs if u.slug not in {u.slug for u in drafted}]

    # perfect & scrambled share OPT's 25 -> reuse best25
    _report("perfect", opt_decks, drafted, boss, specs, opt, best25, W)
    _report("scrambled (rewired pairings)", _scramble(opt_decks), drafted, boss, specs, opt, best25, W)

    # weak-swap uses a DIFFERENT 25 -> its own s
    weak_decks = _weak_swap(opt_decks, bench, atk)
    weak_drafted = [u for deck in weak_decks for u in deck]
    print("\n[fixed] s for weak-swap's 25:", flush=True)
    try:
        _, s_weak = _timed("s (best of weak-swap 25)", lambda: da.allocate_decks(weak_drafted, boss, workers=W))
        _report("weak-swap (benched strong units)", weak_decks, weak_drafted, boss, specs, opt, s_weak, W)
    except da.InfeasibleDraft as e:
        print(f"  weak-swap infeasible ({e}) — skipping", flush=True)


if __name__ == "__main__":
    main()
