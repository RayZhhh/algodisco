# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import argparse

from algodisco.common.runner import PROJECT_ROOT, run_search_from_config
from algodisco.methods.one_plus_one_eps.config import OnePlusOneEPSConfig
from algodisco.methods.one_plus_one_eps.search import OnePlusOneEPS


def main():
    parser = argparse.ArgumentParser(description="Run (1+1)-EPS algorithm search.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(PROJECT_ROOT / "examples" / "online_bin_packing" / "configs" / "one_plus_one_eps.yaml"),
        help="Path to the YAML config file",
    )
    args, config_overrides = parser.parse_known_args()

    run_search_from_config(
        config_path=args.config,
        config_cls=OnePlusOneEPSConfig,
        search_cls=OnePlusOneEPS,
        project_root=PROJECT_ROOT,
        config_overrides=config_overrides,
    )


if __name__ == "__main__":
    main()
