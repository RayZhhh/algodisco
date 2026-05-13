# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import math
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from algodisco.base.algo import AlgoProto


class MCTSAHDDatabase:
    """Population manager for MCTS-AHD.

    The MCTS tree stores the full historical search structure, while this
    database only keeps the current elite population used by operators such as
    ``e2``. That split mirrors the original method's intent:

    - the tree keeps search history and branching structure;
    - the database keeps a compact set of strong candidates for parent sampling.
    """

    def __init__(self, pop_size: int):
        """Initialize an empty population manager.

        Args:
            pop_size: Maximum number of elite algorithms to keep.
        """
        self._pop_size = pop_size
        self._population: List[AlgoProto] = []
        self._lock = threading.RLock()

    def __len__(self) -> int:
        """Return the number of algorithms currently stored."""
        with self._lock:
            return len(self._population)

    @property
    def population(self) -> List[AlgoProto]:
        """Return a shallow copy of the current elite population."""
        with self._lock:
            return list(self._population)

    def has_duplicate(
        self,
        algo: AlgoProto | None = None,
        *,
        program: Optional[str] = None,
    ) -> bool:
        """Check whether the population already contains a duplicate candidate.

        Duplicates are defined by identical code text.

        Treating identical scores as duplicates sounds conservative, but with
        coarse evaluators it suppresses many structurally different programs
        that happen to land on the same score. That in turn keeps MCTS-AHD in
        its prompt-heavy initialization phase for much longer than intended.

        Args:
            algo: Optional candidate whose program will be checked.
            program: Explicit program text to check. Used when ``algo`` is not
                provided or when only program-level duplicate checking is needed.

        Returns:
            ``True`` if a duplicate is already present, otherwise ``False``.
        """
        if algo is not None:
            program = algo.program

        with self._lock:
            for existing in self._population:
                if program and str(existing.program) == str(program):
                    return True
        return False

    def register_algo(self, algo: AlgoProto) -> bool:
        """Register one algorithm into the elite population.

        The candidate is accepted only if it has a finite score and is not a
        duplicate by program. When accepted, the population is trimmed
        immediately so the search always samples parents from the latest elite set.

        Args:
            algo: Candidate to register.

        Returns:
            ``True`` if the candidate entered the population, otherwise ``False``.
        """
        if algo is None:
            return False
        if algo.score is None:
            return False
        try:
            if not math.isfinite(algo.score):
                return False
        except (TypeError, ValueError):
            return False

        with self._lock:
            if self.has_duplicate(algo):
                return False

            self._population.append(algo)
            self._survival()
            return True

    def _survival(self) -> None:
        """Keep only the top ``pop_size`` algorithms by score."""
        # The population is intentionally sorted descending because AlgoDisco
        # assumes larger scores are better across search methods.
        self._population.sort(key=lambda algo: algo.score, reverse=True)
        if len(self._population) > self._pop_size:
            self._population = self._population[: self._pop_size]

    def select_algos(
        self,
        k: int,
        *,
        exclude_programs: Optional[List[str]] = None,
    ) -> List[AlgoProto]:
        """Select up to ``k`` elite algorithms with rank-based sampling.

        Args:
            k: Number of algorithms requested.
            exclude_programs: Optional program strings that should not be
                sampled. This is useful for operators that require a distinct
                partner, such as ``e2``.

        Returns:
            A list of selected algorithms. The list may be shorter than ``k`` if
            the population is too small after exclusions.
        """
        exclude_programs = exclude_programs or []
        excluded_program_set = set(map(str, exclude_programs))
        with self._lock:
            valid_algos = [
                algo
                for algo in self._population
                if math.isfinite(algo.score)
                and str(algo.program) not in excluded_program_set
            ]
            if not valid_algos:
                return []

            ranked_algos = sorted(valid_algos, key=lambda algo: algo.score, reverse=True)
            num_ranked = len(ranked_algos)
            # Rank-based probabilities keep sampling biased toward strong
            # algorithms without collapsing to a deterministic top-k policy.
            probabilities = np.array(
                [1.0 / (rank + 1 + num_ranked) for rank in range(num_ranked)],
                dtype=float,
            )
            probabilities /= probabilities.sum()

            indices = np.random.choice(
                num_ranked,
                size=min(k, num_ranked),
                replace=False,
                p=probabilities,
            )
            return [ranked_algos[index] for index in indices]

    def get_best_score(self) -> float:
        """Return the best score in the current population."""
        with self._lock:
            if not self._population:
                return -float("inf")
            return max(algo.score for algo in self._population)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the elite population for logging."""
        with self._lock:
            return {"population": [algo.to_dict() for algo in self._population]}
