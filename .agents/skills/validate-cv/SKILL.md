---
name: validate-cv
description: Validate or review Kaggle cross-validation designs, fold splits, OOF alignment, GroupKFold/TimeSeriesSplit leakage, and split reproducibility. Use when creating, changing, debugging, or comparing CV and OOF experiments.
---

# Validate Kaggle CV and OOF

Use the existing utilities; **do not invent a new split implementation or metric unless required**. This skill offers a procedure, not automated selection of the statistically correct CV design.

## Gather only necessary context

1. Read `docs/COMPETITION.md` for target, evaluation metric, data dependencies, time/group leakage, and official rules. If blank, inspect the relevant task and ask only for critical missing information before executing a costly experiment.
2. Inspect the target experiment and relevant portion of `docs/EXPERIMENTS.md`; check prior CV IDs in `docs/EXPERIMENT_LOG.md` if comparing experiments.
3. Confirm whether splitting must respect time, user/entity/group, spatial structure, or train/test shifts. A syntactically valid CV plan is **not** proof of leakage-free features or representative validation.

## Construct and reuse splits

- Use a splitter that reflects the validation design, e.g. `sklearn.model_selection.KFold`, `GroupKFold`, or `TimeSeriesSplit`. Fix and record random seeds if the strategy is randomized.
- Build a plan using `utils.validation.make_cv_plan(cv_id, row_ids, splits, groups=..., times=...)`. `row_ids` must be unique; pass actual groups/times so the optional overlap checks are active.
- For forward-chaining TimeSeriesSplit where some initial rows never appear in validation, pass `require_complete=False` to both `make_cv_plan` and `load_cv_plan`.
- Store once with `save_cv_plan(path, plan)` under `output/cv/`; reload with `load_cv_plan(path, row_ids, expected_cv_id=cv_id, groups=..., times=...)`. Existing plans are deliberately not overwritten.
- Record `cv_fingerprint(plan)` and data version in `experiment_run(..., cv_id=..., cv_fingerprint=..., data_version=...)`.
- Do not compare experiment scores measured on different CV plans or data versions as if they were controlled comparisons.

## Check predictions and artifacts

- For each fold, ensure predictions are generated **only** for that fold's validation indices and in their original order. Store them as `predictions_by_fold[fold_number]`.
- Call `build_oof_frame(plan, predictions_by_fold)`. For partial OOF (e.g. time splits) use `allow_partial=True`; evaluate only rows with predictions, aligning targets by `row_index` or `row_id`.
- Persist using `save_oof_csv(run.directory / "oof.csv", frame)`; avoid overwriting artifacts from prior runs.
- Calculate competition-specific metrics with a properly aligned target and save actual results via `run.save_metrics({...})`. The shared utilities **do not** calculate model performance, automatically upload to W&B, or verify arbitrary feature leakage.
- Summarize the evidence (CV ID, data version, metric, fold dispersion, code commit, artifact path) in `docs/EXPERIMENT_LOG.md` when relevant.

## Verification and stop conditions

```bash
uv run pytest -q
uv run ruff check .
uv run python -m tools.demo_cv
```

The demo uses synthetic data only. Treat duplicate IDs, fold overlap, missing OOF rows, suspiciously high CV scores, and undocumented public-LB tuning as reasons to inspect the pipeline before running more trials. Preserve secrets and private datasets; no upload or Kaggle submission is part of this skill.
