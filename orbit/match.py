"""Play Orbit Wars episodes and aggregate local results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from kaggle_environments import make

from agents.nearest import NearestAgent
from agents.random_agent import RandomAgent
from orbit.protocol import require_matching_environment

_TERMINAL_STATUSES = ("TIMEOUT", "ERROR", "INVALID")


@dataclass(frozen=True)
class GameResult:
    seed: int
    game_index: int
    outcome: str
    candidate_reward: int | None
    opponent_reward: int | None
    candidate_ships: int
    opponent_ships: int
    final_step: int
    candidate_rejected_moves: int
    opponent_rejected_moves: int
    candidate_timeouts: int
    opponent_timeouts: int
    candidate_errors: int
    opponent_errors: int
    candidate_invalid_statuses: int
    opponent_invalid_statuses: int


def agent_seed(episode_seed: int, game_index: int, role: str) -> int:
    """Derive an independent RNG seed for one seat of one episode."""
    if role not in {"candidate", "opponent"}:
        raise ValueError(f"unknown role: {role}")
    role_bit = 0 if role == "candidate" else 1
    return (episode_seed * 1_000_003 + game_index * 2 + role_bit) % (2**31 - 1)


def make_agent(name: str, seed: int) -> Any:
    if name == "random":
        return RandomAgent(seed)
    if name == "nearest":
        return NearestAgent()
    raise ValueError(f"unknown agent: {name}")


def count_rejected_moves(obs: Any, action: Any) -> int:
    """Count moves the Orbit Wars interpreter would skip.

    Schema failures (non-list actions, wrong types) are included. A schema-valid
    move is rejected when the source is missing, not owned, or cannot pay the
    ship count after earlier moves from the same planet in this action.
    """
    player = obs.get("player")
    garrison = {int(planet[0]): int(planet[5]) for planet in obs.get("planets", [])}
    owner = {int(planet[0]): planet[1] for planet in obs.get("planets", [])}
    if not isinstance(action, list):
        return 1
    rejected = 0
    for move in action:
        if not isinstance(move, (list, tuple)) or len(move) != 3:
            rejected += 1
            continue
        source, _angle, ships = move
        if (
            isinstance(ships, bool)
            or not isinstance(ships, int)
            or isinstance(source, bool)
            or not isinstance(source, int)
        ):
            rejected += 1
            continue
        available = garrison.get(source)
        if available is None or owner.get(source) != player or ships <= 0 or available < ships:
            rejected += 1
            continue
        garrison[source] = available - ships
    return rejected


def play_series(protocol: dict[str, Any], candidate: str) -> list[GameResult]:
    """Play every seed in the protocol. The candidate is not part of the protocol."""
    if candidate not in {"random", "nearest"}:
        raise ValueError(f"unknown candidate: {candidate}")
    require_matching_environment(protocol)
    results: list[GameResult] = []
    for seed in protocol["seeds"]:
        for game_index in range(protocol["games_per_seed"]):
            results.append(
                play_game(
                    configuration=protocol["configuration"],
                    seed=seed,
                    game_index=game_index,
                    candidate=candidate,
                    opponent=protocol["opponent"],
                )
            )
    return results


def play_game(
    *,
    configuration: dict[str, Any],
    seed: int,
    game_index: int,
    candidate: str,
    opponent: str,
) -> GameResult:
    rejected = [[], []]
    agents = [
        _instrument(make_agent(candidate, agent_seed(seed, game_index, "candidate")), rejected[0]),
        _instrument(make_agent(opponent, agent_seed(seed, game_index, "opponent")), rejected[1]),
    ]
    env = make("orbit_wars", configuration={**configuration, "seed": seed}, debug=False)
    steps = env.run(agents)
    final = steps[-1]
    rewards = [_reward(state) for state in final]
    statuses = [_status_counts(steps, player) for player in (0, 1)]
    observation = final[0].observation
    return GameResult(
        seed=seed,
        game_index=game_index,
        outcome=_outcome(rewards),
        candidate_reward=rewards[0],
        opponent_reward=rewards[1],
        candidate_ships=_total_ships(observation, 0),
        opponent_ships=_total_ships(observation, 1),
        final_step=int(observation.step),
        candidate_rejected_moves=sum(rejected[0]),
        opponent_rejected_moves=sum(rejected[1]),
        candidate_timeouts=statuses[0]["TIMEOUT"],
        opponent_timeouts=statuses[1]["TIMEOUT"],
        candidate_errors=statuses[0]["ERROR"],
        opponent_errors=statuses[1]["ERROR"],
        candidate_invalid_statuses=statuses[0]["INVALID"],
        opponent_invalid_statuses=statuses[1]["INVALID"],
    )


def aggregate(results: list[GameResult]) -> dict[str, float]:
    """Numeric summary for metrics.json. Official skill rating is not included."""
    if not results:
        raise ValueError("cannot aggregate an empty result list")
    games = len(results)
    wins = sum(result.outcome == "win" for result in results)
    losses = sum(result.outcome == "loss" for result in results)
    draws = sum(result.outcome == "draw" for result in results)
    invalid = sum(result.outcome == "invalid" for result in results)
    return {
        "games": float(games),
        "wins": float(wins),
        "losses": float(losses),
        "draws": float(draws),
        "invalid_games": float(invalid),
        "win_rate": wins / games,
        "mean_candidate_ships": _mean(result.candidate_ships for result in results),
        "mean_opponent_ships": _mean(result.opponent_ships for result in results),
        "mean_ship_difference": _mean(result.candidate_ships - result.opponent_ships for result in results),
        "mean_final_step": _mean(result.final_step for result in results),
        "candidate_rejected_moves": float(sum(result.candidate_rejected_moves for result in results)),
        "opponent_rejected_moves": float(sum(result.opponent_rejected_moves for result in results)),
        "candidate_timeouts": float(sum(result.candidate_timeouts for result in results)),
        "opponent_timeouts": float(sum(result.opponent_timeouts for result in results)),
        "candidate_errors": float(sum(result.candidate_errors for result in results)),
        "opponent_errors": float(sum(result.opponent_errors for result in results)),
        "candidate_invalid_statuses": float(sum(result.candidate_invalid_statuses for result in results)),
        "opponent_invalid_statuses": float(sum(result.opponent_invalid_statuses for result in results)),
    }


def games_payload(protocol_id: str, candidate: str, results: list[GameResult]) -> dict[str, Any]:
    return {
        "protocol_id": protocol_id,
        "candidate": candidate,
        "games": [asdict(result) for result in results],
    }


def _instrument(agent: Any, sink: list[int]) -> Any:
    def wrapped(obs: Any, config: Any = None) -> Any:
        action = agent(obs, config)
        sink.append(count_rejected_moves(obs, action))
        return action

    return wrapped


def _reward(state: Any) -> int | None:
    reward = state.reward
    if reward is None:
        return None
    return int(reward)


def _outcome(rewards: list[int | None]) -> str:
    """Map environment rewards to a candidate result.

    On a tied ship total the interpreter assigns reward 1 to every tied player.
    That result is a draw, not a win for the candidate.
    """
    if any(reward is None for reward in rewards):
        return "invalid"
    candidate, opponent = rewards
    if candidate == opponent:
        return "draw"
    if candidate is not None and opponent is not None and candidate > opponent:
        return "win"
    return "loss"


def _total_ships(observation: Any, player: int) -> int:
    total = 0
    for planet in observation.planets:
        if planet[1] == player:
            total += int(planet[5])
    for fleet in observation.fleets:
        if fleet[1] == player:
            total += int(fleet[6])
    return total


def _status_counts(steps: list[Any], player: int) -> dict[str, int]:
    """Count entries into TIMEOUT, ERROR, or INVALID. A stuck status counts once."""
    counts = {status: 0 for status in _TERMINAL_STATUSES}
    previous = None
    for step in steps:
        status = step[player].status
        if status != previous and status in counts:
            counts[status] += 1
        previous = status
    return counts


def _mean(values: Any) -> float:
    data = list(values)
    return sum(data) / len(data)
