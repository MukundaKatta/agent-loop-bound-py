"""Tests for agent-loop-bound-py."""

import pytest
from agent_loop_bound import LoopBound, LoopLimitExceeded, bounded, iter_bounded


def test_tick_counts():
    bound = LoopBound(max_iterations=5)
    for i in range(1, 6):
        assert bound.tick() == i
    assert bound.count == 5


def test_tick_raises_on_limit():
    bound = LoopBound(max_iterations=3)
    bound.tick()
    bound.tick()
    bound.tick()
    with pytest.raises(LoopLimitExceeded) as exc_info:
        bound.tick()
    assert exc_info.value.limit == 3


def test_loop_limit_exceeded_message():
    bound = LoopBound(max_iterations=2, label="outer_loop")
    bound.tick()
    bound.tick()
    with pytest.raises(LoopLimitExceeded) as exc_info:
        bound.tick()
    assert "outer_loop" in str(exc_info.value)
    assert "2" in str(exc_info.value)


def test_remaining():
    bound = LoopBound(max_iterations=5)
    assert bound.remaining == 5
    bound.tick()
    assert bound.remaining == 4
    bound.tick()
    assert bound.remaining == 3


def test_remaining_at_zero():
    bound = LoopBound(max_iterations=2)
    bound.tick()
    bound.tick()
    assert bound.remaining == 0


def test_exhausted():
    bound = LoopBound(max_iterations=2)
    assert bound.exhausted is False
    bound.tick()
    assert bound.exhausted is False
    bound.tick()
    assert bound.exhausted is True


def test_reset():
    bound = LoopBound(max_iterations=3)
    bound.tick()
    bound.tick()
    bound.reset()
    assert bound.count == 0
    assert bound.remaining == 3
    assert bound.tick() == 1


def test_context_manager_resets():
    bound = LoopBound(max_iterations=3)
    bound.tick()
    with bound:
        assert bound.count == 0
        bound.tick()
        bound.tick()
    assert True  # no error


def test_context_manager_raises_inside():
    bound = LoopBound(max_iterations=2)
    with pytest.raises(LoopLimitExceeded):
        with bound:
            bound.tick()
            bound.tick()
            bound.tick()  # raises


def test_wrap_decorator():
    bound = LoopBound(max_iterations=5)

    @bound.wrap
    def run():
        for _ in range(5):
            bound.tick()
        return "done"

    assert run() == "done"
    # Second call resets
    assert run() == "done"


def test_wrap_raises_on_exceed():
    bound = LoopBound(max_iterations=2)

    @bound.wrap
    def run():
        for _ in range(10):
            bound.tick()

    with pytest.raises(LoopLimitExceeded):
        run()


def test_bounded_factory():
    b = bounded(10, label="test")
    assert b.max_iterations == 10
    assert b.label == "test"
    assert b.count == 0


def test_iter_bounded_normal():
    items = list(iter_bounded(range(5), max_iterations=10))
    assert items == [0, 1, 2, 3, 4]


def test_iter_bounded_exact_limit():
    items = list(iter_bounded(range(5), max_iterations=5))
    assert items == [0, 1, 2, 3, 4]


def test_iter_bounded_raises():
    with pytest.raises(LoopLimitExceeded):
        list(iter_bounded(range(10), max_iterations=3))


def test_iter_bounded_label_in_error():
    with pytest.raises(LoopLimitExceeded) as exc_info:
        list(iter_bounded(range(100), max_iterations=2, label="gen_loop"))
    assert "gen_loop" in str(exc_info.value)


def test_no_label_in_error():
    bound = LoopBound(max_iterations=1)
    bound.tick()
    with pytest.raises(LoopLimitExceeded) as exc_info:
        bound.tick()
    exc = exc_info.value
    assert exc.label == ""
    assert exc.limit == 1


def test_zero_max_iterations_raises_on_first_tick():
    bound = LoopBound(max_iterations=0)
    assert bound.exhausted is True
    assert bound.remaining == 0
    with pytest.raises(LoopLimitExceeded):
        bound.tick()


def test_negative_max_iterations_rejected():
    with pytest.raises(ValueError):
        LoopBound(max_iterations=-1)


def test_non_int_max_iterations_rejected():
    with pytest.raises(TypeError):
        LoopBound(max_iterations=3.5)


def test_bool_max_iterations_rejected():
    # bool is a subclass of int; passing one is a programmer error.
    with pytest.raises(TypeError):
        LoopBound(max_iterations=True)


def test_bounded_factory_validates():
    with pytest.raises(ValueError):
        bounded(-5)


def test_iter_bounded_is_lazy():
    # iter_bounded should not consume the whole iterable before raising.
    consumed = []

    def gen():
        for i in range(100):
            consumed.append(i)
            yield i

    with pytest.raises(LoopLimitExceeded):
        list(iter_bounded(gen(), max_iterations=3))
    # Only a bounded prefix of the source should have been pulled.
    assert consumed == [0, 1, 2, 3]
