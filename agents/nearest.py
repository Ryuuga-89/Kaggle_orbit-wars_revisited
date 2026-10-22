"""Nearest-planet heuristic from the Orbit Wars getting-started example."""

from __future__ import annotations

import math
from typing import Any


class NearestAgent:
    """From each owned planet, send exactly enough ships to capture the nearest other planet.

    The aim uses the target's current coordinates. It does not predict orbits,
    comets, or the sun. A planet that cannot afford the garrison-plus-one does
    not launch.
    """

    def __call__(self, obs: Any, config: Any = None) -> list[list[int | float]]:
        del config
        player = obs.get("player", 0)
        planets = list(obs.get("planets", []))
        mine = [planet for planet in planets if planet[1] == player]
        targets = [planet for planet in planets if planet[1] != player]
        if not targets:
            return []
        moves: list[list[int | float]] = []
        for source in mine:
            target = min(targets, key=lambda other: math.hypot(source[2] - other[2], source[3] - other[3]))
            needed = int(target[5]) + 1
            if int(source[5]) < needed or needed <= 0:
                continue
            angle = math.atan2(target[3] - source[3], target[2] - source[2])
            moves.append([int(source[0]), angle, needed])
        return moves
