# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import dataclasses
import logging
import random
import threading
import time
import traceback
from typing import Optional, List, Any, Dict, Literal
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import numpy as np

from algodisco.base.algo import AlgoProto
from algodisco.methods.algobleu_search.similarity_calculator import AlgoSimCalculator


@dataclasses.dataclass
class AlgoDatabaseConfig:
    algo_sim_calculator: AlgoSimCalculator = AlgoSimCalculator()

    # --- Island specifications ---
    n_islands: int = 10
    island_capacity: Optional[int] = 100  # None means an endless large island

    # --- Selection parameters ---
    selection_exploitation_intensity: float = 1.0

    # --- Algo registration acceleration parameters ---
    num_sim_caculator_workers: int = 1
    async_register: bool = True

    # --- Multi-objective selection and survival ---
    island_selection_mechanism: Literal["single_obj", "multi_obj"] = "single_obj"
    island_survival_mechanism: Literal["single_obj", "multi_obj"] = "single_obj"
    multi_obj_survival_topk: int = 1
    multi_obj_score_rank_weight: float = 0.5

    # --- Weights for similarity calculation ---
    ast_dfg_weight: float = 1.0
    embedding_weight: float = 1.0
    behavioral_weight: float = 1.0

    def __post_init__(self):
        if self.island_capacity is not None:
            assert (
                self.multi_obj_survival_topk <= self.island_capacity
            ), "multi_obj_survival_topk must be <= island_capacity"

        assert (
            0 <= self.multi_obj_score_rank_weight <= 1.0
        ), "multi_obj_score_rank_weight must be between 0 and 1."


def _get_ranks(values: List[float] | Any, higher_is_better: bool = True) -> np.ndarray:
    """Returns the 1-based rank of each item. 1 is best."""
    values = np.array(values)
    # argsort gives indices that sort the array
    sorted_indices = np.argsort(values)

    if higher_is_better:
        sorted_indices = sorted_indices[::-1]

    # To get ranks for original items:
    # ranks[sorted_indices[i]] = i + 1
    n = len(values)
    ranks = np.empty(n, dtype=int)
    ranks[sorted_indices] = np.arange(1, n + 1)

    return ranks


def _rank_based_selection(
    scores: List[float], choices: List[Any], k: int, exploitation_intensity: float = 1.0
) -> List[Any]:
    """Selects k items based on rank, with higher scores being more likely.

    The selection probability for each item $i$ is given by
    $p_i = \frac{r_i^{-\alpha}}{\sum_{j=1}^n r_j^{-\alpha}}$,
    where $r_i$ is the rank of item $i$ (1 for the highest score) and $\alpha$
    (exploitation_intensity) controls the selection pressure.

    Args:
        scores: A list of scores corresponding to the choices.
        choices: A list of items to choose from.
        k: The number of items to select.
        exploitation_intensity: A non-negative float controlling the selection
            pressure.
            - If 0, sampling is uniform (all items have equal probability).
            - As it approaches infinity, it implements hill-climbing
              (only the top-ranked item is selected).

    Returns:
        A list of k selected items.
    """
    if len(scores) != len(choices):
        raise ValueError("Length of scores and choices must be the same.")
    if k > len(choices):
        raise ValueError("k cannot be greater than the number of choices.")
    if exploitation_intensity < 0:
        raise ValueError("exploitation_intensity cannot be negative.")

    # Calculate ranks for all items (1-based, 1 is best)
    ranks = _get_ranks(scores, higher_is_better=True)

    # Calculate probabilities based on the provided formula
    if exploitation_intensity == 0:
        probabilities = np.ones_like(ranks, dtype=float)  # Uniform sampling
    else:
        probabilities = ranks ** (-exploitation_intensity)
    probabilities /= np.sum(probabilities)

    # Select k items based on rank probabilities
    selected_indices = np.random.choice(
        len(choices), size=k, p=probabilities, replace=False
    )
    selected_items = [choices[i] for i in selected_indices]

    return selected_items


