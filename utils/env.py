from dataclasses import dataclass, field
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).parent.parent


@dataclass
class EnvConfig:
    input_dir: str = field(default_factory=lambda: str(_project_root() / "input"))
    output_dir: str = field(default_factory=lambda: str(_project_root() / "output"))
    exp_output_dir: str = field(default_factory=lambda: str(_project_root() / "output" / "experiments"))
