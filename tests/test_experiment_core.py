"""Offline tests for isolated experiment run directories."""

import json

import numpy as np
import pytest

from utils.artifacts import experiment_run


def test_unique_run_and_metadata(tmp_path):
    config = {"seed": 123, "api_token": "secret", "nested": {"password": "hidden"}}
    with experiment_run(
        tmp_path,
        major="exp001",
        minor="000",
        config=config,
        eval_protocol_id="eval_v01",
        eval_protocol_fingerprint="abc",
        environment_version="deadbeef",
    ) as run:
        directory = run.directory
        run.save_metrics({"win_rate": np.float64(0.5), "games": [1]})
        run.set_wandb(run_id="abc", url="https://wandb.ai/example")
    status = json.loads((directory / "run.json").read_text())
    assert status["status"] == "completed"
    assert status["schema_version"] == 2
    assert status["eval_protocol_id"] == "eval_v01"
    assert status["eval_protocol_fingerprint"] == "abc"
    assert status["environment_version"] == "deadbeef"
    assert status["wandb_run_id"] == "abc"
    assert json.loads((directory / "metrics.json").read_text())["win_rate"] == 0.5
    saved_config = (directory / "config.yaml").read_text()
    assert "<redacted>" in saved_config and "secret" not in saved_config and "hidden" not in saved_config
    with experiment_run(tmp_path, major="exp001", minor="000", config={"seed": 123}) as other:
        assert other.directory != directory


def test_failure_status_and_invalid_metadata(tmp_path):
    with pytest.raises(ZeroDivisionError), experiment_run(
        tmp_path, major="exp001", minor="001", config={"seed": 5}
    ) as run:
        failed_path = run.directory
        raise ZeroDivisionError("intentional failure")
    assert json.loads((failed_path / "run.json").read_text())["status"] == "failed"
    with pytest.raises(ValueError, match="path components"), experiment_run(
        tmp_path, major="../evil", minor="001", config={}
    ):
        pass
    with pytest.raises(ValueError, match="finite"), experiment_run(
        tmp_path, major="exp001", minor="003", config={}
    ) as run:
        run.save_metrics({"win_rate": float("nan")})
