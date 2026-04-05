# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from abc import ABC, abstractmethod
from typing import TypedDict


class EvalResult(TypedDict):
    """The result of an evaluation.

    This shared result type is intentionally minimal. It only models the one
    key that every evaluator must produce directly: ``score``.

    Evaluators can still return extra keys at runtime, and method-specific
    evaluators can define ``TypedDict`` subclasses when they need typed fields
    such as ``behavior``.
    """

    score: float


class Evaluator(ABC):
    """Base class for program evaluators."""

    @abstractmethod
    def evaluate_program(self, program_str: str) -> EvalResult:
        """Evaluate a given program.

        Args:
            program_str: The raw program text.

        Returns:
            Returns the evaluation result. This should be a dictionary
            containing at least a ``score`` key.
        """
        raise NotImplementedError(
            "Must provide an evaluator for a python program. "
            "Override this method in a subclass."
        )
