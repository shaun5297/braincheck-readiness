from __future__ import annotations

import random


def stimulus_sequence(*, count: int = 180, seed: int = 0) -> tuple[str, ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    values = [str(rng.randint(1, 9)) for _ in range(count)]
    target_count = max(1, round(count / 9))
    target_indexes = rng.sample(range(count), target_count)
    for index in target_indexes:
        values[index] = "3"
    return tuple(values)


def should_respond(stimulus: str) -> bool:
    return stimulus != "3"

