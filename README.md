# agent-loop-bound-py

Hard cap on agent loop iterations to prevent runaway agent execution. Raises a clear exception when the limit is hit.

## Install

```bash
pip install agent-loop-bound-py
```

## Usage

```python
from agent_loop_bound import LoopBound, LoopLimitExceeded, bounded, iter_bounded

# Basic usage — call .tick() each iteration
bound = LoopBound(max_iterations=20)
while not done:
    bound.tick()    # raises LoopLimitExceeded after 20 calls
    result = agent.step()
    done = result.done

# Context manager (resets count on entry)
with LoopBound(max_iterations=10) as bound:
    while not done:
        bound.tick()
        ...

# With label for debugging
bound = LoopBound(max_iterations=5, label="planning_loop")
# raises: [planning_loop] Agent loop exceeded 5 iteration(s).

# Check remaining / exhausted
bound.count        # iterations so far
bound.remaining    # iterations left
bound.exhausted    # True if limit reached

# Wrap a callable
@bound.wrap
def run_agent():
    while not done:
        bound.tick()

# Bounded iteration over any iterable
for step in iter_bounded(agent_steps(), max_iterations=50):
    process(step)
```

`max_iterations` must be a non-negative `int`; anything else raises
`TypeError` / `ValueError` at construction so misconfigured guards fail fast.

## License

MIT
