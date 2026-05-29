# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from __future__ import annotations

import hashlib
import math
import copy
import random
import re
import statistics
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from algodisco.base.algo import AlgoProto


def _is_finite_score(score: Optional[float]) -> bool:
    """Return whether ``score`` is finite and therefore searchable."""
    if score is None:
        return False
    try:
        return math.isfinite(score)
    except (TypeError, ValueError):
        return False


def _euclidean_distance(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute Euclidean distance between two vectors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)))


@dataclass
class PartEvoSearchContext:
    """Container describing one clustered-search decision."""

    operator: str
    cluster_id: int
    parents: List[AlgoProto]


class PartEvoArchive:
    """External archive used by the ``se`` operator.

    The archive separates strong global attempts into two tiers:

    - ``elites``: top-performing reference algorithms;
    - ``hard_negatives``: strong algorithms that are not currently elite.

    The summary used by ``se`` is cached because it is an auxiliary LLM call and
    should not be regenerated on every request.
    """

    def __init__(
        self,
        *,
        max_elites: int,
        max_hard_negatives: int,
        summary_update_interval: int,
    ):
        """Initialize the archive state."""
        self.max_elites = max_elites
        self.max_hard_negatives = max_hard_negatives
        self.summary_update_interval = summary_update_interval

        self.elites: List[AlgoProto] = []
        self.hard_negatives: List[AlgoProto] = []
        self._cached_summary = ""
        self._request_counter = 0
        self._has_unsummarized_updates = False
        self._lock = threading.RLock()

    def register(self, algo: AlgoProto) -> None:
        """Insert one evaluated algorithm into the archive tiers."""
        if algo is None or not _is_finite_score(algo.score):
            return

        with self._lock:
            # The archive treats identical code as the same algorithm and keeps
            # the stronger version if a refreshed one appears later.
            if self._replace_existing(self.elites, algo):
                self.elites.sort(key=lambda item: item.score, reverse=True)
                self._has_unsummarized_updates = True
                return

            if self._replace_existing(self.hard_negatives, algo):
                self.hard_negatives.sort(key=lambda item: item.score, reverse=True)
                self._has_unsummarized_updates = True
                return

            self._try_add_to_elites(algo)

    def _replace_existing(self, bucket: List[AlgoProto], algo: AlgoProto) -> bool:
        """Replace a code-duplicate inside one archive bucket if beneficial."""
        for index, existing in enumerate(bucket):
            if str(existing.program) != str(algo.program):
                continue
            if algo.score >= existing.score:
                bucket[index] = algo
            return True
        return False

    def _try_add_to_elites(self, algo: AlgoProto) -> None:
        """Insert into elites, demoting the weakest elite when necessary."""
        if len(self.elites) < self.max_elites:
            self.elites.append(algo)
            self.elites.sort(key=lambda item: item.score, reverse=True)
            self._has_unsummarized_updates = True
            return

        if algo.score > self.elites[-1].score:
            self.elites.append(algo)
            self.elites.sort(key=lambda item: item.score, reverse=True)
            demoted = self.elites.pop()
            self._try_add_to_hard_negatives(demoted)
            self._has_unsummarized_updates = True
            return

        self._try_add_to_hard_negatives(algo)

    def _try_add_to_hard_negatives(self, algo: AlgoProto) -> None:
        """Insert into hard negatives if the candidate is strong enough."""
        if len(self.hard_negatives) < self.max_hard_negatives:
            self.hard_negatives.append(algo)
            self.hard_negatives.sort(key=lambda item: item.score, reverse=True)
            self._has_unsummarized_updates = True
            return

        if algo.score > self.hard_negatives[-1].score:
            self.hard_negatives.append(algo)
            self.hard_negatives.sort(key=lambda item: item.score, reverse=True)
            self.hard_negatives = self.hard_negatives[: self.max_hard_negatives]
            self._has_unsummarized_updates = True

    def fetch_summary_context(self) -> Tuple[str, bool, Dict[str, List[AlgoProto]]]:
        """Return cached summary plus a flag indicating whether it should refresh."""
        with self._lock:
            self._request_counter += 1
            if not self.elites and not self.hard_negatives:
                return self._cached_summary, False, {}

            # Summary regeneration is demand-driven instead of eager. That keeps
            # auxiliary LLM traffic bounded even when many worker threads ask
            # for `se` prompts in a short burst.
            needs_refresh = (
                not self._cached_summary
                or (
                    self._request_counter % self.summary_update_interval == 0
                    and self._has_unsummarized_updates
                )
            )
            context = {
                "elites": list(self.elites[: min(4, len(self.elites))]),
                "hard_negatives": list(
                    self.hard_negatives[: min(4, len(self.hard_negatives))]
                ),
            }
            return self._cached_summary, needs_refresh, context

    def update_summary(self, summary_text: Optional[str]) -> None:
        """Update the cached archive summary after an auxiliary LLM call."""
        if not summary_text:
            return
        with self._lock:
            self._cached_summary = summary_text.strip()
            self._has_unsummarized_updates = False

    @property
    def summary(self) -> str:
        """Return the cached global summary."""
        with self._lock:
            return self._cached_summary

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the archive for logging."""
        with self._lock:
            return {
                "elites": [algo.to_dict() for algo in self.elites],
                "hard_negatives": [algo.to_dict() for algo in self.hard_negatives],
                "summary": self._cached_summary,
                "request_counter": self._request_counter,
            }


class PartEvoCluster:
    """One local niche inside the global PartEvo population."""

    OPERATOR_SELECTION_MAP = {
        "re": "tournament",
        "se": "tournament",
        "cn": "tournament",
        "lge": "random",
    }

    def __init__(
        self,
        cluster_id: int,
        max_pop_size: int,
        operator_cycle: List[str],
        population: Optional[List[AlgoProto]] = None,
    ):
        """Initialize one cluster with an operator cycle and local population."""
        self.cluster_id = cluster_id
        self.max_pop_size = max_pop_size
        self._operator_cycle = list(operator_cycle)
        self._operator_index = 0
        self._population = list(population or [])
        self._history_best_score = (
            max((algo.score for algo in self._population if _is_finite_score(algo.score)), default=-float("inf"))
        )
        self.cumulative_non_improvement_count = 0
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._population)

    @property
    def population(self) -> List[AlgoProto]:
        """Return a shallow copy of the local population."""
        with self._lock:
            return list(self._population)

    def get_best(self) -> Optional[AlgoProto]:
        """Return the highest-scoring local algorithm."""
        with self._lock:
            valid = [algo for algo in self._population if _is_finite_score(algo.score)]
            if not valid:
                return None
            return max(valid, key=lambda algo: algo.score)

    def next_operator(self) -> str:
        """Return the next operator in the cluster-local cycle."""
        with self._lock:
            if not self._operator_cycle:
                return "re"
            operator = self._operator_cycle[self._operator_index % len(self._operator_cycle)]
            self._operator_index += 1
            return operator

    def _select_by_mode(
        self,
        population: List[AlgoProto],
        k: int,
        *,
        mode: str,
    ) -> List[AlgoProto]:
        """Select up to ``k`` local parents using a cluster-local strategy."""
        if not population or k <= 0:
            return []

        ranked = sorted(population, key=lambda algo: algo.score, reverse=True)
        if mode == "random":
            return random.sample(ranked, min(k, len(ranked)))

        if mode == "tournament":
            selected: List[AlgoProto] = []
            remaining = list(ranked)
            while remaining and len(selected) < k:
                tournament_size = min(3, len(remaining))
                contenders = random.sample(remaining, tournament_size)
                winner = max(contenders, key=lambda algo: algo.score)
                selected.append(winner)
                remaining.remove(winner)
            return selected

        return ranked[:k]

    def select_local_parents(self) -> Tuple[List[AlgoProto], str, bool]:
        """Select local parents and decide whether external help is needed."""
        operator = self.next_operator()
        mode = self.OPERATOR_SELECTION_MAP.get(operator, "tournament")
        with self._lock:
            valid = [algo for algo in self._population if _is_finite_score(algo.score)]
            if not valid:
                return [], operator, False

            local_parent_count = 1
            parents = self._select_by_mode(valid, local_parent_count, mode=mode)
            # `cn` and `lge` start from one niche-local anchor, then ask the
            # database for extra global context outside the cluster.
            need_external = operator in {"cn", "lge"}
            return parents, operator, need_external

    def register_algo(self, algo: AlgoProto) -> bool:
        """Insert one algorithm into the cluster-local population."""
        if algo is None or not _is_finite_score(algo.score):
            return False

        with self._lock:
            # Replace duplicates aggressively so stale local variants do not
            # accumulate and obscure the niche's true state. We only deduplicate
            # by code here. Same-score but structurally different candidates are
            # important for PartEvo because clustering relies on diversity.
            for index, existing in enumerate(self._population):
                if str(existing.program) != str(algo.program):
                    continue

                if algo.score >= existing.score:
                    self._population[index] = algo
                    self._update_non_improvement(algo.score)
                    self._survival()
                    return True
                return False

            self._population.append(algo)
            self._update_non_improvement(algo.score)
            self._survival()
            return True

    def _update_non_improvement(self, score: float) -> None:
        """Track whether the niche has recently improved."""
        if score > self._history_best_score + 1e-9:
            self._history_best_score = score
            self.cumulative_non_improvement_count = 0
            return
        self.cumulative_non_improvement_count += 1

    def _survival(self) -> None:
        """Keep only the strongest local individuals."""
        unique_map: Dict[str, AlgoProto] = {}
        for algo in self._population:
            code_key = str(algo.program)
            if code_key not in unique_map or algo.score >= unique_map[code_key].score:
                unique_map[code_key] = algo

        self._population = sorted(
            unique_map.values(),
            key=lambda item: item.score,
            reverse=True,
        )[: self.max_pop_size]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize one cluster for logging."""
        with self._lock:
            return {
                "cluster_id": self.cluster_id,
                "population": [algo.to_dict() for algo in self._population],
                "cumulative_non_improvement_count": self.cumulative_non_improvement_count,
            }


