"""Process-pool deck evaluation for the budget-heavy search phases (Phase 5
throughput lever - ProcessPool parallelism, Fienn 2026-07-17).

evaluate_deck is a pure ~100 ms function of (ordered specs, boss); the search
layers issue map-shaped batches of independent calls. SimPool fans a batch out
to a ProcessPoolExecutor. Workers are initialized ONCE with the roster's specs
and the boss (spawn pickles initargs a single time), so each task travels as a
tuple of slugs - not as repeatedly re-pickled spec objects.

Small batches never spawn: batches below spawn_threshold run inline, so tiny
rosters, tests, and API smoke requests pay zero pool cost. The executor is
created lazily on the first big batch and reused until close().

Script callers beware: Windows spawn re-imports the main module in every
worker, so a plain script that reaches a SimPool at module top level forks
bombs itself - keep the pool-reaching code under `if __name__ == "__main__":`
(server/pytest contexts are unaffected; their main module isn't the caller).
"""
import os
from concurrent.futures import CancelledError, ProcessPoolExecutor

from app.cancellation import Cancelled
from app.deck_search import evaluate_deck, ranking_damage

SPAWN_THRESHOLD = 32

# Ceiling on how much work one dispatch hands a worker. Chunking exists to
# amortize dispatch over a ~100 ms simulation, and eight of them (~0.8 s) is
# already far more than enough for that - but a chunk, once started, is what
# cancel CANNOT drop. Uncapped, a big batch handed each worker ~60 decks and a
# cancelled run kept them busy 7.8 s; capped, 1.5 s. Measured free: the
# real-roster three-seat draft ran 83.4/83.3 s capped vs 84.1/84.1 s uncapped,
# same damage (scripts/measure_thin_draft.py).
MAX_CHUNK = 8

_WORKER_SPECS = None
_WORKER_BOSS = None


def _init_worker(specs_by_slug, boss):
    global _WORKER_SPECS, _WORKER_BOSS
    _WORKER_SPECS = specs_by_slug
    _WORKER_BOSS = boss


def _slim_summary(deck_slugs, result):
    burst = sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    normal = sum(e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack")
    return {"deck": list(deck_slugs), "total_damage": result["total_damage"],
            "burst_damage": burst, "normal_attack_damage": normal}


def _score_slugs(slugs):
    # `score_many` only ever yields a number to compare decks BY, so it is a
    # ranking path by construction and takes the pass cap. `_summarize_slugs`
    # below is the report path and must not.
    deck = [_WORKER_SPECS[s] for s in slugs]
    return ranking_damage(deck, _WORKER_BOSS)


def _summarize_slugs(slugs):
    deck = [_WORKER_SPECS[s] for s in slugs]
    return _slim_summary(slugs, evaluate_deck(deck, _WORKER_BOSS))


def resolve_workers(workers):
    """None/0/1 -> serial; "auto" -> half the machine, never more.

    This runs on the player's own device, not a server we own, so a
    recommendation must not take the whole machine for a minute. Half is not a
    compromise on results: measured on a 78-unit roster, 8 workers and 15 reach
    exactly the same allocation damage - the swap hill-climb converges either
    way, and the extra cores only shave wall clock (80s vs 73s). Below that the
    phase degrades gently rather than breaking (4 workers keep 99.6% of the
    converged damage, 2 keep 98.3%). See docs/decisions.md.
    """
    if workers in (None, 0, 1):
        return 1
    if workers == "auto":
        return max(1, (os.cpu_count() or 2) // 2)
    return int(workers)


class SimPool:
    """Batched deck evaluation: inline below spawn_threshold, pooled above."""

    def __init__(self, roster, boss, workers=None, spawn_threshold=None):
        self._specs = {u.slug: u for u in roster}
        self._boss = boss
        self._workers = resolve_workers(workers)
        self._spawn_threshold = spawn_threshold
        self._executor = None

    def score_many(self, decks):
        return self._map(
            _score_slugs,
            lambda deck: ranking_damage(deck, self._boss),
            decks,
        )

    def summarize_many(self, decks):
        return self._map(
            _summarize_slugs,
            lambda deck: _slim_summary([u.slug for u in deck], evaluate_deck(deck, self._boss)),
            decks,
        )

    def _map(self, worker_fn, inline_fn, decks):
        threshold = self._spawn_threshold if self._spawn_threshold is not None else SPAWN_THRESHOLD
        # The threshold guards STARTING the executor - spawning processes and
        # pickling the roster into each. Once one is running a task costs a
        # five-slug tuple, so a batch under the threshold is still worth fanning
        # out; holding it back only leaves the workers idle. The swap
        # hill-climb lives on this: its deck-to-deck candidates arrive ~22 at a
        # time and were serial for exactly this reason.
        if self._workers <= 1 or (len(decks) < threshold and self._executor is None):
            return [inline_fn(deck) for deck in decks]
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self._workers,
                initializer=_init_worker,
                initargs=(self._specs, self._boss),
            )
        slug_tuples = [tuple(u.slug for u in deck) for deck in decks]
        chunksize = max(1, min(len(slug_tuples) // (self._workers * 4), MAX_CHUNK))
        # Bound to a local: cancel() clears self._executor from another thread,
        # and a batch already in flight has to keep talking to its own pool.
        executor = self._executor
        try:
            return list(executor.map(worker_fn, slug_tuples, chunksize=chunksize))
        except CancelledError:
            # cancel() dropped the queued futures; consuming the iterator is how
            # this thread finds out. Report it as the domain event the search
            # understands rather than a concurrent.futures internal.
            raise Cancelled()

    def cancel(self):
        """Fold the pool now, dropping work nobody is waiting for.

        The workers are blocked inside evaluate_deck and cannot be asked to
        stop, so the queue is dropped instead: whatever is mid-simulation
        finishes (~100 ms each) and everything behind it is cancelled. Never
        waits - the caller is cancelling BECAUSE the batch is long.
        """
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    def close(self):
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
