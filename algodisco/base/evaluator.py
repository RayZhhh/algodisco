# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from abc import ABC, abstractmethod
from typing import TypedDict, TypeVar, Generic, Optional, NotRequired


class EvalResult(TypedDict):
    """The result of an evaluation.

    Must contain at least a 'score' key. Subclasses can add more keys.
    """
    score: float
    execution_time: NotRequired[Optional[float]]
    error_msg: NotRequired[Optional[str]]


T = TypeVar("T", bound=EvalResult)


class Evaluator(ABC, Generic[T]):
    """Base class for program evaluators."""

    @abstractmethod
    def evaluate_program(self, program_str: str) -> T:
        """Evaluate a given program.

        Args:
            program_str: The raw program text.

        Returns:
            Returns the evaluation result. This should be a dictionary
            containing at least a 'score' key.
        """
        raise NotImplementedError(
            "Must provide an evaluator for a python program. "
            "Override this method in a subclass."
        )
