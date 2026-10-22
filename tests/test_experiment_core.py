"""Offline tests for configurable CV, OOF integrity and isolated experiment runs."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold, TimeSeriesSplit

from utils.artifacts import experiment_run
from utils.validation import (
    build_oof_frame,
    cv_fingerprint,
    load_cv_plan,
    make_cv_plan,
    save_cv_plan,
    save_oof_csv,
)


def plan():
    ids = ["x1", "x2", "x3", "x4"]
    splits = [([2, 3], [0, 1]), ([0, 1], [2, 3])]
    return make_cv_plan("cv_v01", ids, splits)


def test_cv_roundtrip_rejects_reordered_data(tmp_path):
    p = plan()
    path = save_cv_plan(tmp_path / "cv.json", p)
    loaded = load_cv_plan(path, p.row_ids, expected_cv_id="cv_v01")
    assert loaded == p
    assert cv_fingerprint(loaded) == cv_fingerprint(p)
    with pytest.raises(ValueError, match="row_ids"):
        load_cv_plan(path, p.row_ids[::-1])
    with pytest.raises(ValueError, match="CV ID"):
        load_cv_plan(path, p.row_ids, expected_cv_id="cv_v02")
    with pytest.raises(FileExistsError):
        save_cv_plan(path, p)


def test_cv_rejects_invalid_rows_and_overlap():
    with pytest.raises(ValueError, match="unique"):
        make_cv_plan("cv", [1, "1"], [([0], [1])])
    with pytest.raises(ValueError, match="duplicate"):
        make_cv_plan("cv", ["a", "b", "c"], [([0, 0], [1, 2])])
    with pytest.raises(ValueError, match="disjoint"):
        make_cv_plan("cv", ["a", "b"], [([0], [0])])
    with pytest.raises(ValueError, match="multiple"):
        make_cv_plan("cv", ["a", "b", "c"], [([0, 2], [1]), ([0], [1, 2])])
    with pytest.raises(ValueError, match="coverage"):
        make_cv_plan("cv", ["a", "b", "c"], [([0, 2], [1])])
    with pytest.raises(ValueError, match="outside"):
        make_cv_plan("cv", ["a", "b"], [([0], [3])])
    with pytest.raises(TypeError, match="integers"):
        make_cv_plan("cv", ["a", "b"], [([0], [True])])


def test_group_cv_and_group_leakage():
    groups = [0, 0, 1, 1, 2, 2]
    folds = GroupKFold(n_splits=3).split(np.zeros(6), groups=groups)
    p = make_cv_plan("group_v1", list(range(6)), folds, groups=groups)
    assert len(p.splits) == 3
    with pytest.raises(ValueError, match="share a group"):
        make_cv_plan(
            "bad_group", ["a", "b", "c", "d"], [([0, 1], [2, 3])],
            groups=[0, 1, 1, 2], require_complete=False,
        )


def test_time_split_partial_validation(tmp_path):
    ids = list(range(8))
    folds = list(TimeSeriesSplit(n_splits=3).split(ids))
    with pytest.raises(ValueError, match="coverage"):
        make_cv_plan("time", ids, folds, times=ids)
    p = make_cv_plan("time", ids, folds, times=ids, require_complete=False)
    with pytest.raises(ValueError, match="strictly precede"):
        make_cv_plan("bad_time", ids, [([3, 4], [0, 1])], times=ids, require_complete=False)
    with pytest.raises(ValueError, match="coverage"):
        load_cv_plan(save_cv_plan(tmp_path / "splits.json", p), ids)


def test_oof_alignment_multiclass_and_duplicates(tmp_path):
    p = plan()
    frame = build_oof_frame(p, {0: [[0.1, 0.9], [0.3, 0.7]], 1: [[0.8, 0.2], [0.4, 0.6]]})
    assert frame["row_id"].tolist() == ["x1", "x2", "x3", "x4"]
    assert frame["fold"].tolist() == [0, 0, 1, 1]
    assert frame["prediction_0"].tolist() == [0.1, 0.3, 0.8, 0.4]
    path = save_oof_csv(tmp_path / "oof.csv", frame)
    assert pd.read_csv(path)["row_id"].tolist() == ["x1", "x2", "x3", "x4"]
    with pytest.raises(FileExistsError):
        save_oof_csv(path, frame)
    with pytest.raises(ValueError, match="duplicated"):
        save_oof_csv(tmp_path / "invalid.csv", pd.concat([frame, frame.iloc[:1]]))


def test_oof_rejects_shape_nonfinite_and_incomplete():
    p = plan()
    with pytest.raises(ValueError, match="shape"):
        build_oof_frame(p, {0: [0.2], 1: [0.5, 0.7]})
    with pytest.raises(ValueError, match="NaN/Inf"):
        build_oof_frame(p, {0: [float("nan"), 0.1], 1: [0.5, 0.7]})
    with pytest.raises(ValueError, match="keys"):
        build_oof_frame(p, {0: [0.1, 0.2]})
    partial = build_oof_frame(p, {0: [0.1, 0.2]}, allow_partial=True)
    assert len(partial) == 2


def test_unique_run_and_metadata(tmp_path):
    config = {"seed": 123, "api_token": "secret", "nested": {"password": "hidden"}}
    with experiment_run(tmp_path, major="exp001", minor="000", config=config, cv_id="cv_v1", data_version="v1") as run:
        p1 = run.directory
        run.save_metrics({"cv_rmse": np.float64(0.42), "folds": [0.4, 0.44]})
        run.set_wandb(run_id="abc", url="https://wandb.ai/example")
    status = json.loads((p1 / "run.json").read_text())
    assert status["status"] == "completed" and status["cv_id"] == "cv_v1"
    assert status["wandb_run_id"] == "abc"
    assert json.loads((p1 / "metrics.json").read_text())["cv_rmse"] == 0.42
    saved_config = (p1 / "config.yaml").read_text()
    assert "<redacted>" in saved_config and "secret" not in saved_config and "hidden" not in saved_config
    with experiment_run(tmp_path, major="exp001", minor="000", config={"seed": 123}) as r2:
        assert r2.directory != p1


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
        run.save_metrics({"rmse": float("nan")})
