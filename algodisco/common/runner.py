# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from pathlib import Path
from typing import Any

from algodisco.common.config_loading import (
    build_component,
    build_method_config,
    load_yaml_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_search_from_config(
    *,
    config_path: str | Path,
    config_cls: type,
    search_cls: type,
    project_root: Path = PROJECT_ROOT,
    config_overrides: list[str] | None = None,
) -> Any:
    """Build and run one search method from a YAML config file."""
    config_data = load_yaml_config(config_path, config_overrides)
    method_config, debug_mode, debug_mode_crash = build_method_config(
        config_data=config_data,
        project_root=project_root,
        config_cls=config_cls,
    )

    llm = build_component(
        section_config=config_data.get("llm", {}),
        project_root=project_root,
    )
    evaluator = build_component(
        section_config=config_data.get("evaluator", {}),
        project_root=project_root,
    )
    logger = build_component(
        section_config=config_data.get("logger", {}),
        project_root=project_root,
        path_kwargs=("logdir", "swanlab_logdir"),
    )

    if not llm:
        raise ValueError("An LLM must be provided in the configuration.")
    if not evaluator:
        raise ValueError("An Evaluator must be provided in the configuration.")

    search = search_cls(
        config=method_config,
        llm=llm,
        evaluator=evaluator,
        logger=logger,
    )
    search.debug_mode = debug_mode
    search.debug_mode_crash = debug_mode_crash
    search.run()
    return search
