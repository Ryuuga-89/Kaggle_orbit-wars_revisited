"""Upload selected model files as a private Kaggle Dataset."""
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import click


def copy_matching_files(source: Path, target: Path, patterns: tuple[str, ...]) -> list[Path]:
    """Copy only matching regular files, without following symlinks outside source."""
    root = source.resolve()
    copied: list[Path] = []
    for pattern in patterns:
        for path in sorted(source.glob(pattern)):
            if not path.is_file() or path in copied:
                continue
            if not path.resolve().is_relative_to(root):
                raise click.ClickException(f"Refusing path outside source directory: {path}")
            dest = target / path.relative_to(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            copied.append(path)
    return copied


@click.command()
@click.option("--title", "-t", required=True, help="Lowercase dataset slug.")
@click.option("--dir", "source", "-d", type=click.Path(path_type=Path, exists=True, file_okay=False),
              default=Path("./output/experiments"), show_default=True)
@click.option("--pattern", "-p", "patterns", multiple=True, default=("**/best_model.pt",),
              help="Glob for files to upload; repeatable.")
@click.option("--user-name", "-u", required=True, envvar="KAGGLE_USERNAME")
@click.option("--license", "license_name", default="other", show_default=True)
@click.option("--new", is_flag=True, help="Create a new private Dataset; otherwise upload a new version.")
def main(title: str, source: Path, patterns: tuple[str, ...], user_name: str,
         license_name: str, new: bool) -> None:
    """Upload selected artifacts; check the competition data license first."""
    from kaggle.api.kaggle_api_extended import KaggleApi

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", title):
        raise click.ClickException("Title must be a lowercase Kaggle dataset slug.")
    with tempfile.TemporaryDirectory(prefix="kaggle-upload-") as temporary:
        folder = Path(temporary)
        copied = copy_matching_files(source, folder, patterns)
        if not copied:
            raise click.ClickException("No model files matched the selected patterns.")
        metadata: dict[str, Any] = {
            "id": f"{user_name}/{title}",
            "title": title,
            "licenses": [{"name": license_name}],
        }
        (folder / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        api = KaggleApi()
        api.authenticate()
        if new:
            api.dataset_create_new(folder=folder, dir_mode="tar", convert_to_csv=False, public=False)
        else:
            api.dataset_create_version(folder=folder, version_notes="Update model artifacts",
                                       dir_mode="tar", convert_to_csv=False)
        click.echo(f"Uploaded {len(copied)} files to {metadata['id']}")


if __name__ == "__main__":
    main()
