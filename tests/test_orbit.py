"""Local Orbit Wars protocol, illegal-move counting, and a short episode."""

import pytest

from agents.nearest import NearestAgent
from agents.random_agent import RandomAgent
from orbit.match import agent_seed, aggregate, count_rejected_moves, play_game
from orbit.protocol import load_protocol, protocol_fingerprint


def test_protocol_loads_and_hashes_stably():
    protocol = load_protocol("eval_v01")
    assert protocol["id"] == "eval_v01"
    assert protocol["seeds"] == [42]
    assert protocol["opponent"] == "random"
    assert protocol_fingerprint(protocol) == protocol_fingerprint(load_protocol("eval_v01"))
    with pytest.raises(FileNotFoundError):
        load_protocol("missing")
    with pytest.raises(ValueError):
        load_protocol("../eval_v01")


def test_rejected_moves_follow_interpreter_rules():
    obs = {"player": 0, "planets": [[1, 0, 0, 0, 1, 10, 1], [2, 1, 5, 5, 1, 4, 1]]}
    assert count_rejected_moves(obs, []) == 0
    assert count_rejected_moves(obs, [[1, 0.0, 4], [1, 1.0, 6]]) == 0
    assert count_rejected_moves(obs, [[1, 0.0, 6], [1, 1.0, 6]]) == 1
    assert count_rejected_moves(obs, [[2, 0.0, 1], [9, 0.0, 1], [1, 0.0, 0]]) == 3
    assert count_rejected_moves(obs, "nope") == 1
    assert count_rejected_moves(obs, [[1, 0.0, 1.5]]) == 1


def test_short_game_is_reproducible_and_legal():
    configuration = {"episodeSteps": 8, "actTimeout": 1, "shipSpeed": 6.0, "cometSpeed": 4.0}
    first = play_game(configuration=configuration, seed=42, game_index=0, candidate="nearest", opponent="random")
    second = play_game(configuration=configuration, seed=42, game_index=0, candidate="nearest", opponent="random")
    assert first == second
    assert first.outcome in {"win", "loss", "draw"}
    assert first.candidate_rejected_moves == 0
    assert first.opponent_rejected_moves == 0
    assert first.candidate_timeouts == 0
    summary = aggregate([first])
    assert summary["games"] == 1
    assert summary["wins"] + summary["losses"] + summary["draws"] + summary["invalid_games"] == 1


def test_agent_seeds_differ_by_seat():
    assert agent_seed(42, 0, "candidate") != agent_seed(42, 0, "opponent")
    assert RandomAgent(1)({"player": 0, "planets": []}) == []
    assert NearestAgent()({"player": 0, "planets": [[1, 0, 0, 0, 1, 5, 1]]}) == []
