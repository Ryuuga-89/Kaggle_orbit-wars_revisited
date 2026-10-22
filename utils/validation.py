"""CV split manifests: validate, save and reuse an explicit fold assignment.

No split strategy is imposed: pass indices from KFold, GroupKFold,
TimeSeriesSplit, or a competition-specific splitter.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CVPlan:
    cv_id: str
    row_ids: tuple[str, ...]
    splits: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]


def make_cv_plan(
    cv_id: str,
    row_ids: Sequence[object],
    splits: Iterable[tuple[Sequence[int], Sequence[int]]],
    *,
    groups: Sequence[object] | None = None,
    times: Sequence[object] | None = None,
    require_complete: bool = True,
) -> CVPlan:
    """Validate train/validation splits, optionally checking groups or time order.

    Validation rows must be unique across folds. For forward/time-split CV,
    set require_complete=False because early rows may never be validation.
    """
    if not isinstance(cv_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", cv_id):
        raise ValueError("cv_id must contain only letters, digits, dots, underscores, or hyphens")
    ids = tuple(str(v) for v in row_ids)
    n = len(ids)
    if not n or any(v == "" or v == "None" for v in ids) or len(set(ids)) != n:
        raise ValueError("row_ids must be nonempty, unique, and non-null after string conversion")
    if groups is not None and len(groups) != n:
        raise ValueError("groups must match row_ids length")
    if times is not None and len(times) != n:
        raise ValueError("times must match row_ids length")

    folds: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    seen: set[int] = set()
    for train_seq, valid_seq in splits:
        train = _indices(train_seq, n)
        valid = _indices(valid_seq, n)
        if not train or not valid or set(train) & set(valid):
            raise ValueError("train and validation must be nonempty and disjoint")
        if seen.intersection(valid):
            raise ValueError("a row appears in validation for multiple folds")
        if groups is not None and {str(groups[i]) for i in train} & {str(groups[i]) for i in valid}:
            raise ValueError("train and validation share a group")
        if times is not None:
            try:
                if max(times[i] for i in train) >= min(times[i] for i in valid):
                    raise ValueError("train timestamps must strictly precede validation timestamps")
            except TypeError as exc:
                raise ValueError("times values must be mutually comparable") from exc
        seen.update(valid)
        folds.append((train, valid))

    if not folds:
        raise ValueError("at least one fold is required")
    if require_complete and len(seen) != n:
        raise ValueError(f"OOF coverage incomplete: {len(seen)} of {n} rows")
    return CVPlan(cv_id=cv_id, row_ids=ids, splits=tuple(folds))


def _indices(values: Sequence[int], n: int) -> tuple[int, ...]:
    result = []
    for value in values:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise TypeError("split indices must be integers")
        index = int(value)
        if not 0 <= index < n:
            raise ValueError(f"index {index} outside [0, {n})")
        result.append(index)
    if len(result) != len(set(result)):
        raise ValueError("duplicate indices within a split")
    return tuple(result)


def save_cv_plan(path: str | Path, plan: CVPlan) -> Path:
    """Store explicit train/valid indices and ordered row IDs, without overwriting."""
    path = Path(path)
    data = {
        "format_version": 1,
        "cv_id": plan.cv_id,
        "row_ids": list(plan.row_ids),
        "splits": [{"train": list(train), "valid": list(valid)} for train, valid in plan.splits],
    }
    _save_exclusive(path, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return path


def load_cv_plan(
    path: str | Path,
    row_ids: Sequence[object],
    *,
    expected_cv_id: str | None = None,
    groups: Sequence[object] | None = None,
    times: Sequence[object] | None = None,
    require_complete: bool = True,
) -> CVPlan:
    """Reject reusing a plan on reordered/different rows or with a wrong CV ID."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format_version") != 1:
        raise ValueError("unsupported CV manifest format")
    normalized = tuple(str(i) for i in row_ids)
    if tuple(data["row_ids"]) != normalized:
        raise ValueError("row_ids or their order differs from saved CV plan")
    if expected_cv_id is not None and data["cv_id"] != expected_cv_id:
        raise ValueError("saved CV ID does not match expected_cv_id")
    return make_cv_plan(
        data["cv_id"], row_ids,
        ((part["train"], part["valid"]) for part in data["splits"]),
        groups=groups, times=times, require_complete=require_complete,
    )


def cv_fingerprint(plan: CVPlan) -> str:
    """Stable digest including row IDs, fold IDs, and all train/valid memberships."""
    raw = json.dumps(
        [plan.cv_id, plan.row_ids, plan.splits], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_oof_frame(
    plan: CVPlan,
    predictions_by_fold: dict[int, Sequence[object]],
    *,
    allow_partial: bool = False,
) -> pd.DataFrame:
    """Align validation predictions to original sample indices, not append order.

    Supports 1D regression/binary and 2D multiclass predictions. Rejects
    missing/duplicated/unexpected folds, mismatched lengths and NaN/Inf.
    """
    required = set(range(len(plan.splits)))
    supplied = set(predictions_by_fold)
    if not supplied.issubset(required) or (not allow_partial and supplied != required):
        raise ValueError("fold prediction keys do not match the CV plan")
    records: list[tuple[int, int, np.ndarray]] = []
    width = None
    for fold in sorted(supplied):
        valid = plan.splits[fold][1]
        preds = np.asarray(predictions_by_fold[fold], dtype=float)
        if preds.ndim == 1:
            preds = preds.reshape(-1, 1)
        if preds.ndim != 2 or preds.shape[0] != len(valid) or preds.shape[1] < 1:
            raise ValueError(f"fold {fold}: prediction shape does not match validation rows")
        if not np.isfinite(preds).all():
            raise ValueError(f"fold {fold}: predictions contain NaN/Inf")
        if width is None:
            width = preds.shape[1]
        elif width != preds.shape[1]:
            raise ValueError("all folds must have the same prediction width")
        records.extend((index, fold, row) for index, row in zip(valid, preds, strict=True))
    if not records:
        raise ValueError("no predictions supplied")
    records.sort(key=lambda v: v[0])
    if not allow_partial and len(records) != len(plan.row_ids):
        raise ValueError("OOF predictions do not cover all rows")
    cols = ["prediction"] if width == 1 else [f"prediction_{k}" for k in range(width)]
    data = {
        "row_index": [i for i, _, _ in records],
        "row_id": [plan.row_ids[i] for i, _, _ in records],
        "fold": [fold for _, fold, _ in records],
    }
    data.update({key: [float(pred[k]) for _, _, pred in records] for k, key in enumerate(cols)})
    return pd.DataFrame(data)


def save_oof_csv(path: str | Path, frame: pd.DataFrame) -> Path:
    """Write validated OOF data without overwriting a previous run."""
    if frame.empty or not {"row_index", "row_id", "fold"}.issubset(frame.columns):
        raise ValueError("OOF frame must include row_index, row_id, and fold")
    if frame["row_index"].duplicated().any() or frame["row_id"].astype(str).duplicated().any():
        raise ValueError("OOF frame has duplicated rows")
    if not any(c.startswith("prediction") for c in frame.columns):
        raise ValueError("OOF frame is missing predictions")
    _save_exclusive(Path(path), frame.to_csv(index=False, float_format="%.17g"))
    return Path(path)


def _save_exclusive(path: Path, content: str) -> None:
    """Atomic create-only write; a concurrent writer cannot overwrite an artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".tmp-", encoding="utf-8", delete=False) as f:
            temp_name = f.name
            f.write(content)
        os.link(temp_name, path)  # fails if target exists
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
