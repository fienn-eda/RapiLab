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
from concurrent.futures import ProcessPoolExecutor

from app.deck_search import evaluate_deck

SPAWN_THRESHOLD = 32

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
    deck = [_WORKER_SPECS[s] for s in slugs]
    return evaluate_deck(deck, _WORKER_BOSS)["total_damage"]


def _summarize_slugs(slugs):
    deck = [_WORKER_SPECS[s] for s in slugs]
    return _slim_summary(slugs, evaluate_deck(deck, _WORKER_BOSS))


def resolve_workers(workers):
    """None/0/1 -> serial; "auto" -> leave one core for the event loop."""
    if workers in (None, 0, 1):
        return 1
    if workers == "auto":
        return max(1, (os.cpu_count() or 2) - 1)
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
            lambda deck: evaluate_deck(deck, self._boss)["total_damage"],
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
        if self._workers <= 1 or len(decks) < threshold:
            return [inline_fn(deck) for deck in decks]
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self._workers,
                initializer=_init_worker,
                initargs=(self._specs, self._boss),
            )
        slug_tuples = [tuple(u.slug for u in deck) for deck in decks]
        chunksize = max(1, len(slug_tuples) // (self._workers * 4))
        return list(self._executor.map(worker_fn, slug_tuples, chunksize=chunksize))

    def close(self):
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
