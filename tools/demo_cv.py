"""CPU-only smoke demo for split manifest, OOF alignment and run metadata."""

from pathlib import Path

import numpy as np
from sklearn.model_selection import KFold

from utils.artifacts import experiment_run
from utils.validation import build_oof_frame, cv_fingerprint, load_cv_plan, make_cv_plan, save_cv_plan, save_oof_csv


def main() -> None:
    ids = [f"row-{i:03d}" for i in range(12)]
    y = np.arange(12, dtype=float)
    plan = make_cv_plan("demo_v01", ids, KFold(n_splits=3, shuffle=True, random_state=42).split(y))
    cv_path = Path("output/cv/demo_v01.json")
    if cv_path.exists():
        plan = load_cv_plan(cv_path, ids, expected_cv_id="demo_v01")
    else:
        save_cv_plan(cv_path, plan)
    predictions = {k: np.full(len(valid), np.mean(y[list(train)])) for k, (train, valid) in enumerate(plan.splits)}
    frame = build_oof_frame(plan, predictions)
    with experiment_run(
        Path("output/experiments"), major="exp000_demo_cv", minor="000",
        config={"cv": "demo_v01", "n_splits": 3, "model": "train_mean"},
        cv_id=plan.cv_id, cv_fingerprint=cv_fingerprint(plan), data_version="synthetic_v01",
    ) as run:
        save_oof_csv(run.directory / "oof.csv", frame)
        rmse = float(np.sqrt(np.mean((frame["prediction"].to_numpy() - y) ** 2)))
        run.save_metrics({"cv_rmse": rmse})
        print(f"run: {run.directory}; CV RMSE: {rmse:.4f}")


if __name__ == "__main__":
    main()
