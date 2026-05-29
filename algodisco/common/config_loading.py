# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import dataclasses
import importlib
import importlib.util
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin

from omegaconf import OmegaConf

from algodisco.common.component_config import preprocess_component_kwargs


def load_class(
    class_path: str | None = None,
    kwargs: dict[str, Any] | None = None,
    project_root: Path | None = None,
):
    """Dynamically imports and instantiates a class from a config section."""
    if not class_path:
        return None

    if kwargs is None:
        kwargs = {}

    if ":" in class_path and class_path.split(":", 1)[0].endswith(".py"):
        file_path_str, class_name = class_path.rsplit(":", 1)
        file_path = Path(file_path_str)
        if not file_path.is_absolute() and project_root is not None:
            file_path = project_root / file_path

        module_name = f"_algodisco_dynamic_{file_path.stem}_{abs(hash(file_path))}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from file path: {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)

    cls = getattr(module, class_name)
    return cls(**kwargs)


def load_yaml_config(
    config_path: str | Path,
    overrides: list[str] | None = None,
) -> dict[str, Any]:
    """Load a YAML config file with optional OmegaConf CLI overrides."""
    config = OmegaConf.load(config_path)
    if overrides:
        config = OmegaConf.merge(config, OmegaConf.from_cli(overrides))
    data = OmegaConf.to_container(config, resolve=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TypeError("Top-level config must be a mapping.")
    return data


def _extract_component_kwargs(section_config: dict[str, Any]) -> dict[str, Any]:
    """Extract constructor keyword arguments from a component config block.

    We support both `kwargs` and `args` in YAML so users can choose the style
    they find more natural. They are treated as aliases, not as two separate
    argument sources.
    """
    if "kwargs" in section_config and "args" in section_config:
        raise ValueError("Only one of 'kwargs' or 'args' may be provided in a config block.")

    raw_kwargs = section_config.get("kwargs", section_config.get("args", {}))
    if raw_kwargs is None:
        return {}
    if not isinstance(raw_kwargs, dict):
        raise TypeError("Component constructor arguments must be provided as a mapping.")
    return dict(raw_kwargs)


def _resolve_config_value(value: Any, project_root: Path) -> Any:
    """Recursively instantiate nested component configs inside a value.

    This is what enables composite YAML such as an ensemble LLM whose child
    models are themselves declared via nested `class_path` blocks.
    """
    if isinstance(value, list):
        return [_resolve_config_value(item, project_root) for item in value]

    if isinstance(value, dict):
        is_component_config = "class_path" in value and (
            "kwargs" in value or "args" in value or len(value) == 1
        )
        if is_component_config:
            # Instantiate the nested component first, then bubble the concrete
            # object back up into the parent's constructor kwargs.
            return load_class(
                class_path=value.get("class_path"),
                kwargs=_resolve_config_value(
                    _extract_component_kwargs(value),
                    project_root,
                ),
                project_root=project_root,
            )
        return {
            key: _resolve_config_value(item, project_root)
            for key, item in value.items()
        }

    return value


def _resolve_path(project_root: Path, path_value: str | None) -> str | None:
    if path_value is None:
        return None

    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str(project_root / path)


def _resolve_dataclass_type(field_type: Any) -> type | None:
    """Returns the underlying dataclass type for a field annotation, if any."""
    if isinstance(field_type, type) and dataclasses.is_dataclass(field_type):
        return field_type

    origin = get_origin(field_type)
    if origin in (list, dict, tuple):
        return None

    if origin is None:
        return None

    if origin not in (Union, UnionType):
        return None

    for arg in get_args(field_type):
        nested = _resolve_dataclass_type(arg)
        if nested is not None:
            return nested
    return None


def instantiate_dataclass_from_dict(
    config_cls: type, config_data: dict[str, Any], project_root: Path
) -> Any:
    """Instantiates a dataclass, recursively resolving nested config blocks."""
    method_config_data = dict(config_data)

    for field in dataclasses.fields(config_cls):
        if field.name not in method_config_data:
            continue

        value = method_config_data[field.name]
        if not isinstance(value, dict):
            continue

        if "class_path" in value and (
            "kwargs" in value or "args" in value or len(value) == 1
        ):
            method_config_data[field.name] = _resolve_config_value(
                value, project_root
            )
            continue

        nested_dataclass = _resolve_dataclass_type(field.type)
        if nested_dataclass is not None:
            method_config_data[field.name] = instantiate_dataclass_from_dict(
                nested_dataclass, value, project_root
            )

    return config_cls(**method_config_data)


def build_method_config(
    config_data: dict[str, Any],
    project_root: Path,
    config_cls: type,
) -> tuple[Any, bool, bool]:
    """Builds a method config dataclass from the YAML dictionary."""
    method_config_data = dict(config_data.get("method", {}))

    debug_mode = method_config_data.pop("debug_mode", False)
    debug_mode_crash = method_config_data.pop("debug_mode_crash", False)

    if "template_program_path" in method_config_data:
        template_path = Path(
            _resolve_path(project_root, method_config_data.pop("template_program_path"))
        )
        with open(template_path, "r") as f:
            method_config_data["template_program"] = f.read()

    task_desc_path = method_config_data.get("task_description_path")
    if task_desc_path:
        task_desc_path = Path(
            _resolve_path(project_root, method_config_data.pop("task_description_path"))
        )
        with open(task_desc_path, "r") as f:
            method_config_data["task_description"] = f.read()
    elif "task_description_path" in method_config_data:
        method_config_data.pop("task_description_path")

    if method_config_data.get("task_description") is None:
        method_config_data["task_description"] = ""

    if "template_dir" in method_config_data and method_config_data["template_dir"]:
        method_config_data["template_dir"] = _resolve_path(
            project_root, method_config_data["template_dir"]
        )

    return (
        instantiate_dataclass_from_dict(config_cls, method_config_data, project_root),
        debug_mode,
        debug_mode_crash,
    )


def build_component(
    section_config: dict[str, Any],
    project_root: Path,
    path_kwargs: tuple[str, ...] = (),
):
    """Instantiates a component from a config section, resolving relative paths."""
    if not section_config:
        return None

    class_path = section_config.get("class_path")
    kwargs = _resolve_config_value(
        _extract_component_kwargs(section_config),
        project_root,
    )
    # Allow common-layer preprocessors to translate richer YAML structures into
    # the canonical constructor kwargs expected by runtime classes.
    kwargs = preprocess_component_kwargs(class_path, kwargs)
    for key in path_kwargs:
        if key in kwargs and kwargs[key] is not None:
            # Preserve the old path-resolution behavior for known path fields
            # after nested components have already been materialized.
            kwargs[key] = _resolve_path(project_root, kwargs[key])

    return load_class(
        class_path=class_path,
        kwargs=kwargs,
        project_root=project_root,
    )
