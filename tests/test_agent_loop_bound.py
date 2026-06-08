"""Tests for agent-loop-bound-py.

These tests use only the Python standard library (``unittest``) so they can be
run with::

    python3 -m unittest discover -s tests

without installing any third-party dependencies.
"""

import os
import sys
import unittest

# Make ``src/`` importable when running the tests directly from a checkout
# (i.e. without installing the package first).
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"),
)

from agent_loop_bound import (  # noqa: E402
    LoopBound,
    LoopLimitExceeded,
    bounded,
    iter_bounded,
)


class TickTests(unittest.TestCase):
    def test_tick_counts(self):
        bound = LoopBound(max_iterations=5)
        for i in range(1, 6):
            self.assertEqual(bound.tick(), i)
        self.assertEqual(bound.count, 5)

    def test_tick_raises_on_limit(self):
        bound = LoopBound(max_iterations=3)
        bound.tick()
        bound.tick()
        bound.tick()
        with self.assertRaises(LoopLimitExceeded) as ctx:
            bound.tick()
        self.assertEqual(ctx.exception.limit, 3)

    def test_tick_returns_one_indexed_value(self):
        bound = LoopBound(max_iterations=2)
        self.assertEqual(bound.tick(), 1)
        self.assertEqual(bound.tick(), 2)


class ErrorMessageTests(unittest.TestCase):
    def test_loop_limit_exceeded_message(self):
        bound = LoopBound(max_iterations=2, label="outer_loop")
        bound.tick()
        bound.tick()
        with self.assertRaises(LoopLimitExceeded) as ctx:
            bound.tick()
        self.assertIn("outer_loop", str(ctx.exception))
        self.assertIn("2", str(ctx.exception))

    def test_no_label_in_error(self):
        bound = LoopBound(max_iterations=1)
        bound.tick()
        with self.assertRaises(LoopLimitExceeded) as ctx:
            bound.tick()
        exc = ctx.exception
        self.assertEqual(exc.label, "")
        self.assertEqual(exc.limit, 1)
        # With no label there should be no stray bracket prefix.
        self.assertFalse(str(exc).startswith("["))

    def test_exception_is_subclass_of_exception(self):
        self.assertTrue(issubclass(LoopLimitExceeded, Exception))


class RemainingAndExhaustedTests(unittest.TestCase):
    def test_remaining(self):
        bound = LoopBound(max_iterations=5)
        self.assertEqual(bound.remaining, 5)
        bound.tick()
        self.assertEqual(bound.remaining, 4)
        bound.tick()
        self.assertEqual(bound.remaining, 3)

    def test_remaining_at_zero(self):
        bound = LoopBound(max_iterations=2)
        bound.tick()
        bound.tick()
        self.assertEqual(bound.remaining, 0)

    def test_remaining_never_negative(self):
        # Even after the limit has been blown, ``remaining`` clamps at 0.
        bound = LoopBound(max_iterations=1)
        bound.tick()
        with self.assertRaises(LoopLimitExceeded):
            bound.tick()
        self.assertEqual(bound.remaining, 0)

    def test_exhausted(self):
        bound = LoopBound(max_iterations=2)
        self.assertFalse(bound.exhausted)
        bound.tick()
        self.assertFalse(bound.exhausted)
        bound.tick()
        self.assertTrue(bound.exhausted)


class ResetTests(unittest.TestCase):
    def test_reset(self):
        bound = LoopBound(max_iterations=3)
        bound.tick()
        bound.tick()
        bound.reset()
        self.assertEqual(bound.count, 0)
        self.assertEqual(bound.remaining, 3)
        self.assertEqual(bound.tick(), 1)

    def test_reset_returns_self(self):
        bound = LoopBound(max_iterations=3)
        bound.tick()
        self.assertIs(bound.reset(), bound)


class ContextManagerTests(unittest.TestCase):
    def test_context_manager_resets(self):
        bound = LoopBound(max_iterations=3)
        bound.tick()
        with bound as ctx_bound:
            self.assertIs(ctx_bound, bound)
            self.assertEqual(bound.count, 0)
            bound.tick()
            bound.tick()

    def test_context_manager_raises_inside(self):
        bound = LoopBound(max_iterations=2)
        with self.assertRaises(LoopLimitExceeded):
            with bound:
                bound.tick()
                bound.tick()
                bound.tick()  # raises


