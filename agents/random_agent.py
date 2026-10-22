"""Seeded random policy matching the environment's built-in random agent."""

from __future__ import annotations

import math
import random
from typing import Any

# Launch only when half the garrison is at least this many ships.
# Same threshold as kaggle_environments.envs.orbit_wars.orbit_wars.random_agent.
MIN_LAUNCH_SHIPS = 20


class RandomAgent:
    """Send half the garrison of each owned planet in a random direction.

    The angle comes from this instance's RNG, so a seed fixes the actions
    given the same observations. The map seed alone does not.
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def __call__(self, obs: Any, config: Any = None) -> list[list[int | float]]:
        del config
        moves: list[list[int | float]] = []
        player = obs.get("player", 0)
        for planet in obs.get("planets", []):
            owner = planet[1]
            ships = int(planet[5])
            if owner != player or ships <= 0:
                continue
            launch = ships // 2
            if launch < MIN_LAUNCH_SHIPS:
                continue
            angle = self._rng.uniform(0, 2 * math.pi)
            moves.append([int(planet[0]), angle, launch])
        return moves
