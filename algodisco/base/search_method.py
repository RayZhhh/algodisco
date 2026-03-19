# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import abc
from typing import Union, List, Optional
from algodisco.base.algo import AlgoProto


class IterativeSearchBase(abc.ABC):
    """
    Abstract base class for iterative algorithm search methods.
    Defines a standard lifecycle: Initialize -> (Select/Prompt -> Generate -> Evaluate -> Register) loop.
    """

    @abc.abstractmethod
    def initialize(self) -> None:
        """Initializes the search process (e.g., evaluating the initial template)."""
        pass

    @abc.abstractmethod
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Selects candidates from the database and constructs a prompt."""
        pass

    @abc.abstractmethod
    def generate(self, selection: AlgoProto) -> Union[AlgoProto, List[AlgoProto]]:
        """Generates new algorithm candidate(s) based on the selection/prompt."""
        pass

    @abc.abstractmethod
    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """Extracts algorithm code from the LLM response text."""
        pass

    @abc.abstractmethod
    def evaluate(
        self, candidates: Union[AlgoProto, List[AlgoProto]]
    ) -> Union[AlgoProto, List[AlgoProto]]:
        """Evaluates the generated algorithm candidate(s)."""
        pass

    @abc.abstractmethod
    def register(self, results: Union[AlgoProto, List[AlgoProto]]) -> None:
        """Registers the evaluated result(s) in the database and logger."""
        pass

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        """Returns True if the search termination criteria are met."""
        pass
