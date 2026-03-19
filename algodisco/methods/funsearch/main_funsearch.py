# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import argparse
import importlib
import yaml
from pathlib import Path

# Automatically detect the project root (4 levels up from this file).
PROJECT_ROOT = Path(__file__).resolve().parents[3]

from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch


def load_class(class_path=None, kwargs=None):
    if not class_path:
        return None
    if kwargs is None:
        kwargs = {}
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(**kwargs)


def main():
    parser = argparse.ArgumentParser(description="Run FunSearch algorithm search.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(PROJECT_ROOT / "configs" / "funsearch.yaml"),
        help="Path to the YAML config file",
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config_data = yaml.safe_load(f)

    # Load configurations
    method_config_data = config_data.get("method", {})

    # Extract debug mode settings before creating config
    debug_mode = method_config_data.pop("debug_mode", False)
    debug_mode_crash = method_config_data.pop("debug_mode_crash", False)

    # Resolve relative paths against the project root
    if "template_program_path" in method_config_data:
        template_path = PROJECT_ROOT / method_config_data.pop("template_program_path")
        with open(template_path, "r") as f:
            method_config_data["template_program"] = f.read()

    # Handle task_description_path - only read if it's not null/empty
    task_desc_path = method_config_data.get("task_description_path")
    if task_desc_path:
        task_desc_path = PROJECT_ROOT / method_config_data.pop("task_description_path")
        with open(task_desc_path, "r") as f:
            method_config_data["task_description"] = f.read()
    elif "task_description_path" in method_config_data:
        method_config_data.pop("task_description_path")

    # Ensure task_description is not None
    if method_config_data.get("task_description") is None:
        method_config_data["task_description"] = ""

    method_config = FunSearchConfig(**method_config_data)

    # Dynamically instantiate components
    llm = load_class(
        class_path=config_data.get("llm", {}).get("class_path"),
        kwargs=config_data.get("llm", {}).get("kwargs", {}),
    )
    evaluator = load_class(
        class_path=config_data.get("evaluator", {}).get("class_path"),
        kwargs=config_data.get("evaluator", {}).get("kwargs", {}),
    )

    # Resolve logger path if it exists
    logger_config = config_data.get("logger", {})
    if "kwargs" in logger_config and "logdir" in logger_config["kwargs"]:
        logger_config["kwargs"]["logdir"] = str(
            PROJECT_ROOT / logger_config["kwargs"]["logdir"]
        )

    logger = load_class(
        class_path=logger_config.get("class_path"),
        kwargs=logger_config.get("kwargs", {}),
    )

    if not llm:
        raise ValueError("An LLM must be provided in the configuration.")
    if not evaluator:
        raise ValueError("An Evaluator must be provided in the configuration.")

    search = FunSearch(
        config=method_config, llm=llm, evaluator=evaluator, logger=logger
    )

    # Set debug mode from config
    search.debug_mode = debug_mode
    search.debug_mode_crash = debug_mode_crash

    search.run()


if __name__ == "__main__":
    main()