def _compute_avg_sim_for_island(
    algo: AlgoProto,
    island_algos: List[AlgoProto],
    sim_calculator: AlgoSimCalculator,
    weights: Dict[str, float],
) -> tuple[float, dict[str, float], dict[str, float]]:
    """Calculates the average similarity for a candidate algorithm against an island."""

    if not island_algos:
        return 0.0, {}, {}

    similarities = []

    # The sim cache records {k: "target algo_proto_id", v: "similarity between algo and target algo"}
    # Sim cache is used for calculating the dissimilarity value for two algos within same islands,
    # avoiding redundant re-calculation
    sim_cache = {}

    # Timings are recorded for debug
    # Sometimes computing similarity is time-consuming while registering algorithms
    total_timings = {}

    for island_algo in island_algos:
        try:
            sim, timings = sim_calculator.calculate_sim(
                algo,
                island_algo,
                weights=weights,
            )
            # Skip unexpected value encountered
            # Set the similarity to 0.0
            if np.isnan(sim) or np.isinf(sim):
                sim = 0.0
            # Aggregate timings
            for k, v in timings.items():
                total_timings[k] = total_timings.get(k, 0.0) + v
        except Exception:
            logging.error(traceback.format_exc())
            # Set the similarity to 0.0 if getting an exception
            sim = 0.0

        similarities.append(sim)
        sim_cache[island_algo.algo_id] = sim

    return float(np.mean(similarities)), total_timings, sim_cache


def _get_sim_algo(algo1, algo2, sim_calculator: AlgoSimCalculator, weights) -> float:
    # We first try to get similarity from sim cache to avoid re-calculation
    if algo1.algo_id == algo2.algo_id:
        return 1.0

    sim_cache1 = algo1.get("sim_cache", {})
    sim_cache2 = algo2.get("sim_cache", {})

    if algo1.algo_id in sim_cache2:
        sim = sim_cache2[algo1.algo_id]
    elif algo2.algo_id in sim_cache1:
        sim = sim_cache1[algo2.algo_id]
    else:
        # If similarity cannot be found, then calculate
        try:
            sim, _ = sim_calculator.calculate_sim(
                algo1,
                algo2,
                weights=weights,
            )
            # Assign the similarity to zero for strange value
            if sim is None or np.isnan(sim) or np.isinf(sim):
                sim = 0.0
        except:  # noqa
            # Assign the similarity to zero when encountering exception
            sim = 0.0

        # Save the results to the similarity cache
        if "sim_cache" not in algo1.metadata:
            algo1["sim_cache"] = {}
        if "sim_cache" not in algo2.metadata:
            algo2["sim_cache"] = {}
        algo1["sim_cache"][algo2.algo_id] = sim
        algo2["sim_cache"][algo1.algo_id] = sim

    return sim


