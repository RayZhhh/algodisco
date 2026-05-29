# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import argparse
from dataclasses import dataclass
from pathlib import Path

from algodisco.common.runner import PROJECT_ROOT, run_search_from_config
from algodisco.methods.eoh.config import EoHConfig
from algodisco.methods.eoh.search import EoHSearch
from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch
from algodisco.methods.mcts_ahd.config import MCTSAHDConfig
from algodisco.methods.mcts_ahd.search import MCTSAHDSearch
from algodisco.methods.one_plus_one_eps.config import OnePlusOneEPSConfig
from algodisco.methods.one_plus_one_eps.search import OnePlusOneEPS
from algodisco.methods.openevolve.config import OpenEvolveConfig
from algodisco.methods.openevolve.search import OpenEvolve
from algodisco.methods.partevo.config import PartEvoConfig
from algodisco.methods.partevo.search import PartEvoSearch
from algodisco.methods.randsample.config import RandSampleConfig
from algodisco.methods.randsample.search import RandSample
from algodisco.methods.reevo.config import ReEvoConfig
from algodisco.methods.reevo.search import ReEvoSearch


@dataclass(frozen=True)
class MethodSpec:
    config_cls: type
    search_cls: type
    default_config: Path


EXAMPLE_CONFIG_DIR = PROJECT_ROOT / "examples" / "online_bin_packing" / "configs"

METHODS: dict[str, MethodSpec] = {
    "eoh": MethodSpec(EoHConfig, EoHSearch, EXAMPLE_CONFIG_DIR / "eoh.yaml"),
    "funsearch": MethodSpec(
        FunSearchConfig,
        FunSearch,
        EXAMPLE_CONFIG_DIR / "funsearch.yaml",
    ),
    "funsearch_swanlab": MethodSpec(
        FunSearchConfig,
        FunSearch,
        EXAMPLE_CONFIG_DIR / "funsearch_swanlab.yaml",
    ),
    "mcts_ahd": MethodSpec(
        MCTSAHDConfig,
        MCTSAHDSearch,
        EXAMPLE_CONFIG_DIR / "mcts_ahd.yaml",
    ),
    "one_plus_one_eps": MethodSpec(
        OnePlusOneEPSConfig,
        OnePlusOneEPS,
        EXAMPLE_CONFIG_DIR / "one_plus_one_eps.yaml",
    ),
    "openevolve": MethodSpec(
        OpenEvolveConfig,
        OpenEvolve,
        EXAMPLE_CONFIG_DIR / "openevolve.yaml",
    ),
    "partevo": MethodSpec(
        PartEvoConfig,
        PartEvoSearch,
        EXAMPLE_CONFIG_DIR / "partevo.yaml",
    ),
    "randsample": MethodSpec(
        RandSampleConfig,
        RandSample,
        EXAMPLE_CONFIG_DIR / "randsample.yaml",
    ),
    "reevo": MethodSpec(ReEvoConfig, ReEvoSearch, EXAMPLE_CONFIG_DIR / "reevo.yaml"),
}


def run_method(
    method: str,
    *,
    config_path: str | Path | None = None,
    config_overrides: list[str] | None = None,
):
    """Run a registered search method by name."""
    try:
        spec = METHODS[method]
    except KeyError as error:
        available = ", ".join(sorted(METHODS))
        raise ValueError(f"Unknown method '{method}'. Available methods: {available}") from error

    return run_search_from_config(
        config_path=config_path or spec.default_config,
        config_cls=spec.config_cls,
        search_cls=spec.search_cls,
        project_root=PROJECT_ROOT,
        config_overrides=config_overrides,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="algodisco",
        description="Run AlgoDisco search methods from YAML configs.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one search method.")
    run_parser.add_argument("method", choices=sorted(METHODS))
    run_parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to the YAML config file. Defaults to the method's online bin packing example config.",
    )

    args, config_overrides = parser.parse_known_args()
    if args.command == "run":
        run_method(
            args.method,
            config_path=args.config,
            config_overrides=config_overrides,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
