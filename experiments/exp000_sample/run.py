import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import hydra
import wandb
from hydra.core.config_store import ConfigStore
from hydra.core.hydra_config import HydraConfig
from omegaconf import OmegaConf

from utils.artifacts import experiment_run
from utils.env import EnvConfig
from utils.logger import get_logger
from utils.timing import trace

WANDB_PROJECT_NAME = "kaggle-template"


@dataclass
class ExpConfig:
    debug: bool = False
    seed: int = 7
    learning_rate: float = 0.001
    batch_size: int = 32
    folds: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])


@dataclass
class Config:
    env: EnvConfig = field(default_factory=EnvConfig)
    exp: ExpConfig = field(default_factory=ExpConfig)


cs = ConfigStore.instance()
cs.store(name="default", group="env", node=EnvConfig)
cs.store(name="default", group="exp", node=ExpConfig)


@hydra.main(version_base=None, config_path=".", config_name="config")
def main(cfg: Config) -> None:
    """Smoke example: Hydra/W&B/run metadata only, NOT a training experiment."""
    major = Path(sys.argv[0]).parent.name
    minor = HydraConfig.get().runtime.choices.exp
    exp_name = f"{major}/{minor}"

    with experiment_run(cfg.env.exp_output_dir, major=major, minor=minor, config=cfg) as record:
        logger = get_logger(f"{__name__}.{record.run_id}", record.directory)
        logger.info("Start %s, run_id=%s", exp_name, record.run_id)
        logger.info("Resolved configuration saved at %s", record.directory / "config.yaml")

        with trace("sleep"):
            time.sleep(1.1)

        with wandb.init(
            project=WANDB_PROJECT_NAME,
            name=f"{exp_name}/{record.run_id}",
            notes=", ".join(HydraConfig.get().overrides.task),
            config=OmegaConf.to_container(cfg.exp, resolve=True),
            mode="disabled" if cfg.exp.debug else "online",
        ) as wb:
            record.set_wandb(run_id=getattr(wb, "id", None), url=getattr(wb, "url", None))
        logger.info("Finished smoke example (no training or CV metrics were computed)")


if __name__ == "__main__":
    main()
