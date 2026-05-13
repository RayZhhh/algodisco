# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from collections.abc import Callable, Mapping
from typing import Any

from algodisco.base.llm import LanguageModel


def _preprocess_ensemble_llm_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Convert YAML-friendly ensemble config into canonical constructor kwargs.

    `EnsembleLLM` itself only accepts runtime-ready constructor arguments:

    - `llms`
    - `probabilities`
    - `random_seed`

    For YAML, we additionally allow:

    ```yaml
    args:
      models:
        model_a:
          llm: <instantiated child LanguageModel>
          prob: 0.2
    ```

    This helper translates that declarative shape into the constructor form the
    runtime class expects.
    """
    if "models" not in kwargs:
        return kwargs

    if "llms" in kwargs or "probabilities" in kwargs:
        raise ValueError(
            "EnsembleLLM config must use either 'models' or "
            "'llms'/'probabilities', not both."
        )

    models = kwargs["models"]
    if not isinstance(models, Mapping):
        raise TypeError("EnsembleLLM 'models' config must be a mapping.")

    llms: list[LanguageModel] = []
    probabilities: list[float | None] = []

    for name, member in models.items():
        if isinstance(member, LanguageModel):
            llms.append(member)
            probabilities.append(None)
            continue

        if not isinstance(member, Mapping):
            raise TypeError(
                f"EnsembleLLM member '{name}' must be a LanguageModel or a mapping."
            )

        llm = member.get("llm", member.get("model"))
        if not isinstance(llm, LanguageModel):
            raise TypeError(
                f"EnsembleLLM member '{name}' must define an instantiated "
                "'llm' or 'model' field."
            )

        prob = member.get("prob")
        if prob is not None and not isinstance(prob, (int, float)):
            raise TypeError(
                f"EnsembleLLM member '{name}' has a non-numeric 'prob' value."
            )

        llms.append(llm)
        probabilities.append(prob)

    if any(prob is None for prob in probabilities):
        if not all(prob is None for prob in probabilities):
            raise ValueError(
                "If any EnsembleLLM member specifies 'prob', all members must specify it."
            )
        normalized_probabilities: list[float] | None = None
    else:
        normalized_probabilities = [float(prob) for prob in probabilities]

    preprocessed_kwargs = dict(kwargs)
    preprocessed_kwargs.pop("models")
    preprocessed_kwargs["llms"] = llms
    preprocessed_kwargs["probabilities"] = normalized_probabilities
    return preprocessed_kwargs


_COMPONENT_KWARGS_PREPROCESSORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "algodisco.providers.llm.ensemble_llm.EnsembleLLM": _preprocess_ensemble_llm_kwargs,
    "algodisco.providers.llm.EnsembleLLM": _preprocess_ensemble_llm_kwargs,
}


def preprocess_component_kwargs(
    class_path: str | None,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Apply optional config preprocessing for classes with richer YAML shapes."""
    if class_path is None:
        return kwargs

    preprocessor = _COMPONENT_KWARGS_PREPROCESSORS.get(class_path)
    if preprocessor is None:
        return kwargs
    return preprocessor(kwargs)
