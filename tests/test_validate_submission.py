"""Offline regression tests: Kaggle submission validation never uses the API."""

import csv

import pytest
from click.testing import CliRunner

from tools.validate_submission import SubmissionValidationError, main, validate_submission


def write_csv(tmp_path, name, rows):
    file = tmp_path / name
    with file.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return file


def files(tmp_path):
    sample = write_csv(tmp_path, "sample.csv", [["id", "target"], ["001", "0"], ["002", "0"]])
    submission = write_csv(tmp_path, "submission.csv", [["id", "target"], ["001", "0.25"], ["002", "0.75"]])
    return submission, sample


def test_valid_strict_ids_and_numeric(tmp_path):
    submission, sample = files(tmp_path)
    report = validate_submission(submission, sample, numeric_columns=("target",))
    assert report.rows == 2 and report.id_column == "id"
    result = CliRunner().invoke(main, [str(submission), "--sample", str(sample), "--numeric", "target"])
    assert result.exit_code == 0 and "PASS" in result.output


@pytest.mark.parametrize(
    ("sub_rows", "message"),
    [
        ([["id", "target", "extra"], ["001", "0", "z"], ["002", "1", "z"]], "column"),
        ([["target", "id"], ["0", "001"], ["1", "002"]], "column"),
        ([["id", "target"], ["001", "0"]], "row count"),
        ([["id", "target"], ["001", "0"], ["002", "0"], ["003", "0"]], "row count"),
        ([["id", "target"], ["002", "0"], ["001", "1"]], "ID/order"),
        ([["id", "target"], ["001", "0"], ["001", "1"]], "duplicate ID"),
        ([["id", "target"], ["001", ""], ["002", "1"]], "missing or blank"),
        ([["id", "target"], ["001", "0"], ["002"]], "cells"),
        ([["id", "target"], ["001", "0", "extra"], ["002", "1"]], "cells"),
        ([["id", "target"], ["001", "inf"], ["002", "1"]], "non-finite"),
        ([["id", "target"], ["001", "NaN"], ["002", "1"]], "non-finite"),
        ([["id", "target"], ["001", "a"], ["002", "1"]], "non-finite"),
        ([["id", "target"], ["001", "1e309"], ["002", "1"]], "non-finite"),
        ([["id", "target"], ["001", "0.2"], ["002", "  "]], "missing or blank"),
        ([["id", "id"], ["001", "0"], ["002", "1"]], "duplicate column"),
    ],
)
def test_invalid_submission(tmp_path, sub_rows, message):
    submission, sample = files(tmp_path)
    write_csv(tmp_path, "submission.csv", sub_rows)
    with pytest.raises(SubmissionValidationError, match=message):
        validate_submission(submission, sample, numeric_columns=("target",))


def test_reorder_opt_in_and_id_set(tmp_path):
    submission, sample = files(tmp_path)
    write_csv(tmp_path, "submission.csv", [["id", "target"], ["002", "0.2"], ["001", "0.3"]])
    report = validate_submission(submission, sample, allow_reordered=True, numeric_columns=("target",))
    assert report.rows == 2 and not report.ordered_ids
    write_csv(tmp_path, "submission.csv", [["id", "target"], ["002", "0.2"], ["003", "0.3"]])
    with pytest.raises(SubmissionValidationError, match="IDs differ"):
        validate_submission(submission, sample, allow_reordered=True)


def test_custom_id_and_no_id_explicit(tmp_path):
    sample = write_csv(tmp_path, "sample.csv", [["PassengerId", "Survived"], ["4", "0"], ["5", "0"]])
    submission = write_csv(tmp_path, "submission.csv", [["PassengerId", "Survived"], ["4", "1"], ["5", "0"]])
    with pytest.raises(SubmissionValidationError, match="cannot be inferred"):
        validate_submission(submission, sample)
    assert validate_submission(submission, sample, id_column="PassengerId").rows == 2
    assert validate_submission(submission, sample, no_id=True).id_column is None
    with pytest.raises(SubmissionValidationError, match="requires an ID"):
        validate_submission(submission, sample, no_id=True, allow_reordered=True)


def test_categorical_predictions_and_na_literals(tmp_path):
    sample = write_csv(tmp_path, "sample.csv", [["id", "category"], ["a", ""], ["b", ""]])
    submission = write_csv(tmp_path, "submission.csv", [["id", "category"], ["a", "NA"], ["b", "No"]])
    assert validate_submission(submission, sample).rows == 2
    with pytest.raises(SubmissionValidationError, match="invalid numeric"):
        validate_submission(submission, sample, numeric_columns=("category",))


def test_duplicate_sample_ids_and_empty(tmp_path):
    submission, sample = files(tmp_path)
    write_csv(tmp_path, "sample.csv", [["id", "target"], ["001", "0"], ["001", "0"]])
    with pytest.raises(SubmissionValidationError, match="duplicate ID"):
        validate_submission(submission, sample)
    write_csv(tmp_path, "sample.csv", [["id", "target"]])
    write_csv(tmp_path, "submission.csv", [["id", "target"]])
    with pytest.raises(SubmissionValidationError, match="no data rows"):
        validate_submission(submission, sample)


def test_numeric_column_must_exist_and_not_be_id(tmp_path):
    submission, sample = files(tmp_path)
    with pytest.raises(SubmissionValidationError, match="unknown"):
        validate_submission(submission, sample, numeric_columns=("p",))
    with pytest.raises(SubmissionValidationError, match="ID column cannot"):
        validate_submission(submission, sample, numeric_columns=("id",))


def test_utf8_bom_supported(tmp_path):
    submission, sample = files(tmp_path)
    text = submission.read_text()
    submission.write_text("\ufeff" + text)
    assert validate_submission(submission, sample).rows == 2
