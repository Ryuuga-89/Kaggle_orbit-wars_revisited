import hydra

from orbit.harness import Config, evaluate


@hydra.main(version_base=None, config_path=".", config_name="config")
def main(cfg: Config) -> None:
    """Evaluate the seeded random agent on the recorded protocol. This does not train."""
    evaluate(cfg)


if __name__ == "__main__":
    main()
