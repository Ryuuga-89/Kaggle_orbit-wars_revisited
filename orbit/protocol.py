"""Load and fingerprint a local Orbit Wars evaluation protocol."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import yaml

_PROTOCOL_DIR = Path(__file__).parent / "protocols"
_KNOWN_AGENTS = frozenset({"random", "nearest"})


def protocol_path(protocol_id: str) -> Path:
    if not protocol_id or Path(protocol_id).name != protocol_id:
        raise ValueError(f"invalid protocol id: {protocol_id!r}")
    path = _PROTOCOL_DIR / f"{protocol_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"evaluation protocol not found: {path}")
    return path


def load_protocol(protocol_id: str) -> dict[str, Any]:
    """Load a protocol YAML and reject a file whose id does not match its name."""
    path = protocol_path(protocol_id)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"protocol must be a mapping: {path}")
    protocol = _validate(loaded)
    if protocol["id"] != protocol_id:
        raise ValueError(f"protocol id {protocol['id']!r} does not match file {protocol_id!r}")
    return protocol


def protocol_fingerprint(protocol: dict[str, Any]) -> str:
    """Hash the protocol contents so a changed seed list or opponent is visible."""
    payload = json.dumps(protocol, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def installed_environment_commit() -> str:
    """Return the git commit of the installed kaggle-environments package."""
    direct = importlib.metadata.distribution("kaggle-environments").read_text("direct_url.json")
    if not direct:
        raise RuntimeError(
            "kaggle-environments has no direct_url.json. "
            "Install the git revision named by the evaluation protocol. "
            "The PyPI wheel of 1.33.2 does not include orbit_wars."
        )
    commit = json.loads(direct).get("vcs_info", {}).get("commit_id")
    if not isinstance(commit, str) or not commit:
        raise RuntimeError("kaggle-environments direct_url.json has no vcs commit id")
    return commit


def require_matching_environment(protocol: dict[str, Any]) -> str:
    """Fail when the installed simulator is not the protocol's commit."""
    installed = installed_environment_commit()
    expected = protocol["environment_commit"]
    if installed != expected:
        raise RuntimeError(
            f"installed kaggle-environments commit {installed} does not match "
            f"protocol {protocol['id']} commit {expected}"
        )
    return installed


def _validate(raw: dict[str, Any]) -> dict[str, Any]:
    required = (
        "id",
        "environment",
        "environment_commit",
        "players",
        "seeds",
        "games_per_seed",
        "opponent",
        "configuration",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"protocol is missing fields: {', '.join(missing)}")
    if raw["environment"] != "orbit_wars":
        raise ValueError(f"unsupported environment: {raw['environment']!r}")
    if not isinstance(raw["environment_commit"], str) or len(raw["environment_commit"]) < 7:
        raise ValueError("environment_commit must be a git commit id")
    if raw["players"] != 2:
        raise ValueError("eval protocols currently support exactly 2 players")
    seeds = raw["seeds"]
    if not isinstance(seeds, list) or not seeds or not all(isinstance(seed, int) and seed >= 0 for seed in seeds):
        raise ValueError("seeds must be a non-empty list of non-negative integers")
    games = raw["games_per_seed"]
    if not isinstance(games, int) or games < 1:
        raise ValueError("games_per_seed must be a positive integer")
    if raw["opponent"] not in _KNOWN_AGENTS:
        raise ValueError(f"unknown opponent: {raw['opponent']!r}")
    configuration = raw["configuration"]
    if not isinstance(configuration, dict):
        raise TypeError("configuration must be a mapping")
    if "seed" in configuration:
        raise ValueError("put seeds in the protocol seed list, not in configuration")
    return {
        "id": str(raw["id"]),
        "environment": "orbit_wars",
        "environment_commit": raw["environment_commit"],
        "players": 2,
        "seeds": list(seeds),
        "games_per_seed": games,
        "opponent": raw["opponent"],
        "configuration": dict(configuration),
    }
