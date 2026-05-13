# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import math
import random
import threading
from collections.abc import Sequence

from algodisco.base.llm import LanguageModel


class EnsembleLLM(LanguageModel):
    """Route each request to one backend LLM by weighted random sampling.

    This class is intentionally runtime-focused: it accepts concrete child LLM
    instances plus optional sampling weights. YAML-oriented convenience shapes
    are translated into this constructor form by the config-loading utilities
    in `algodisco.common`.
    """

    def __init__(
        self,
        llms: Sequence[LanguageModel],
        probabilities: Sequence[float] | None = None,
        random_seed: int | None = None,
    ):
        """Initialize an ensemble of language models.

        Args:
            llms: Language model instances to sample from directly.
            probabilities: Optional sampling weights aligned with `llms`.
                If omitted, each model is sampled uniformly.
            random_seed: Optional seed for deterministic routing in tests or
                controlled experiments.

        Raises:
            ValueError: If the configuration is ambiguous or invalid.
            TypeError: If ensemble members are not language models or weights
                are malformed.
        """
        super().__init__()

        self._llms = list(llms)
        if not self._llms:
            raise ValueError("EnsembleLLM requires at least one language model.")

        for index, llm in enumerate(self._llms):
            if not isinstance(llm, LanguageModel):
                raise TypeError(
                    f"Item at index {index} is not a LanguageModel: {type(llm)!r}"
                )

        self._probabilities = self._normalize_probabilities(
            probabilities=probabilities,
            num_models=len(self._llms),
        )
        self._rng = random.Random(random_seed)
        # Sampling can happen from multiple worker threads during search.
        self._lock = threading.Lock()

    @property
    def llms(self) -> list[LanguageModel]:
        """Return a shallow copy of the child LLM list."""
        return list(self._llms)

    @property
    def probabilities(self) -> list[float]:
        """Return the normalized sampling probabilities."""
        return list(self._probabilities)

    def _normalize_probabilities(
        self,
        probabilities: Sequence[float] | None,
        num_models: int,
    ) -> list[float]:
        """Validate and normalize sampling probabilities."""
        if num_models <= 0:
            raise ValueError("num_models must be positive.")

        if probabilities is None:
            return [1.0 / num_models] * num_models

        normalized = [float(prob) for prob in probabilities]
        if len(normalized) != num_models:
            raise ValueError(
                "The number of probabilities must match the number of language models."
            )

        for index, prob in enumerate(normalized):
            if not math.isfinite(prob):
                raise ValueError(
                    f"Probability at index {index} must be a finite number."
                )
            if prob < 0:
                raise ValueError(
                    f"Probability at index {index} must be non-negative."
                )

        total = sum(normalized)
        if total <= 0:
            raise ValueError("At least one probability must be positive.")

        # Users may provide unnormalized weights such as [1, 3, 6].
        return [prob / total for prob in normalized]

    def _choose_llm(self) -> LanguageModel:
        """Sample one child LLM according to the normalized weights."""
        with self._lock:
            return self._rng.choices(
                self._llms,
                weights=self._probabilities,
                k=1,
            )[0]

    def chat_completion(
        self,
        message,
        max_tokens,
        timeout_seconds,
        *args,
        **kwargs,
    ):
        """Forward a chat completion request to one sampled backend LLM."""
        return self._choose_llm().chat_completion(
            message=message,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            *args,
            **kwargs,
        )

    def embedding(
        self,
        text,
        dimensions=None,
        timeout_seconds=None,
        **kwargs,
    ):
        """Forward an embedding request to one sampled backend LLM."""
        return self._choose_llm().embedding(
            text=text,
            dimensions=dimensions,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )

    def close(self):
        """Close each unique child LLM once."""
        # Deduplicate by object identity in case the same provider instance is reused.
        for llm in {id(llm): llm for llm in self._llms}.values():
            llm.close()

    def reload(self):
        """Reload each unique child LLM once."""
        for llm in {id(llm): llm for llm in self._llms}.values():
            llm.reload()