class PartEvoDatabase:
    """Population manager, cluster manager, and external archive for PartEvo."""

    def __init__(
        self,
        *,
        pop_size: int,
        num_clusters: int,
        operator_weights: Dict[str, int],
        use_resource_tilt: bool,
        resource_tilt_alpha: float,
        cluster_refresh_interval: int,
        archive_elite_size: int,
        archive_hard_negative_size: int,
        summary_update_interval: int,
    ):
        """Initialize the full PartEvo search state."""
        self._pop_size = pop_size
        self._num_clusters = num_clusters
        self._use_resource_tilt = use_resource_tilt
        self._resource_tilt_alpha = resource_tilt_alpha
        self._cluster_refresh_interval = cluster_refresh_interval

        # Expand operator weights into a deterministic local cycle so every
        # cluster gets a similar operator mix over time.
        self._operator_cycle: List[str] = []
        for operator in ("re", "se", "cn", "lge"):
            self._operator_cycle.extend([operator] * max(0, operator_weights.get(operator, 0)))
        if not self._operator_cycle:
            self._operator_cycle = ["re"]

        self._population: List[AlgoProto] = []
        self._clusters: Dict[int, PartEvoCluster] = {}
        self._program_to_cluster: Dict[str, int] = {}
        self._accepted_since_last_cluster = 0
        self._is_clustered = False
        self._global_best: Optional[AlgoProto] = None
        self._lock = threading.RLock()

        self.archive = PartEvoArchive(
            max_elites=archive_elite_size,
            max_hard_negatives=archive_hard_negative_size,
            summary_update_interval=summary_update_interval,
        )

    def __len__(self) -> int:
        with self._lock:
            return len(self._population)

    @property
    def population(self) -> List[AlgoProto]:
        """Return a shallow copy of the global elite population."""
        with self._lock:
            return list(self._population)

    @property
    def is_clustered(self) -> bool:
        """Return whether the search has already entered the clustered phase."""
        with self._lock:
            return self._is_clustered

    @property
    def global_best(self) -> Optional[AlgoProto]:
        """Return the best algorithm seen in the global elite population."""
        with self._lock:
            return self._global_best

    def get_best_score(self) -> float:
        """Return the best score in the current global population."""
        with self._lock:
            if not self._population:
                return -float("inf")
            return max(algo.score for algo in self._population)

    def can_cluster(self, *, min_population: int) -> bool:
        """Return whether the current population is large enough to cluster."""
        with self._lock:
            return len(self._population) >= max(2, min_population, self._num_clusters)

    def register_algo(
        self,
        algo: AlgoProto,
        *,
        source_cluster_id: Optional[int] = None,
    ) -> bool:
        """Register one candidate into the global elite population.

        Returns:
            ``True`` if the candidate remains in the global elite population
            after survival, otherwise ``False``.
        """
        if algo is None or not _is_finite_score(algo.score):
            return False
        algo_copy = copy.deepcopy(algo)
        algo_copy.pop("parents", None)

        with self._lock:
            self.archive.register(algo_copy)

            existing_index = None
            for index, existing in enumerate(self._population):
                # Global deduplication is intentionally code-based. PartEvo
                # benefits from keeping equally scored but behaviorally distinct
                # candidates because those candidates may seed different niches.
                if str(existing.program) == str(algo_copy.program):
                    existing_index = index
                    break

            if existing_index is not None:
                # A refreshed version of the same code can still be useful if
                # the evaluator score improved, so we update in place.
                existing = self._population[existing_index]
                if algo_copy.score >= existing.score:
                    self._population[existing_index] = algo_copy
                else:
                    return False
            else:
                # New code enters the global candidate pool immediately, then
                # survival trims the pool back to the elite capacity.
                self._population.append(algo_copy)

            self._survival()
            accepted = any(
                item.algo_id == algo_copy.algo_id for item in self._population
            )
            if not accepted:
                return False

            if self._global_best is None or algo_copy.score >= self._global_best.score:
                self._global_best = algo_copy

            if self._is_clustered:
                # Once clustering has started, every accepted candidate should
                # be routed back into one niche so local operator selection has
                # up-to-date state.
                self._register_into_cluster(algo_copy, source_cluster_id)
                self._accepted_since_last_cluster += 1
                if self._accepted_since_last_cluster >= self._cluster_refresh_interval:
                    # Periodic re-clustering lets the niches adapt as the elite
                    # population drifts over time.
                    self.recluster()

            return True

    def _survival(self) -> None:
        """Keep the global population deduplicated and truncated by score."""
        unique_map: Dict[str, AlgoProto] = {}
        for algo in self._population:
            code_key = str(algo.program)
            if code_key not in unique_map or algo.score >= unique_map[code_key].score:
                unique_map[code_key] = algo

        self._population = sorted(
            unique_map.values(),
            key=lambda item: item.score,
            reverse=True,
        )[: self._pop_size]

    def _register_into_cluster(
        self,
        algo: AlgoProto,
        source_cluster_id: Optional[int],
    ) -> None:
        """Insert one accepted algorithm into a concrete cluster."""
        target_cluster_id = source_cluster_id
        if target_cluster_id is None or target_cluster_id not in self._clusters:
            # If the producing cluster is unknown, assign the candidate to the
            # nearest existing niche so later local selection stays coherent.
            target_cluster_id = self._assign_cluster_from_features(algo)

        cluster = self._clusters.get(target_cluster_id)
        if cluster is None:
            return

        cluster.register_algo(algo)
        self._program_to_cluster[str(algo.program)] = target_cluster_id

    def _assign_cluster_from_features(self, algo: AlgoProto) -> int:
        """Assign one algorithm to the nearest cluster centroid."""
        if not self._clusters:
            return 0

        candidate_vec = self._extract_feature_vector(algo)
        best_cluster_id = 0
        best_distance = float("inf")
        for cluster_id, cluster in self._clusters.items():
            cluster_population = cluster.population
            if not cluster_population:
                return cluster_id
            centroid = self._compute_centroid(
                [self._extract_feature_vector(item) for item in cluster_population]
            )
            distance = _euclidean_distance(candidate_vec, centroid)
            if distance < best_distance:
                best_distance = distance
                best_cluster_id = cluster_id
        return best_cluster_id

    def recluster(self) -> bool:
        """Rebuild all clusters from the current global population."""
        with self._lock:
            valid_population = [
                algo for algo in self._population if _is_finite_score(algo.score)
            ]
            if len(valid_population) < max(2, self._num_clusters):
                return False

            # Rebuild the full clustering assignment from the current elite
            # population rather than patching labels incrementally. The full
            # rebuild is simpler, deterministic enough, and fits this repo's
            # preference for explicit state over hidden heuristics.
            cluster_count = min(self._num_clusters, len(valid_population))
            feature_vectors = [
                self._extract_feature_vector(algo) for algo in valid_population
            ]
            labels = self._run_kmeans(feature_vectors, cluster_count)

            grouped_population: Dict[int, List[AlgoProto]] = {
                cluster_id: [] for cluster_id in range(cluster_count)
            }
            for algo, cluster_id in zip(valid_population, labels):
                grouped_population[cluster_id].append(algo)

            self._clusters = {}
            self._program_to_cluster = {}
            for cluster_id in range(cluster_count):
                cluster = PartEvoCluster(
                    cluster_id=cluster_id,
                    max_pop_size=self._pop_size,
                    operator_cycle=self._operator_cycle,
                    population=grouped_population.get(cluster_id, []),
                )
                self._clusters[cluster_id] = cluster
                for algo in cluster.population:
                    self._program_to_cluster[str(algo.program)] = cluster_id

            self._accepted_since_last_cluster = 0
            self._is_clustered = True
            return True

    def _extract_feature_vector(self, algo: AlgoProto) -> List[float]:
        """Extract a lightweight feature vector for clustering.

        The upstream implementation uses heavyweight external tooling such as
        CodeBLEU and optional language-model embeddings. This repository keeps
        the method self-contained and dependency-light by combining:

        - simple structural code statistics;
        - idea-length signals;
        - a hashed token histogram for diversity;
        - the current evaluator score.
        """
        program = str(algo.program or "")
        idea = str(algo.get("idea", ""))
        lines = [line for line in program.splitlines() if line.strip()]

        vector = [
            float(len(program)),
            float(len(lines)),
            float(program.count("for ")),
            float(program.count("while ")),
            float(program.count("if ")),
            float(program.count("return ")),
            float(program.count("import ")),
            float(program.count("try:")),
            float(len(idea)),
            float(algo.score if _is_finite_score(algo.score) else 0.0),
        ]
        # The hashed histogram adds a cheap approximation of "code style / token
        # usage" diversity so clustering is not driven purely by score and size.
        vector.extend(self._hashed_token_histogram(program + "\n" + idea, bins=8))
        return vector

    def _hashed_token_histogram(self, text: str, *, bins: int) -> List[float]:
        """Build a stable hashed token histogram."""
        histogram = [0.0] * bins
        tokens = re.findall(r"[A-Za-z_]\w+|\d+|[^\s]", text.lower())
        if not tokens:
            return histogram

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
            bucket = int.from_bytes(digest, "big") % bins
            histogram[bucket] += 1.0

        total = sum(histogram) or 1.0
        return [value / total for value in histogram]

    def _standardize_vectors(self, vectors: List[List[float]]) -> List[List[float]]:
        """Standardize vectors dimension-wise before k-means."""
        if not vectors:
            return []

        columns = list(zip(*vectors))
        means = [statistics.fmean(column) for column in columns]
        stds = []
        for column, mean in zip(columns, means):
            variance = statistics.fmean([(value - mean) ** 2 for value in column])
            std = math.sqrt(variance)
            stds.append(std if std > 1e-12 else 1.0)

        normalized = []
        for vector in vectors:
            normalized.append(
                [(value - mean) / std for value, mean, std in zip(vector, means, stds)]
            )
        return normalized

    def _compute_centroid(self, vectors: List[List[float]]) -> List[float]:
        """Compute the arithmetic centroid of one cluster."""
        if not vectors:
            return []
        dimension = len(vectors[0])
        centroid = [0.0] * dimension
        for vector in vectors:
            for index, value in enumerate(vector):
                centroid[index] += value
        return [value / len(vectors) for value in centroid]

    def _run_kmeans(self, vectors: List[List[float]], k: int) -> List[int]:
        """Run a small dependency-free k-means clustering procedure."""
        normalized = self._standardize_vectors(vectors)
        num_points = len(normalized)
        if num_points <= k:
            return list(range(num_points))

        # Deterministic initialization by rank-spaced sampling keeps clustering
        # stable across runs and avoids a random dependency here.
        centroids = []
        for offset in range(k):
            index = min(num_points - 1, round(offset * (num_points - 1) / max(1, k - 1)))
            centroids.append(list(normalized[index]))

        labels = [0] * num_points
        for _ in range(10):
            changed = False
            for index, vector in enumerate(normalized):
                distances = [
                    _euclidean_distance(vector, centroid) for centroid in centroids
                ]
                best_label = min(range(k), key=lambda item: distances[item])
                if labels[index] != best_label:
                    labels[index] = best_label
                    changed = True

            grouped: Dict[int, List[List[float]]] = {cluster_id: [] for cluster_id in range(k)}
            for label, vector in zip(labels, normalized):
                grouped[label].append(vector)

            for cluster_id in range(k):
                if grouped[cluster_id]:
                    centroids[cluster_id] = self._compute_centroid(grouped[cluster_id])

            if not changed:
                # Early stop once assignments stabilize. We do not need a more
                # elaborate convergence test for the small populations used here.
                break

        return labels

    def _cluster_selection_probabilities(self) -> Tuple[List[int], List[float]]:
        """Compute cluster-selection probabilities for one search step."""
        cluster_ids = sorted(self._clusters.keys())
        if not cluster_ids:
            return [], []

        if not self._use_resource_tilt:
            uniform = 1.0 / len(cluster_ids)
            return cluster_ids, [uniform] * len(cluster_ids)

        scores = []
        for cluster_id in cluster_ids:
            best = self._clusters[cluster_id].get_best()
            if best is None or not _is_finite_score(best.score):
                scores.append(-1e9)
            else:
                scores.append(best.score)

        max_score = max(scores)
        # Resource tilt softly prefers stronger niches without making weak
        # niches unreachable. This preserves exploration while still allocating
        # more traffic to productive regions of the search space.
        weights = [
            math.exp((score - max_score) * self._resource_tilt_alpha) for score in scores
        ]
        total_weight = sum(weights) or 1.0
        return cluster_ids, [weight / total_weight for weight in weights]

    def select_search_context(self) -> Optional[PartEvoSearchContext]:
        """Select the next clustered-search context."""
        with self._lock:
            if not self._is_clustered or not self._clusters:
                return None

            cluster_ids, probabilities = self._cluster_selection_probabilities()
            if not cluster_ids:
                return None

            chosen_cluster_id = random.choices(
                population=cluster_ids,
                weights=probabilities,
                k=1,
            )[0]
            chosen_cluster = self._clusters[chosen_cluster_id]
            parents, operator, need_external = chosen_cluster.select_local_parents()
            if not parents:
                return None

            if need_external and operator == "cn":
                # Cross-niche synthesis injects one helper from another niche
                # so the LLM sees a concrete contrast instead of only local
                # information from the chosen cluster.
                helper = self._sample_cross_cluster_helper(chosen_cluster_id)
                if helper is not None and all(
                    str(parent.program) != str(helper.program) for parent in parents
                ):
                    parents.append(helper)

            if need_external and operator == "lge":
                # Local-global evolution compares the local anchor with strong
                # references. We try the niche best first, then fall back to the
                # current global best if that adds new information.
                cluster_best = chosen_cluster.get_best()
                if cluster_best is not None and all(
                    str(parent.program) != str(cluster_best.program) for parent in parents
                ):
                    parents.append(cluster_best)

                if self._global_best is not None and all(
                    str(parent.program) != str(self._global_best.program) for parent in parents
                ):
                    parents.append(self._global_best)

            return PartEvoSearchContext(
                operator=operator,
                cluster_id=chosen_cluster_id,
                parents=parents,
            )

    def _sample_cross_cluster_helper(self, excluded_cluster_id: int) -> Optional[AlgoProto]:
        """Sample one helper parent from another cluster or from the global best."""
        other_clusters = [
            cluster
            for cluster_id, cluster in self._clusters.items()
            if cluster_id != excluded_cluster_id and len(cluster) > 0
        ]
        if other_clusters:
            helper_cluster = random.choice(other_clusters)
            helper_parents, _, _ = helper_cluster.select_local_parents()
            if helper_parents:
                return helper_parents[0]
        return self._global_best

    def get_cluster_id_for_program(self, program: str) -> Optional[int]:
        """Return the assigned cluster id for one program string."""
        with self._lock:
            return self._program_to_cluster.get(str(program))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the whole PartEvo search state for logging."""
        with self._lock:
            return {
                "population": [algo.to_dict() for algo in self._population],
                "global_best": None if self._global_best is None else self._global_best.to_dict(),
                "is_clustered": self._is_clustered,
                "cluster_refresh_interval": self._cluster_refresh_interval,
                "accepted_since_last_cluster": self._accepted_since_last_cluster,
                "program_to_cluster": dict(self._program_to_cluster),
                "clusters": {
                    cluster_id: cluster.to_dict()
                    for cluster_id, cluster in self._clusters.items()
                },
                "archive": self.archive.to_dict(),
            }
