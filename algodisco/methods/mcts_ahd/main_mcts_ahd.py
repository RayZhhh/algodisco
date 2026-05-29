# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import argparse

from algodisco.common.runner import PROJECT_ROOT, run_search_from_config
from algodisco.methods.mcts_ahd.config import MCTSAHDConfig
from algodisco.methods.mcts_ahd.search import MCTSAHDSearch


def main():
    """CLI entrypoint for running MCTS-AHD from a YAML config file."""
    parser = argparse.ArgumentParser(description="Run MCTS-AHD algorithm search.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(
            PROJECT_ROOT
            / "examples"
            / "online_bin_packing"
            / "configs"
            / "mcts_ahd.yaml"
        ),
        help="Path to the YAML config file",
    )
    args, config_overrides = parser.parse_known_args()

    run_search_from_config(
        config_path=args.config,
        config_cls=MCTSAHDConfig,
        search_cls=MCTSAHDSearch,
        project_root=PROJECT_ROOT,
        config_overrides=config_overrides,
    )


if __name__ == "__main__":
    main()
