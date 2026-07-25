"""The cancellation token the search checks, and the pools it folds.

A recommendation runs for a minute or two across a process pool, so a client
that goes away (Cancel button, page reload) must be able to stop it. Measured
before this existed: a disconnected request kept eight workers busy to
completion.
"""
import pytest

from app.cancellation import CancelToken, Cancelled


class _FakePool:
    def __init__(self):
        self.cancelled = 0

    def cancel(self):
        self.cancelled += 1


def test_a_fresh_token_is_not_cancelled():
    token = CancelToken()
    assert token.cancelled is False
    token.check()  # must not raise


def test_check_raises_once_cancelled():
    token = CancelToken()
    token.cancel()
    assert token.cancelled is True
    with pytest.raises(Cancelled):
        token.check()


def test_cancelling_folds_every_attached_pool():
    """The token is what the request handler holds; the pools are created deep
    inside the search. Attaching them is how a cancel from the event loop
    reaches the worker processes."""
    token = CancelToken()
    first, second = _FakePool(), _FakePool()
    token.attach(first)
    token.attach(second)

    token.cancel()

    assert (first.cancelled, second.cancelled) == (1, 1)


def test_attaching_to_an_already_cancelled_token_folds_that_pool_at_once():
    """Cancel can land in the window between a pool being built and its first
    batch. Without this the new pool would never be told, and its workers would
    run the whole search out."""
    token = CancelToken()
    token.cancel()
    pool = _FakePool()

    with pytest.raises(Cancelled):
        token.attach(pool)

    assert pool.cancelled == 1


def test_cancel_is_idempotent():
    token = CancelToken()
    pool = _FakePool()
    token.attach(pool)

    token.cancel()
    token.cancel()

    assert pool.cancelled == 1


def test_a_none_token_is_usable_without_branching():
    """Every search parameter here is optional; callers should not have to
    guard each check with `if token is not None`."""
    from app.cancellation import NEVER

    assert NEVER.cancelled is False
    NEVER.check()
