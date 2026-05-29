# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from __future__ import annotations

import math
import copy
import random
import threading
from typing import Any, Dict, List, Optional, Tuple

from algodisco.base.algo import AlgoProto


class ReEvoDatabase:
    """Elite-population manager for iterative ReEvo."""

    def __init__(self, pop_size: int):
        """Initialize an empty bounded elite population."""
        self._pop_size = pop_size
        self._population: List[AlgoProto] = []
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._population)

    @property
    def population(self) -> List[AlgoProto]:
        """Return a shallow copy of the current elite population."""
        with self._lock:
            return list(self._population)

    def get_elitist(self) -> Optional[AlgoProto]:
        """Return the current best valid algorithm."""
        with self._lock:
            valid = [algo for algo in self._population if _is_valid_score(algo.score)]
            if not valid:
                return None
            return max(valid, key=lambda algo: algo.score)

    def register_algo(self, algo: AlgoProto) -> bool:
        """Insert one candidate into the elite population if it survives."""
        if algo is None or not _is_valid_score(algo.score):
            return False
        algo_copy = copy.deepcopy(algo)
        algo_copy.pop("parents", None)

        with self._lock:
            for index, existing in enumerate(self._population):
                if str(existing.program) == str(algo_copy.program):
                    # Code-level duplicates keep only the stronger refreshed
                    # evaluation so the population does not fragment.
                    if algo_copy.score >= existing.score:
                        self._population[index] = algo_copy
                        self._survival()
                        return any(
                            item.algo_id == algo_copy.algo_id
                            for item in self._population
                        )
                    return False
                if existing.score == algo_copy.score:
                    # ReEvo intentionally avoids keeping many score-tied elites
                    # because its prompts already compare only one parent pair.
                    return False

            self._population.append(algo_copy)
            self._survival()
            return any(item.algo_id == algo_copy.algo_id for item in self._population)

    def _survival(self) -> None:
        """Keep only the top-scoring `pop_size` algorithms."""
        self._population.sort(key=lambda item: item.score, reverse=True)
        if len(self._population) > self._pop_size:
            self._population = self._population[: self._pop_size]

    def select_pair(self, mode: str) -> Optional[Tuple[AlgoProto, AlgoProto]]:
        """Select one parent pair whose scores are intentionally different."""
        with self._lock:
            valid = [algo for algo in self._population if _is_valid_score(algo.score)]
            if len(valid) < 2:
                return None

            ranked = sorted(valid, key=lambda algo: algo.score, reverse=True)
            for _ in range(100):
                # The iterative ReEvo variant wants a clear "better vs worse"
                # contrast for short-term reflection, so equal-score pairs are
                # rejected and resampled.
                if mode == "rank":
                    pair = _weighted_pair(ranked)
                else:
                    pair = tuple(random.sample(ranked, 2))
                if pair[0].score != pair[1].score:
                    return pair
            return None

    def get_best_score(self) -> float:
        """Return the best score in the current population."""
        with self._lock:
            elitist = self.get_elitist()
            return elitist.score if elitist is not None else -float("inf")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the elite population for logging."""
        with self._lock:
            return {"population": [algo.to_dict() for algo in self._population]}


def _is_valid_score(score: Optional[float]) -> bool:
    """Return whether `score` is finite and therefore searchable."""
    if score is None:
        return False
    try:
        return math.isfinite(score)
    except (TypeError, ValueError):
        return False


def _weighted_pair(population: List[AlgoProto]) -> Tuple[AlgoProto, AlgoProto]:
    """Sample two distinct parents with a mild bias toward better ranks."""
    n = len(population)
    weights = [1.0 / (rank + 1 + n) for rank in range(n)]
    chosen_indices: List[int] = []
    available_indices = list(range(n))
    available_weights = list(weights)

    for _ in range(2):
        total = sum(available_weights)
        normalized = [weight / total for weight in available_weights]
        # Sampling without replacement keeps the pair genuinely comparative
        # rather than accidentally selecting the same parent twice.
        pick = random.choices(available_indices, weights=normalized, k=1)[0]
        chosen_indices.append(pick)
        remove_index = available_indices.index(pick)
        available_indices.pop(remove_index)
        available_weights.pop(remove_index)

    return population[chosen_indices[0]], population[chosen_indices[1]]
