"""Regression tests for Kaggle helper functions (no Kaggle API/network required)."""
from pathlib import Path
from types import SimpleNamespace

import click
import pytest

from tools.check_submission import find_submission, wait_for_submission
from tools.upload_model import copy_matching_files


class FakeApi:
    def __init__(self, batches):
        self.batches = iter(batches)

    def competition_submissions(self, competition):
        assert competition == "sample"
        return next(self.batches)


def submission(ref, status="pending", score=None, error=None):
    return SimpleNamespace(ref=ref, status=status, publicScore=score, errorDescription=error)


def test_submission_ref_match():
    api = FakeApi([[submission(10), submission(11)]])
    assert find_submission(api, "sample", "11").ref == 11


def test_completed_submission(capsys):
    api = FakeApi([[submission(11, "complete", "0.9")]])
    wait_for_submission(api, "sample", "11", 1, 10)
    assert "0.9" in capsys.readouterr().out


def test_failed_submission():
    api = FakeApi([[submission(11, "error", error="Invalid format")]])
    with pytest.raises(click.ClickException, match="Invalid format"):
        wait_for_submission(api, "sample", "11", 1, 10)


def test_missing_submission():
    with pytest.raises(click.ClickException, match="not found"):
        wait_for_submission(FakeApi([[]]), "sample", "11", 1, 10)


def test_upload_matches_globs_and_preserves_paths(tmp_path: Path):
    source = tmp_path / "src"
    target = tmp_path / "target"
    (source / "exp01").mkdir(parents=True)
    (source / "exp01" / "best_model.pt").write_text("model")
    matches = copy_matching_files(source, target, ("**/best_model.pt",))
    assert len(matches) == 1
    assert (target / "exp01" / "best_model.pt").read_text() == "model"


def test_upload_rejects_symlink_escape(tmp_path: Path):
    source = tmp_path / "src"
    source.mkdir()
    external = tmp_path / "external.pt"
    external.write_text("private")
    (source / "best_model.pt").symlink_to(external)
    with pytest.raises(click.ClickException, match="outside"):
        copy_matching_files(source, tmp_path / "target", ("**/best_model.pt",))
