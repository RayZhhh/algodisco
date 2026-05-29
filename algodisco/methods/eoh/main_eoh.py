# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import argparse

from algodisco.common.runner import PROJECT_ROOT, run_search_from_config
from algodisco.methods.eoh.config import EoHConfig
from algodisco.methods.eoh.search import EoHSearch


def main():
    parser = argparse.ArgumentParser(description="Run EoH algorithm search.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(PROJECT_ROOT / "examples" / "online_bin_packing" / "configs" / "eoh.yaml"),
        help="Path to the YAML config file",
    )
    args, config_overrides = parser.parse_known_args()

    run_search_from_config(
        config_path=args.config,
        config_cls=EoHConfig,
        search_cls=EoHSearch,
        project_root=PROJECT_ROOT,
        config_overrides=config_overrides,
    )


if __name__ == "__main__":
    main()