class AlgoDatabase:
    def __init__(
        self,
        algo_database_config: AlgoDatabaseConfig = AlgoDatabaseConfig(),
        islands: List["AlgoIsland"] = None,
    ):
        """Initializes the AlgoDatabase.

        Args:
            algo_database_config: Configuration for the algorithm database.
            islands: An optional list of pre-initialized AlgoIsland instances.
                     If None, `n_islands` new AlgoIsland instances are created
                     based on `algo_database_config`.
        """
        self.algo_database_config = algo_database_config

        # Extract weights from config
        self._weights = {
            "ast": algo_database_config.ast_dfg_weight,
            "embedding": algo_database_config.embedding_weight,
            "behavioral": algo_database_config.behavioral_weight,
        }

        if islands is not None:
            self.islands: List[AlgoIsland] = islands
        else:
            self.islands: List[AlgoIsland] = [
                AlgoIsland(
                    sim_calculator=algo_database_config.algo_sim_calculator,
                    island_capacity=algo_database_config.island_capacity,
                    exploitation_intensity=algo_database_config.selection_exploitation_intensity,
                    weights=self._weights,
                    selection_mechanism=algo_database_config.island_selection_mechanism,
                    survival_mechanism=algo_database_config.island_survival_mechanism,
                    multi_obj_survival_topk=algo_database_config.multi_obj_survival_topk,
                    multi_obj_score_rank_weight=algo_database_config.multi_obj_score_rank_weight,
                )
                for _ in range(algo_database_config.n_islands)
            ]
        self._lock = threading.RLock()
        self._last_reset_time = time.time()

        # Executor for coordinating the registration process (running in a background thread)
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Executor for CPU-bound similarity calculations (running in background processes)
        self._process_executor = ProcessPoolExecutor(
            max_workers=self.algo_database_config.num_sim_caculator_workers
        )

    def register_algo(self, algo: AlgoProto):
        """Registers the given algorithm to the most similar island asynchronously.

        This method submits the registration task to a background thread pool, allowing
        the caller to proceed immediately. The background task handles similarity
        calculation (utilizing multiple processes) and then acquires the
        lock to place the algorithm into the chosen island.

        Args:
            algo: The algorithm prototype to register.
        """
        future = self._executor.submit(self._register_algo_worker, algo)
        if not self.algo_database_config.async_register:
            future.result()

    def _register_algo_worker(self, algo: AlgoProto):
        """Worker method for asynchronous algorithm registration."""
        if algo.score is None or algo["behavior"] is None:
            return

        # Snapshot islands for calculation to avoid holding lock during heavy calc.
        with self._lock:
            if not self.islands:
                return

            # Prefer empty islands to ensure diversity and exploration.
            empty_island_indices = [
                i for i, island in enumerate(self.islands) if not island
            ]
            if empty_island_indices:
                chosen_island_index = random.choice(empty_island_indices)
                self.islands[chosen_island_index].register_algo(algo)
                self.restart_database()
                return

            # Take a snapshot of islands for similarity calculation
            islands_snapshot = list(self.islands)

        # Calculate similarity against each island in parallel using processes
        futures = []
        for island in islands_snapshot:
            # Pass only data needed for calculation to picklable worker
            futures.append(
                self._process_executor.submit(
                    _compute_avg_sim_for_island,
                    algo,
                    island.algorithms,
                    self.algo_database_config.algo_sim_calculator,
                    self._weights,
                )
            )

        island_results = [f.result() for f in futures]
        island_similarities = [res[0] for res in island_results]
        island_sim_cache = [res[2] for res in island_results]

        # Aggregate timings across all islands
        all_timings = {}
        for _, timings, _ in island_results:
            for k, v in timings.items():
                all_timings[k] = all_timings.get(k, 0.0) + v

        if all_timings:
            timing_str = ", ".join([f"{k}: {v:.4f}s" for k, v in all_timings.items()])
            # logging.info(
            #     f">>> [{self.__class__.__name__}] "
            #     f"Total Similarity Calculation Times (Register): {timing_str}",
            # )

        # Handle potential NaNs in similarities
        clean_similarities = [
            (sim if not np.isnan(sim) else -float("inf")) for sim in island_similarities
        ]

        max_sim = max(clean_similarities)
        candidate_indices = [
            i for i, sim in enumerate(clean_similarities) if sim == max_sim
        ]

        chosen_island_index = random.choice(candidate_indices)
        # Preserve the sim cache for that island in the algo
        algo["sim_cache"] = island_sim_cache[chosen_island_index]

        # Re-acquire lock to place the algorithm
        with self._lock:
            # Ensure index is still valid
            if chosen_island_index < len(self.islands):
                target_island = self.islands[chosen_island_index]
                target_island.register_algo(algo)
                self.restart_database()

    def restart_database(self):
        """Resets the weaker half of islands every 3600 seconds."""
        # If a max capacity is set, we skip database restart
        if self.algo_database_config.island_capacity is not None:
            return

        with self._lock:
            if time.time() - self._last_reset_time < 3600:
                return
            self._last_reset_time = time.time()

            # Calculate the best score for each island
            island_scores = []
            for island in self.islands:
                if not island.algorithms:
                    island_scores.append(-float("inf"))
                else:
                    # Assuming higher score is better
                    island_scores.append(max(algo.score for algo in island.algorithms))

            island_scores = np.array(island_scores)

            # Sort islands by score. Add noise to break ties randomly.
            indices_sorted_by_score = np.argsort(
                island_scores + np.random.randn(len(island_scores)) * 1e-6
            )

            num_islands = len(self.islands)
            num_islands_to_reset = num_islands // 2

            reset_islands_ids = indices_sorted_by_score[:num_islands_to_reset]
            keep_islands_ids = indices_sorted_by_score[num_islands_to_reset:]

            for island_id in reset_islands_ids:
                # Reset the island
                self.islands[island_id] = AlgoIsland(
                    sim_calculator=self.algo_database_config.algo_sim_calculator,
                    island_capacity=self.algo_database_config.island_capacity,
                    exploitation_intensity=self.algo_database_config.selection_exploitation_intensity,
                    weights=self._weights,
                    multi_obj_score_rank_weight=self.algo_database_config.multi_obj_score_rank_weight,
                )

                # Copy a founder from a surviving island
                if len(keep_islands_ids) > 0:
                    founder_island_id = np.random.choice(keep_islands_ids)
                    founder_island = self.islands[founder_island_id]

                    if founder_island.algorithms:
                        # Pick the best algorithm as founder
                        founder = max(founder_island.algorithms, key=lambda x: x.score)
                        self.islands[island_id].register_algo(founder)

    def select_algos(
        self,
        num_islands: int,
        samples_per_island: int,
    ) -> List[tuple[AlgoProto, int]]:
        """Selects algorithms from the database based on two strategies.

        This method can be used for two scenarios:
        1. Select k algorithms from 1 random island: `select_algos(num_islands=1, samples_per_island=k)`
        2. Select 1 algorithm from k random islands: `select_algos(num_islands=k, samples_per_island=1)`

        This method is thread-safe.

        Args:
            num_islands: The number of different islands to sample from.
            samples_per_island: The number of algorithms to sample from each island.

        Returns:
            A list of tuples, where each tuple contains an algorithm prototype
            and the ID of the island it was selected from.
        """
        with self._lock:
            non_empty_islands_with_indices = [
                (i, island) for i, island in enumerate(self.islands) if island
            ]
            if not non_empty_islands_with_indices:
                return []

            # If k is too large, use all non-empty islands
            num_to_select = min(num_islands, len(non_empty_islands_with_indices))
            selected_islands_with_indices = random.sample(
                non_empty_islands_with_indices, num_to_select
            )

            all_selected_algos = []
            for island_id, island in selected_islands_with_indices:
                selected_algos = island.selection(k=samples_per_island)  # Todo add
                for algo in selected_algos:
                    all_selected_algos.append((algo, island_id))

            return all_selected_algos

    def get_island_stats(self) -> Dict[int, int]:
        """Returns a dictionary with the number of algorithms in each island."""
        with self._lock:
            return {i: len(island) for i, island in enumerate(self.islands)}

    def get_all_algorithms(self) -> List[AlgoProto]:
        """Gathers all algorithms from all islands in the database.
        This method is thread-safe.
        """
        all_algos: List[AlgoProto] = []
        with self._lock:
            for island in self.islands:
                all_algos.extend(island.get_all_algorithms())
        return all_algos

    def to_dict(self) -> dict[str, Any]:
        """Converts the AlgoDatabase to a dictionary."""
        return {"islands": [island.to_dict() for island in self.islands]}

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        config: AlgoDatabaseConfig,
    ) -> "AlgoDatabase":
        """Creates an AlgoDatabase from a dictionary."""
        islands = [
            AlgoIsland.from_dict(island_data, config)
            for island_data in data.get("islands", [])
        ]

        return cls(config, islands=islands)