class WrapTests(unittest.TestCase):
    def test_wrap_decorator(self):
        bound = LoopBound(max_iterations=5)

        @bound.wrap
        def run():
            for _ in range(5):
                bound.tick()
            return "done"

        self.assertEqual(run(), "done")
        # Second call resets the counter, so it succeeds again.
        self.assertEqual(run(), "done")

    def test_wrap_raises_on_exceed(self):
        bound = LoopBound(max_iterations=2)

        @bound.wrap
        def run():
            for _ in range(10):
                bound.tick()

        with self.assertRaises(LoopLimitExceeded):
            run()

    def test_wrap_preserves_metadata(self):
        bound = LoopBound(max_iterations=3)

        @bound.wrap
        def run():
            """My docstring."""
            return 42

        self.assertEqual(run.__name__, "run")
        self.assertEqual(run.__doc__, "My docstring.")

    def test_wrap_forwards_arguments(self):
        bound = LoopBound(max_iterations=10)

        @bound.wrap
        def add(a, b, c=0):
            bound.tick()
            return a + b + c

        self.assertEqual(add(1, 2, c=3), 6)


class FactoryTests(unittest.TestCase):
    def test_bounded_factory(self):
        b = bounded(10, label="test")
        self.assertEqual(b.max_iterations, 10)
        self.assertEqual(b.label, "test")
        self.assertEqual(b.count, 0)

    def test_bounded_factory_validates(self):
        with self.assertRaises(ValueError):
            bounded(-5)


class IterBoundedTests(unittest.TestCase):
    def test_iter_bounded_normal(self):
        items = list(iter_bounded(range(5), max_iterations=10))
        self.assertEqual(items, [0, 1, 2, 3, 4])

    def test_iter_bounded_exact_limit(self):
        items = list(iter_bounded(range(5), max_iterations=5))
        self.assertEqual(items, [0, 1, 2, 3, 4])

    def test_iter_bounded_raises(self):
        with self.assertRaises(LoopLimitExceeded):
            list(iter_bounded(range(10), max_iterations=3))

    def test_iter_bounded_label_in_error(self):
        with self.assertRaises(LoopLimitExceeded) as ctx:
            list(iter_bounded(range(100), max_iterations=2, label="gen_loop"))
        self.assertIn("gen_loop", str(ctx.exception))

    def test_iter_bounded_is_lazy(self):
        # iter_bounded should not consume the whole iterable before raising.
        consumed = []

        def gen():
            for i in range(100):
                consumed.append(i)
                yield i

        with self.assertRaises(LoopLimitExceeded):
            list(iter_bounded(gen(), max_iterations=3))
        # Only a bounded prefix of the source should have been pulled.
        self.assertEqual(consumed, [0, 1, 2, 3])

    def test_iter_bounded_empty_iterable(self):
        self.assertEqual(list(iter_bounded([], max_iterations=5)), [])


class ValidationTests(unittest.TestCase):
    def test_zero_max_iterations_raises_on_first_tick(self):
        bound = LoopBound(max_iterations=0)
        self.assertTrue(bound.exhausted)
        self.assertEqual(bound.remaining, 0)
        with self.assertRaises(LoopLimitExceeded):
            bound.tick()

    def test_negative_max_iterations_rejected(self):
        with self.assertRaises(ValueError):
            LoopBound(max_iterations=-1)

    def test_non_int_max_iterations_rejected(self):
        with self.assertRaises(TypeError):
            LoopBound(max_iterations=3.5)

    def test_bool_max_iterations_rejected(self):
        # bool is a subclass of int; passing one is almost always a bug.
        with self.assertRaises(TypeError):
            LoopBound(max_iterations=True)

    def test_string_max_iterations_rejected(self):
        with self.assertRaises(TypeError):
            LoopBound(max_iterations="10")


if __name__ == "__main__":
    unittest.main()
