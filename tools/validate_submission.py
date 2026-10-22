"""Offline, competition-agnostic Kaggle CSV submission preflight.

This script never authenticates, uploads, or submits anything.
"""

from __future__ import annotations

import csv
import math
import re
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import click

_NUMERIC = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


class SubmissionValidationError(ValueError):
    """A submission file violates the selected sample schema."""


@dataclass(frozen=True)
class SubmissionReport:
    rows: int
    columns: tuple[str, ...]
    id_column: str | None
    numeric_columns: tuple[str, ...]
    ordered_ids: bool


def _check_header(reader: csv.reader, path: Path) -> list[str]:
    try:
        columns = next(reader)
    except StopIteration as exc:
        raise SubmissionValidationError(f"{path}: empty CSV") from exc
    if not columns or any(not col.strip() for col in columns):
        raise SubmissionValidationError(f"{path}: blank column name")
    if len(columns) != len(set(columns)):
        raise SubmissionValidationError(f"{path}: duplicate column names")
    return columns


def _read_row(reader: csv.reader, expected_width: int, label: str, row_number: int) -> list[str] | None:
    try:
        row = next(reader)
    except StopIteration:
        return None
    if len(row) != expected_width:
        raise SubmissionValidationError(
            f"{label}: row {row_number} has {len(row)} cells, expected {expected_width}"
        )
    return row


def validate_submission(
    submission: str | Path,
    sample: str | Path,
    *,
    id_column: str | None = None,
    no_id: bool = False,
    allow_reordered: bool = False,
    numeric_columns: tuple[str, ...] = (),
) -> SubmissionReport:
    """Match a CSV against a sample schema with strict row and ID checks.

    Default: recognize an unambiguous header named 'id' (any capitalization).
    For other IDs use id_column='PassengerId'; for ID-less competitions set
    no_id=True explicitly. Columns, order, and row counts must match.
    """
    if id_column is not None and no_id:
        raise SubmissionValidationError("--id-column and --no-id are mutually exclusive")
    if len(numeric_columns) != len(set(numeric_columns)):
        raise SubmissionValidationError("duplicate --numeric column")
    with ExitStack() as stack:
        sample_path, submission_path = Path(sample), Path(submission)
        for path in (sample_path, submission_path):
            if not path.is_file():
                raise SubmissionValidationError(f"CSV file not found: {path}")
        sample_file = stack.enter_context(sample_path.open(newline="", encoding="utf-8-sig"))
        pred_file = stack.enter_context(submission_path.open(newline="", encoding="utf-8-sig"))
        expected_reader = csv.reader(sample_file, strict=True)
        actual_reader = csv.reader(pred_file, strict=True)
        columns = _check_header(expected_reader, sample_path)
        actual_columns = _check_header(actual_reader, submission_path)
        if actual_columns != columns:
            raise SubmissionValidationError(
                f"column names/order mismatch: expected {columns!r}, got {actual_columns!r}"
            )

        if no_id:
            selected_id = None
        elif id_column is not None:
            if id_column not in columns:
                raise SubmissionValidationError(f"ID column {id_column!r} is not in the sample")
            selected_id = id_column
        else:
            candidates = [col for col in columns if col.lower() == "id"]
            if len(candidates) != 1:
                raise SubmissionValidationError(
                    "ID column cannot be inferred: use --id-column NAME or --no-id explicitly"
                )
            selected_id = candidates[0]
        if not (set(columns) - ({selected_id} if selected_id else set())):
            raise SubmissionValidationError("no prediction columns")
        unknown = set(numeric_columns) - set(columns)
        if unknown:
            raise SubmissionValidationError(f"unknown --numeric columns: {sorted(unknown)!r}")
        if selected_id in numeric_columns:
            raise SubmissionValidationError("ID column cannot be validated as a numeric prediction")
        if allow_reordered and selected_id is None:
            raise SubmissionValidationError("--allow-reordered requires an ID column")

        id_index = columns.index(selected_id) if selected_id else None
        numeric_indices = [(column, columns.index(column)) for column in numeric_columns]
        sample_ids: set[str] = set()
        submitted_ids: set[str] = set()
        rows = 0
        while True:
            sample_row = _read_row(expected_reader, len(columns), str(sample_path), rows + 2)
            submitted_row = _read_row(actual_reader, len(columns), str(submission_path), rows + 2)
            if sample_row is None and submitted_row is None:
                break
            if sample_row is None or submitted_row is None:
                raise SubmissionValidationError(f"row count differs at data row {rows + 1}")
            rows += 1
            if any(not cell.strip() for cell in submitted_row):
                raise SubmissionValidationError(f"submission row {rows}: missing or blank field")
            if id_index is not None:
                expected_id = sample_row[id_index]
                actual_id = submitted_row[id_index]
                if not expected_id.strip():
                    raise SubmissionValidationError(f"sample row {rows}: missing ID")
                if expected_id in sample_ids:
                    raise SubmissionValidationError(f"sample row {rows}: duplicate ID {expected_id!r}")
                if actual_id in submitted_ids:
                    raise SubmissionValidationError(f"submission row {rows}: duplicate ID {actual_id!r}")
                sample_ids.add(expected_id)
                submitted_ids.add(actual_id)
                if not allow_reordered and expected_id != actual_id:
                    raise SubmissionValidationError(
                        f"submission row {rows}: ID/order mismatch (expected {expected_id!r}, got {actual_id!r})"
                    )
            for column, index in numeric_indices:
                value = submitted_row[index].strip()
                if not _NUMERIC.fullmatch(value) or not math.isfinite(float(value)):
                    raise SubmissionValidationError(
                        f"submission row {rows}, column {column!r}: non-finite or invalid numeric prediction"
                    )
        if rows == 0:
            raise SubmissionValidationError("submission has no data rows")
        if allow_reordered and sample_ids != submitted_ids:
            raise SubmissionValidationError("submission IDs differ from sample IDs")
    return SubmissionReport(rows, tuple(columns), selected_id, numeric_columns, not allow_reordered)


@click.command()
@click.argument("submission", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--sample", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True)
@click.option("--id-column", default=None, help="ID column; auto-recognizes an exact 'id' header")
@click.option("--no-id", is_flag=True, help="Explicitly use row count/order without an ID field")
@click.option("--numeric", "numeric_columns", multiple=True, help="Prediction column requiring finite numbers")
@click.option("--allow-reordered", is_flag=True, help="Allow different row order if ID sets exactly match")
def main(
    submission: Path,
    sample: Path,
    id_column: str | None,
    no_id: bool,
    numeric_columns: tuple[str, ...],
    allow_reordered: bool,
) -> None:
    """Validate a local CSV against sample_submission.csv; NEVER upload or submit."""
    try:
        report = validate_submission(
            submission, sample, id_column=id_column, no_id=no_id,
            numeric_columns=numeric_columns, allow_reordered=allow_reordered,
        )
    except (SubmissionValidationError, OSError, UnicodeError, csv.Error) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        f"PASS: {report.rows} rows, {len(report.columns)} columns, "
        f"ID: {report.id_column or 'none (explicit)'}, numeric: {list(report.numeric_columns)}"
    )


if __name__ == "__main__":
    main()
