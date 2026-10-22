"""Hydra entry shared by local evaluation experiments."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from hydra.core.config_store import ConfigStore
from hydra.core.hydra_config import HydraConfig

from orbit.match import aggregate, games_payload, play_series
from orbit.protocol import load_protocol, protocol_fingerprint, require_matching_environment
from utils.artifacts import experiment_run
from utils.env import EnvConfig
from utils.logger import get_logger


@dataclass
class ExpConfig:
    protocol: str = "eval_v01"
    agent: str = "random"


@dataclass
class Config:
    env: EnvConfig = field(default_factory=EnvConfig)
    exp: ExpConfig = field(default_factory=ExpConfig)


cs = ConfigStore.instance()
cs.store(name="default", group="env", node=EnvConfig)
cs.store(name="default", group="exp", node=ExpConfig)


def evaluate(cfg: Config) -> None:
    """Run the configured candidate against the configured protocol and save real results."""
    major = Path(sys.argv[0]).resolve().parent.name
    minor = HydraConfig.get().runtime.choices.exp
    protocol = load_protocol(cfg.exp.protocol)
    commit = require_matching_environment(protocol)
    fingerprint = protocol_fingerprint(protocol)
    with experiment_run(
        cfg.env.exp_output_dir,
        major=major,
        minor=minor,
        config=cfg,
        eval_protocol_id=protocol["id"],
        eval_protocol_fingerprint=fingerprint,
        environment_version=commit,
    ) as record:
        logger = get_logger(f"{major}.{minor}.{record.run_id}", record.directory)
        logger.info("Start %s/%s protocol=%s candidate=%s", major, minor, protocol["id"], cfg.exp.agent)
        results = play_series(protocol, cfg.exp.agent)
        metrics = aggregate(results)
        record.save_metrics(metrics)
        games_path = record.directory / "games.json"
        games_path.write_text(
            json.dumps(games_payload(protocol["id"], cfg.exp.agent, results), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "games=%s wins=%s losses=%s draws=%s win_rate=%s",
            metrics["games"],
            metrics["wins"],
            metrics["losses"],
            metrics["draws"],
            metrics["win_rate"],
        )
        logger.info("Saved %s", games_path)
