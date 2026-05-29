# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import abc
import copy
import dataclasses
import math
import os
from typing import Union, List, Optional, Literal
from algodisco.base.algo import AlgoProto


@dataclasses.dataclass()
class SearchConfigBase:
    max_samples: int = dataclasses.field(kw_only=True)
    language: str = dataclasses.field(default="python", kw_only=True)
    num_samplers: Union[int, Literal["auto"]] = dataclasses.field(
        default="auto", kw_only=True
    )
    num_evaluators: Union[int, Literal["auto"]] = dataclasses.field(
        default="auto", kw_only=True
    )

    def __post_init__(self):
        # Update num_samplers
        if self.num_samplers == "auto":
            cpu_count = os.cpu_count() or 1
            self.num_samplers = max(1, cpu_count // 2)

        # Update num_evaluators
        if self.num_evaluators == "auto":
            cpu_count = os.cpu_count() or 1
            self.num_evaluators = max(1, cpu_count // 4)


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

    @abc.abstractmethod
    def current_num_samples(self) -> int:
        """Returns the current number of samples generated."""
        pass

    @abc.abstractmethod
    def get_top_k_algos(self, k: int) -> List[AlgoProto]:
        pass

    def _get_top_k_algos_from_list(
        self, algos: List[AlgoProto], k: int
    ) -> List[AlgoProto]:
        """Return deep-copied algorithms sorted by score descending."""
        if k <= 0:
            return []

        scored_algos = []
        for algo in algos:
            if algo.score is None:
                continue
            try:
                if not math.isfinite(algo.score):
                    continue
            except (TypeError, ValueError):
                continue
            scored_algos.append(algo)
        top_algos = sorted(scored_algos, key=lambda algo: algo.score, reverse=True)[:k]
        return [copy.deepcopy(algo) for algo in top_algos]

    def _copy_algo_for_storage(
        self,
        algo: AlgoProto,
        *,
        drop_metadata_keys: Optional[List[str]] = None,
    ) -> AlgoProto:
        """Return a deep copy suitable for long-lived search state."""
        stored_algo = copy.deepcopy(algo)
        keys_to_drop = ["parents"]
        if drop_metadata_keys:
            keys_to_drop.extend(drop_metadata_keys)
        for key in keys_to_drop:
            stored_algo.pop(key, None)
        return stored_algo

    @abc.abstractmethod
    def get_config(self) -> SearchConfigBase:
        """Returns the current search configuration."""
        pass

    def finish(self):
        """Terminate resources after searching."""
        if hasattr(self, "_logger"):
            self._logger.finish()
