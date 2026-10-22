"""Isolated ML experiment run outputs and provenance (no external services)."""

from __future__ import annotations

import json
import math
import numbers
import os
import re
import socket
import subprocess
import tempfile
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from omegaconf import OmegaConf

_SECRET_KEY = re.compile(r"(?:password|passwd|secret|token|credential|api[_-]?key|private[_-]?key)", re.IGNORECASE)
_COMPONENT = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*\Z")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _git_sha() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=True, timeout=2,
        )
        return proc.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _clean_config(config: Any) -> Any:
    if OmegaConf.is_config(config):
        config = OmegaConf.to_container(config, resolve=True)
    if is_dataclass(config) and not isinstance(config, type):
        config = asdict(config)
    if isinstance(config, Mapping):
        return {str(k): "<redacted>" if _SECRET_KEY.search(str(k)) else _clean_config(v) for k, v in config.items()}
    if isinstance(config, (list, tuple)):
        return [_clean_config(v) for v in config]
    if isinstance(config, np.generic):
        return config.item()
    if config is None or isinstance(config, (str, int, float, bool)):
        return config
    raise TypeError(f"Unsupported config value type: {type(config).__name__}")


def _write_json(path: Path, obj: Any) -> None:
    """Atomic write with a temporary file in the same directory."""
    content = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as f:
            tmp = Path(f.name)
            f.write(content)
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _metric_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _metric_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_metric_value(v) for v in value]
    if isinstance(value, numbers.Real) and not isinstance(value, (bool, np.bool_)):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("metrics must contain only finite numbers")
        return result
    raise TypeError("metrics must contain only numeric scalars, lists, or dictionaries")


class ExperimentRun:
    def __init__(self, directory: Path, metadata: dict[str, Any]):
        self.directory = directory
        self.metadata = metadata
        self._start = time.monotonic()
        self._ended = False

    @property
    def run_id(self) -> str:
        return self.metadata["run_id"]

    def save_metrics(self, metrics: Mapping[str, Any]) -> Path:
        if self._ended:
            raise RuntimeError("run has already finished")
        dest = self.directory / "metrics.json"
        if dest.exists():
            raise FileExistsError(f"metrics already exist for this run: {dest}")
        data = _metric_value(metrics)
        if not data:
            raise ValueError("metrics must be nonempty")
        _write_json(dest, data)
        return dest

    def set_wandb(self, *, run_id: str | None, url: str | None) -> None:
        """Store tracking references, but never credentials or environment dumps."""
        if run_id:
            self.metadata["wandb_run_id"] = run_id
        if url:
            self.metadata["wandb_url"] = url
        _write_json(self.directory / "run.json", self.metadata)

    def finish(self, status: str, *, error_type: str | None = None) -> None:
        if self._ended:
            raise RuntimeError("run has already finished")
        if status not in {"completed", "failed"}:
            raise ValueError("status must be 'completed' or 'failed'")
        self.metadata.update(status=status, finished_at=_utc_now(), duration_seconds=round(time.monotonic() - self._start, 3))
        if error_type:
            self.metadata["error_type"] = error_type
        _write_json(self.directory / "run.json", self.metadata)
        self._ended = True


@contextmanager
def experiment_run(
    output_root: str | Path,
    *,
    major: str,
    minor: str,
    config: Any,
    cv_id: str | None = None,
    cv_fingerprint: str | None = None,
    data_version: str | None = None,
) -> Iterator[ExperimentRun]:
    """Create a unique run directory and automatically record final status.

    The caller passes resolved experiment configuration and explicit CV/data
    provenance. Never reuse the same run directory or overwrite artifacts.
    """
    if not _COMPONENT.fullmatch(major) or not _COMPONENT.fullmatch(minor):
        raise ValueError("major/minor must be simple path components")
    safe_config = _clean_config(config)
    # Validate serializability before creating an output directory.
    yaml_text = yaml.safe_dump(safe_config, sort_keys=False, allow_unicode=True)
    root = Path(output_root) / major / minor
    root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:10]
    directory = root / run_id
    directory.mkdir(exist_ok=False)
    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "major": major,
        "minor": minor,
        "status": "running",
        "started_at": _utc_now(),
        "git_commit": _git_sha(),
        "cv_id": cv_id,
        "cv_fingerprint": cv_fingerprint,
        "data_version": data_version,
        "host": socket.gethostname(),
    }
    (directory / "config.yaml").write_text(yaml_text, encoding="utf-8")
    _write_json(directory / "run.json", metadata)
    run = ExperimentRun(directory, metadata)
    try:
        yield run
    except BaseException as exc:
        run.finish("failed", error_type=type(exc).__name__)
        raise
    else:
        run.finish("completed")
