"""Stopping a search that nobody is waiting for any more.

A recommendation runs one to two minutes across a process pool. Measured: a
client that disconnects mid-request does NOT stop it - the handler is ordinary
sync code and nothing in it looks at the connection, so eight workers run the
search out for a browser tab that closed. That is a Cancel button the user
cannot have, and on a shared server it is other people's CPU.

Cancelling has to reach two places, and they are reached differently:

  * the SEARCH loops, which are plain Python and can simply be asked between
    iterations (`check()`), and
  * the WORKER PROCESSES, which are blocked inside `executor.map` and cannot be
    asked anything - the pool has to be folded from outside (`attach`/`cancel`).

So the token is passed down for the first and pools register themselves for the
second. It carries no engine types, and imports nothing from the engine, so any
layer may hold one.
"""
import threading


class Cancelled(Exception):
    """The search stopped because its caller went away. Not an error: nobody is
    waiting for a response, so a handler catching this has nothing to report."""


class CancelToken:
    """Shared cancel flag, plus the pools to fold when it flips.

    Cancel arrives on the event loop thread while the search runs in a worker
    thread, so every field is touched under a lock.
    """

    def __init__(self):
        self._cancelled = False
        self._pools = []
        self._lock = threading.Lock()

    @property
    def cancelled(self):
        with self._lock:
            return self._cancelled

    def check(self):
        """Raise if cancelled - the search's between-iterations question."""
        if self.cancelled:
            raise Cancelled()

    def attach(self, pool):
        """Register a pool to be folded on cancel (duck-typed: `.cancel()`).

        Raises immediately if the token is ALREADY cancelled, having folded the
        pool first: cancel can land in the window between a pool being built and
        its first batch, and a pool registered after that moment would otherwise
        never be told and would run the whole search out.
        """
        with self._lock:
            if not self._cancelled:
                self._pools.append(pool)
                return
        pool.cancel()
        raise Cancelled()

    def cancel(self):
        """Flip the flag and fold every attached pool. Idempotent."""
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
            pools, self._pools = self._pools, []
        for pool in pools:
            pool.cancel()


class _NeverCancelled:
    """The do-nothing token, so callers take a token unconditionally instead of
    guarding every call site with `if token is not None`."""

    cancelled = False

    def check(self):
        pass

    def attach(self, pool):
        pass

    def cancel(self):
        pass


NEVER = _NeverCancelled()