class AlgoIsland:
    def __init__(
        self,
        sim_calculator: AlgoSimCalculator,
        island_capacity: Optional[int],
        exploitation_intensity: float,
        weights: Optional[Dict[str, float]] = None,
        selection_mechanism: Literal["single_obj", "multi_obj"] = "single_obj",
        survival_mechanism: Literal["single_obj", "multi_obj"] = "single_obj",
        multi_obj_survival_topk: int = 1,
        multi_obj_score_rank_weight: float = 0.2,
    ):
        self.sim_calculator = sim_calculator
        self.island_capacity = island_capacity
        self.algorithms: List[AlgoProto] = []
        self.all_algos: List[AlgoProto] = []  # Store all algorithms ever registered
        self.exploitation_intensity = exploitation_intensity
        self.weights = weights
        self.selection_mechanism = selection_mechanism
        self.survival_mechanism = survival_mechanism
        self.multi_obj_survival_topk = multi_obj_survival_topk
        self.multi_obj_score_rank_weight = multi_obj_score_rank_weight
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self.algorithms)

    def calculate_avg_sim_to_island(
        self,
        algo: AlgoProto,
    ) -> tuple[float, dict[str, float]]:
        """Calculates the average similarity from an algorithm to this island.

        This method is thread-safe.

        Args:
            algo: The algorithm to calculate the similarity from.

        Returns:
            A tuple containing:
            - float: The average similarity. Returns 0.0 if the island is empty.
            - dict: Aggregated timings for similarity calculations.
        """
        with self._lock:
            if not self.algorithms:
                return 0.0, {}

            similarities = []
            total_timings = {}
            for island_algo in self.algorithms:
                try:
                    sim, timings = self.sim_calculator.calculate_sim(
                        algo,
                        island_algo,
                        weights=self.weights,
                    )
                    if np.isnan(sim) or np.isinf(sim):
                        sim = 0.0

                    # Aggregate timings
                    for k, v in timings.items():
                        total_timings[k] = total_timings.get(k, 0.0) + v

                except Exception:
                    sim = 0.0
                similarities.append(sim)

            return float(np.mean(similarities)), total_timings

    def survival(self):
        """Implements a naive survival mechanism for the island.

        If the number of algorithms in the island exceeds `island_capacity`,
        only the algorithms with the highest scores are preserved, up to
        the `island_capacity` limit.
        """
        with self._lock:
            if self.island_capacity is None:
                return
            if len(self.algorithms) > self.island_capacity:
                # Sort algorithms by score in descending order and keep the top ones
                self.algorithms.sort(key=lambda algo: algo.score, reverse=True)
                self.algorithms = self.algorithms[: self.island_capacity]

    def selection(self, k: int = 1) -> List[AlgoProto]:
        with self._lock:
            if self.selection_mechanism == "single_obj" or k == 1:
                return self.single_objective_selection(k)
            else:
                return self.multi_objective_selection(k)

    def single_objective_selection(self, k: int = 1) -> List[AlgoProto]:
        """Selects k algorithms from the island using rank-based selection.

        Algorithms are selected based on their scores, with higher-scoring
        algorithms having a greater probability of being chosen. The
        `exploitation_intensity` parameter from the AlgoDatabaseConfig controls
        the steepness of this probability distribution.

        For each selected algorithm, its `num_selected` attribute is
        incremented to track its participation in the selection process.

        This method is thread-safe.

        Args:
            k: The number of algorithms to select. Defaults to 1.

        Returns:
            A list of `k` selected AlgoProto instances. If the island is empty,
            an empty list is returned.
        """
        with self._lock:
            if not self.algorithms:
                return []

            # Ensure k does not exceed the number of unique scores to guarantee score diversity
            unique_scores = set(algo.score for algo in self.algorithms)
            if k > len(unique_scores):
                k = len(unique_scores)

            # Select k algorithms with different scores
            selected_algos = []
            candidates = list(self.algorithms)

            for _ in range(k):
                if not candidates:
                    break

                scores = [algo.score for algo in candidates]
                # Select 1 algorithm from the current candidates
                picked = _rank_based_selection(
                    scores=scores,
                    choices=candidates,
                    k=1,
                    exploitation_intensity=self.exploitation_intensity,
                )[0]
                selected_algos.append(picked)

                # Remove candidates with the same score to ensure next selection has a different score
                candidates = [algo for algo in candidates if algo.score != picked.score]

            return selected_algos

    def multi_objective_selection(self, k: int = 1) -> List[AlgoProto]:
        with self._lock:
            if not self.algorithms:
                return []

            # Ensure k does not exceed the number of unique scores to guarantee score diversity
            unique_scores = set(algo.score for algo in self.algorithms)
            if k > len(unique_scores):
                k = len(unique_scores)

            # Find the best algo in this island
            best_algo = self.get_best_k_algo(1)[0]
            island_algo_protos, col_wise_sum = (
                self._cal_col_wise_sum_of_dissimilarity_mat()
            )

            combined_scores = self._get_combined_rank_score(
                island_algo_protos, col_wise_sum
            )

            # Map algorithm to its multi-objective score for selection
            algo_to_mo_score = {}
            for algo, combined_score in zip(island_algo_protos, combined_scores):
                if algo == best_algo:
                    algo_to_mo_score[algo] = float("inf")
                else:
                    algo_to_mo_score[algo] = combined_score

            # Select k algorithms with different scores
            selected_algos = []
            candidates = list(island_algo_protos)

            for _ in range(k):
                if not candidates:
                    break

                current_mo_scores = [algo_to_mo_score[algo] for algo in candidates]
                # Select an algorithm from the current candidates
                picked = _rank_based_selection(
                    scores=current_mo_scores,
                    choices=candidates,
                    k=1,
                    exploitation_intensity=self.exploitation_intensity,
                )[0]
                selected_algos.append(picked)

                # Remove candidates with the same score to ensure next selection has a different score
                candidates = [algo for algo in candidates if algo.score != picked.score]

            return selected_algos

    def register_algo(self, algo: AlgoProto):
        """Registers a new algorithm in the island.

        The new algorithm is added to the island's collection.

        This method is thread-safe.

        Args:
            algo: The AlgoProto instance to register.
        """
        with self._lock:
            self.algorithms.append(algo)
            self.all_algos.append(algo)  # Add to history

            if self.survival_mechanism == "single_obj":
                self.survival()
            else:
                self.multi_objective_survival()

    def get_all_algorithms(self) -> List[AlgoProto]:
        """Returns a list of all algorithms in the island.

        This method is thread-safe.
        """
        with self._lock:
            return list(self.algorithms)

    def get_best_k_algo(self, k: int) -> List[AlgoProto]:
        """Returns the k algorithms with the highest scores from the island.
        This method is thread-safe.

        Args:
            k: The number of algorithms to return.

        Returns:
            A list of the top k AlgoProto instances.
        """
        with self._lock:
            # Sort algorithms by score in descending order and return top k
            return sorted(
                self.algorithms,
                key=lambda algo: (
                    algo.score if algo.score is not None else -float("inf")
                ),
                reverse=True,
            )[:k]

    def to_dict(self) -> dict[str, Any]:
        """Converts the AlgoIsland to a dictionary."""
        return {
            "algorithms": [algo.to_dict() for algo in self.algorithms],
            "all_algos": [algo.to_dict() for algo in self.all_algos],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        algo_database_config: AlgoDatabaseConfig,
    ) -> "AlgoIsland":
        """Creates an AlgoIsland from a dictionary."""
        weights = {
            "ast": algo_database_config.ast_dfg_weight,
            "embedding": algo_database_config.embedding_weight,
            "behavioral": algo_database_config.behavioral_weight,
        }
        island = cls(
            sim_calculator=algo_database_config.algo_sim_calculator,
            island_capacity=algo_database_config.island_capacity,
            exploitation_intensity=algo_database_config.selection_exploitation_intensity,
            weights=weights,
            multi_obj_score_rank_weight=algo_database_config.multi_obj_score_rank_weight,
        )
        island.algorithms = [
            AlgoProto.from_dict(algo_data) for algo_data in data["algorithms"]
        ]

        # Restore all_algos
        if "all_algos" in data:
            island.all_algos = [
                AlgoProto.from_dict(algo_data) for algo_data in data["all_algos"]
            ]
        else:
            # Fallback for old data: assume current algorithms are the history
            island.all_algos = list(island.algorithms)

        return island

    def _cal_col_wise_sum_of_dissimilarity_mat(self):
        """Calculates the column-wise sum of the dissimilarity matrix, referenced from MEoH:
            - Yao et al. "Multi-objective Evolution of Heuristic Using Large Language Model". AAAI 2025.

        It calculates a score for each individual based on:
        1. Dominance in objective space (Fitness score).
        2. Dissimilarity in search space (Code similarity).

        Logic:
        - Score[j] = Sum( -1 * Similarity(i, j) ) for all i that dominate j.
        - Individuals that are dominated by 'clones' (high similarity) get large negative penalties.
        - Individuals that are dominated by 'strangers' (low similarity) get small penalties.
        - Non-dominated individuals get a score of 0.

        Returns:
            The current algos and their score.
        """
        with self._lock:
            # Find the best algo in this island
            best_algo = self.get_best_k_algo(1)[0]
            island_algo_protos: List[AlgoProto] = list(self.algorithms)

            # Calculate the two obj score
            for algo_proto in island_algo_protos:
                if algo_proto == best_algo:
                    sim = 1.0
                else:
                    sim = _get_sim_algo(
                        algo_proto,
                        best_algo,
                        sim_calculator=self.sim_calculator,
                        weights=self.weights,
                    )
                algo_proto["sim"] = sim
                algo_proto["two_obj_arr"] = np.array(
                    [-algo_proto.score, algo_proto["sim"]]
                )

            N = len(island_algo_protos)
            S = np.zeros(shape=(N, N))

            def is_dominated(i, j):
                if (
                    island_algo_protos[i]["two_obj_arr"]
                    < island_algo_protos[j]["two_obj_arr"]
                ).all():
                    return True
                else:
                    return False

            # Calculate dissimilarity score matrix
            # Reference: 'Yao et. al. Multi-objective Evolution of Heuristic Using Large Language Model.'
            for i in range(N):
                for j in range(i + 1, N):
                    if is_dominated(i, j):
                        S[i, j] = -_get_sim_algo(
                            island_algo_protos[i],
                            island_algo_protos[j],
                            sim_calculator=self.sim_calculator,
                            weights=self.weights,
                        )
                    elif is_dominated(j, i):
                        S[j, i] = -_get_sim_algo(
                            island_algo_protos[i],
                            island_algo_protos[j],
                            sim_calculator=self.sim_calculator,
                            weights=self.weights,
                        )
            # Calculate column-wise sum
            col_wise_sum = S.sum(0)
            return island_algo_protos, col_wise_sum

    def _get_combined_rank_score(
        self, island_algo_protos: List[AlgoProto], col_wise_sum: np.ndarray
    ) -> np.ndarray:
        """Combines the rank of the column-wise sum and the rank of the fitness score.

        The combined score is calculated as:
        Combined = w * Rank(Fitness) + (1 - w) * Rank(MO_Score)
        where w is `multi_obj_score_rank_weight`.
        Both ranks are normalized to [0, 1] (higher is better).

        Args:
            island_algo_protos: The list of algorithms.
            col_wise_sum: The column-wise sum of the dissimilarity matrix (MO score).

        Returns:
            A numpy array of combined scores.
        """
        if not island_algo_protos:
            return np.array([])

        scores = [
            algo.score if algo.score is not None else -float("inf")
            for algo in island_algo_protos
        ]

        r_fitness = _get_ranks(scores, higher_is_better=True)
        # Higher col_wise_sum (closer to 0) is better
        r_mo = _get_ranks(col_wise_sum, higher_is_better=True)

        n = len(island_algo_protos)
        if n <= 1:
            return np.array([1.0])

        # Normalize: (N - rank) / (N - 1) -> 1.0 (Best) to 0.0 (Worst)
        # Since rank 1 is best, N - 1 is highest possible numerator (N - 1)
        norm_r_fitness = (n - r_fitness) / (n - 1)
        norm_r_mo = (n - r_mo) / (n - 1)

        w = self.multi_obj_score_rank_weight
        combined_score = w * norm_r_fitness + (1 - w) * norm_r_mo
        return combined_score

    def multi_objective_survival(self) -> None:
        """Implements the dominance-dissimilarity survival mechanism from MEoH.
        It calculates a score for each individual based on:
        1. Dominance in objective space (Fitness score).
        2. Dissimilarity in search space (Code similarity).

        Logic:
        - Score[j] = Sum( -1 * Similarity(i, j) ) for all i that dominate j.
        - Individuals that are dominated by 'clones' (high similarity) get large negative penalties.
        - Individuals that are dominated by 'strangers' (low similarity) get small penalties.
        - Non-dominated individuals get a score of 0.

        The population is sorted by this score descending, keeping the top `island_capacity`.
        """
        with self._lock:
            if (
                self.island_capacity is None
                or len(self.algorithms) < self.island_capacity * 2
            ):
                return

            _start_time = time.time()

            # Find the best algo in this island
            topk = self.multi_obj_survival_topk
            topk_algo = self.get_best_k_algo(topk)

            island_algo_protos, col_wise_sum = (
                self._cal_col_wise_sum_of_dissimilarity_mat()
            )

            combined_scores = self._get_combined_rank_score(
                island_algo_protos, col_wise_sum
            )

            # Preserve the 'survival score' in each algo
            for algo, combined_score in zip(island_algo_protos, combined_scores):
                if algo in topk_algo:
                    algo["survival_score"] = float("inf")
                else:
                    algo["survival_score"] = combined_score

            # Sort based on the score and preserve top-island-capacity algos
            sorted_algo = sorted(
                island_algo_protos, key=lambda algo: algo["survival_score"]
            )[::-1]
            self.algorithms = sorted_algo[: self.island_capacity]

            # logging.info(
            #     f">>> [{self.__class__.__name__}] "
            #     f"Multi-objective survival time: {time.time() - _start_time}",
            # )
