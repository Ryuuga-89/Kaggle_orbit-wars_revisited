"""Poll a specific Kaggle competition submission."""
import time
from typing import Any

import click

FAILED = {"error", "failed", "failure", "cancelled", "canceled"}


def find_submission(api: Any, competition: str, ref: str) -> Any | None:
    return next((s for s in api.competition_submissions(competition) if str(s.ref) == ref), None)


def wait_for_submission(api: Any, competition: str, ref: str, interval: int, timeout: int) -> Any:
    started = time.monotonic()
    while True:
        submission = find_submission(api, competition, ref)
        if submission is None:
            raise click.ClickException(f"Submission {ref} not found in recent submissions.")
        status = str(getattr(submission, "status", "")).strip().lower()
        if status == "complete":
            click.echo(f"Submission {ref}: complete, Public LB: {getattr(submission, 'publicScore', 'N/A')}")
            return submission
        if status in FAILED:
            error = getattr(submission, "errorDescription", None) or getattr(submission, "error", None)
            raise click.ClickException(f"Submission {ref} failed ({status}): {error or 'no details'}")
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise click.ClickException(f"Timed out waiting for submission {ref}, status={status}.")
        time.sleep(min(interval, remaining))


@click.command()
@click.argument("competition")
@click.option("--ref", "submission_ref", default=None, help="Submission reference; defaults to latest.")
@click.option("--interval", type=click.IntRange(min=1), default=60, show_default=True)
@click.option("--timeout", type=click.IntRange(min=1), default=3600, show_default=True)
def main(competition: str, submission_ref: str | None, interval: int, timeout: int) -> None:
    """Check Kaggle submission status; never submits a new entry."""
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    if submission_ref is None:
        submissions = api.competition_submissions(competition)
        if not submissions:
            raise click.ClickException(f"No submissions found for {competition}.")
        submission_ref = str(submissions[0].ref)
    click.echo(f"Tracking {competition}: {submission_ref}")
    wait_for_submission(api, competition, submission_ref, interval, timeout)


if __name__ == "__main__":
    main()
