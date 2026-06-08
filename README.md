# agent-loop-bound-py

Hard cap on agent loop iterations to prevent runaway agent execution. Raises a
clear exception the moment the limit is hit, so a misbehaving agent (or a buggy
stopping condition) can never spin forever, burn tokens, or hang a process.

- Zero dependencies — pure standard library.
- Tiny surface area: one class, one exception, two helpers.
- Fully type-hinted and ships a `py.typed` marker.

## Install

```bash
pip install agent-loop-bound-py
```

## Quick start

```python
from agent_loop_bound import LoopBound, LoopLimitExceeded

bound = LoopBound(max_iterations=20)

done = False
while not done:
    bound.tick()            # raises LoopLimitExceeded after 20 calls
    result = agent.step()
    done = result.done
```

When the cap is exceeded, `tick()` raises `LoopLimitExceeded`:

```python
try:
    while True:
        bound.tick()
except LoopLimitExceeded as exc:
    print(exc)              # "Agent loop exceeded 20 iteration(s)."
    print(exc.limit)        # 20
```

## Usage

### Context manager (resets the counter on entry)

```python
with LoopBound(max_iterations=10) as bound:
    while not done:
        bound.tick()
        ...
```

### Label loops for clearer errors

```python
bound = LoopBound(max_iterations=5, label="planning_loop")
# On overflow raises: [planning_loop] Agent loop exceeded 5 iteration(s).
```

### Inspect progress

```python
bound.count        # iterations completed so far
bound.remaining    # iterations left before the limit (never negative)
bound.exhausted    # True once the limit has been reached
bound.reset()      # set the counter back to zero (returns self)
```

### Wrap a callable

`wrap` resets the bound and runs the function inside the context manager, so
each call to the wrapped function gets a fresh budget:

```python
bound = LoopBound(max_iterations=100)

@bound.wrap
def run_agent():
    while not done:
        bound.tick()
        ...
```

### Bounded iteration over any iterable

`iter_bounded` is a lazy generator: it pulls at most `max_iterations` items from
the source before raising, so an infinite generator is safe to pass in.

```python
from agent_loop_bound import iter_bounded

for step in iter_bounded(agent_steps(), max_iterations=50, label="stream"):
    process(step)
```

### Convenience factory

```python
from agent_loop_bound import bounded

bound = bounded(20, label="tool_loop")   # same as LoopBound(max_iterations=20, label="tool_loop")
```

## Validation

`max_iterations` must be a non-negative `int`; anything else fails fast at
construction time so a misconfigured guard surfaces immediately rather than
silently never tripping:

```python
LoopBound(max_iterations=-1)     # ValueError
LoopBound(max_iterations=3.5)    # TypeError
LoopBound(max_iterations=True)   # TypeError (bool is rejected on purpose)
LoopBound(max_iterations=0)      # valid: tick() raises on the very first call
```

## API reference

### `class LoopBound(max_iterations: int, label: str = "")`

| Member | Description |
| --- | --- |
| `tick() -> int` | Advance the counter by one and return the current iteration (1-indexed). Raises `LoopLimitExceeded` once the limit is passed. |
| `count -> int` | Iterations completed so far. |
| `remaining -> int` | Iterations left before the limit; clamped to `0`. |
| `exhausted -> bool` | `True` once the limit has been reached. |
| `reset() -> LoopBound` | Reset the counter to zero; returns `self`. |
| `wrap(fn) -> Callable` | Decorator: resets the bound and runs `fn` inside the context manager. |
| `with LoopBound(...) as b:` | Context manager; resets the counter on entry. |

### `class LoopLimitExceeded(Exception)`

Raised when a loop exceeds its limit. Exposes `.limit` (the configured cap) and
`.label` (the loop label, or `""`).

### `bounded(max_iterations: int, label: str = "") -> LoopBound`

Convenience factory for `LoopBound`.

### `iter_bounded(iterable, max_iterations: int, label: str = "")`

Lazily yields items from `iterable`, raising `LoopLimitExceeded` after
`max_iterations` items have been produced.

## Development

Run the test suite with the standard library only (no third-party deps needed):

```bash
python3 -m unittest discover -s tests
```

## License

MIT
