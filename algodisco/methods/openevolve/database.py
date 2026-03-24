# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import ast
import copy
import logging
import random
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from algodisco.base.algo import AlgoProto
from algodisco.methods.openevolve.config import OpenEvolveConfig

logger = logging.getLogger(__name__)


def safe_numeric_average(metrics: Dict[str, Any]) -> float:
    """Average numeric metric values while ignoring strings, bools, and NaNs."""
    if not metrics:
        return 0.0

    numeric_values = []
    for value in metrics.values():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                float_val = float(value)
            except (TypeError, ValueError, OverflowError):
                continue

            if float_val == float_val:
                numeric_values.append(float_val)

    if not numeric_values:
        return 0.0

    return sum(numeric_values) / len(numeric_values)


def get_fitness_score(
    metrics: Dict[str, Any], feature_dimensions: Optional[List[str]] = None
) -> float:
    """
    Compute the program fitness used for ranking and archive selection.

    The aggregation rule is intentionally simple:
    - prefer `combined_score` when the evaluator provides one
    - otherwise average numeric metrics that are not being used as features
    - finally fall back to the average of all numeric metrics
    """
    if not metrics:
        return 0.0

    # Allow evaluators to expose one explicit optimization target.
    if "combined_score" in metrics:
        try:
            return float(metrics["combined_score"])
        except (TypeError, ValueError, OverflowError):
            pass

    feature_dimensions = feature_dimensions or []
    filtered_metrics: Dict[str, float] = {}

    for key, value in metrics.items():
        # Feature dimensions are excluded here so search pressure is not doubled
        # by also injecting the same quantities into the fitness aggregate.
        if key in feature_dimensions:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        try:
            float_val = float(value)
        except (TypeError, ValueError, OverflowError):
            continue

        if float_val == float_val:
            filtered_metrics[key] = float_val

    if filtered_metrics:
        return safe_numeric_average(filtered_metrics)

    return safe_numeric_average(metrics)


class ProgramDatabase:
    """
    Store and sample programs for island-based evolution.

    The database tracks several views of the population at once:
    - `programs`: every live program object
    - `islands`: island-local populations used for parent sampling
    - `island_feature_maps`: per-island MAP-Elites elites
    - `archive`: a bounded global set of strong programs
    """

    def __init__(self, config: OpenEvolveConfig):
        self.config = config
        # All live programs keyed by algorithm id.
        self.programs: Dict[str, AlgoProto] = {}

        # Each island owns one MAP-Elites feature grid and one broader population.
        self.island_feature_maps: List[Dict[str, str]] = [
            {} for _ in range(config.db_num_islands)
        ]
        self.islands: List[Set[str]] = [set() for _ in range(config.db_num_islands)]

        # Global archive used for exploitation sampling across islands.
        self.archive: Set[str] = set()

        # Global/island best pointers are cached so prompt construction and
        # migrations do not need to rescan the full population every time.
        self.best_program_id: Optional[str] = None
        self.island_best_programs: List[Optional[str]] = [None] * config.db_num_islands

        # `current_island` supports legacy round-robin helpers. Generation
        # counters drive migration checks during registration.
        self.current_island: int = 0
        self.island_generations: List[int] = [0] * config.db_num_islands
        self.last_migration_generation: int = 0

        # Diversity is computed against a rolling reference set and cached by
        # code hash so feature extraction stays cheap during large searches.
        self.diversity_cache: Dict[int, Dict[str, Any]] = {}
        self.diversity_cache_size: int = 1000
        self.diversity_reference_set: List[str] = []
        self.diversity_reference_size: int = getattr(
            config, "diversity_reference_size", 20
        )

        # Running min/max per feature dimension for online bin normalization.
        self.feature_stats: Dict[str, Dict[str, float]] = {}

        # Registration, sampling, and migration may happen from multiple threads.
        self._lock = threading.RLock()

    def register_program(self, program: AlgoProto, island_id: Optional[int] = None):
        """
        Register a program into the island population and the island feature map.

        A program always enters the island population. It only replaces the
        existing MAP-Elites occupant when it is better for the same feature cell.
        """
        with self._lock:
            # `parents` is only needed while generating and evaluating a child.
            # Once the program is entering the database, collapse that linkage
            # into a few scalar metadata fields and drop the recursive objects.
            parent_lineage = program.get("parents", [])
            parent = (
                parent_lineage[0]
                if parent_lineage and isinstance(parent_lineage, list)
                else None
            )
            if parent is not None:
                self._capture_parent_metadata(program, parent)
                program.pop("parents", None)

            # If the caller did not specify an island, inherit it from the
            # candidate itself or, as a fallback, from the first parent.
            if island_id is None:
                island_id = program.get("island_id")
            if island_id is None:
                if parent is not None:
                    island_id = self._get_program_field(parent, "island_id", 0)
                else:
                    island_id = 0

            island_id = island_id % len(self.island_feature_maps)
            program["island_id"] = island_id

            self.programs[program.algo_id] = program

            # Compute feature coordinates before touching the island map because
            # both the program metadata and the elite index depend on them.
            coords = self._calculate_feature_coords(program)
            coord_key = self._feature_coords_to_key(coords)
            program["feature_coords"] = coords

            island_map = self.island_feature_maps[island_id]
            existing_id = island_map.get(coord_key)
            should_replace = existing_id is None

            if existing_id is not None and existing_id in self.programs:
                # Replacement is based on fitness, not raw evaluator score.
                should_replace = self._is_better(program, self.programs[existing_id])

            if should_replace:
                if existing_id is not None:
                    self.islands[island_id].discard(existing_id)
                island_map[coord_key] = program.algo_id

            # Keep MAP-Elites elites and the broader island population separately.
            # Every registered program stays in the island population, while the
            # feature map only tracks the best occupant of each feature cell.
            self.islands[island_id].add(program.algo_id)

            # Refresh every secondary index after the program becomes visible.
            self._update_archive(program)
            self._enforce_population_limit(exclude_program_id=program.algo_id)
            self._update_best_program(program)
            self._update_island_best_program(program, island_id)

            logger.debug(
                "Program %s processed for island %d bin %s",
                program.algo_id,
                island_id,
                coord_key,
            )

    def sample(self, num_inspirations: int) -> Tuple[AlgoProto, List[AlgoProto], int]:
        """Sample from the island currently pointed to by `current_island`."""
        with self._lock:
            island_id = self.current_island
            return self.sample_from_island(island_id, num_inspirations)

    def sample_from_island(
        self, island_id: int, num_inspirations: int
    ) -> Tuple[AlgoProto, List[AlgoProto], int]:
        """
        Sample a parent and inspiration set for one target island.

        If the target island is empty, parent selection falls back to the global
        population, but the returned island id still refers to the requested
        target island so registration can place new offspring there.
        """
        with self._lock:
            island_id %= len(self.islands)
            if not any(pid in self.programs for pid in self.islands[island_id]):
                parent, inspirations = self._sample_global(num_inspirations)
                return parent, inspirations, island_id

            parent = self._sample_parent_from_island(island_id)
            inspirations = self._sample_inspirations(
                parent=parent,
                island_id=island_id,
                n=num_inspirations,
            )
            return parent, inspirations, island_id

    def select_programs(
        self, num_programs: int, island_id: Optional[int] = None
    ) -> Tuple[List[AlgoProto], int]:
        """
        Backward-compatible selection helper.

        This now samples within one island to preserve island-local evolution.
        """
        with self._lock:
            island_id = self.current_island if island_id is None else island_id
            island_id %= len(self.islands)

            island_programs = [
                self.programs[pid]
                for pid in self.islands[island_id]
                if pid in self.programs
            ]
            if not island_programs:
                best = self.get_best_program()
                return [best] if best else [], island_id

            if num_programs <= 1:
                return [self._sample_parent_from_island(island_id)], island_id

            random.shuffle(island_programs)
            return island_programs[: min(num_programs, len(island_programs))], island_id

    def get_top_programs(
        self, num_programs: int, island_id: Optional[int] = None
    ) -> List[AlgoProto]:
        """Return the highest-fitness programs globally or within one island."""
        with self._lock:
            if island_id is None:
                candidates = list(self.programs.values())
            else:
                island_id %= len(self.islands)
                candidates = [
                    self.programs[pid]
                    for pid in self.islands[island_id]
                    if pid in self.programs
                ]

            candidates.sort(key=self._get_score, reverse=True)
            return candidates[:num_programs]

    def migrate(self):
        """Perform ring migration once the generation-based trigger fires."""
        with self._lock:
            num_islands = len(self.island_feature_maps)
            if num_islands <= 1:
                return

            migration_rate = getattr(self.config, "migration_rate", 0.1)

            for island_id in range(num_islands):
                # Sort each island independently so migrants are chosen from the
                # strongest local programs rather than the global population.
                island_programs = [
                    self.programs[pid]
                    for pid in self.islands[island_id]
                    if pid in self.programs
                ]
                if not island_programs:
                    continue

                island_programs.sort(key=self._get_score, reverse=True)
                num_to_move = max(1, int(len(island_programs) * migration_rate))
                migrants = island_programs[:num_to_move]

                # Match the original ring-style topology: each island exports to
                # its two neighbors, and migrants are re-registered as fresh nodes.
                target_islands = {
                    (island_id + 1) % num_islands,
                    (island_id - 1) % num_islands,
                }

                for migrant in migrants:
                    # Do not repeatedly remigrate already tagged migrants.
                    if migrant.get("migrant", False):
                        continue

                    for target_island in target_islands:
                        # Avoid flooding an island with exact code duplicates.
                        target_codes = {
                            self.programs[pid].program
                            for pid in self.islands[target_island]
                            if pid in self.programs
                        }
                        if migrant.program in target_codes:
                            continue

                        migrant_copy = copy.deepcopy(migrant)
                        migrant_copy.algo_id = str(uuid.uuid4())
                        migrant_copy["migrant"] = True
                        migrant_copy["parents"] = [migrant]
                        self.register_program(migrant_copy, island_id=target_island)

            if self.island_generations:
                self.last_migration_generation = max(self.island_generations)

    def get_best_program(self) -> Optional[AlgoProto]:
        """Return the current global best program, if one exists."""
        with self._lock:
            return self.programs.get(self.best_program_id)

    def get_island_stats(self) -> Dict[int, int]:
        """Return the current population size for each island."""
        with self._lock:
            return {i: len(s) for i, s in enumerate(self.islands)}

    def set_current_island(self, island_id: int) -> None:
        """Set the round-robin island pointer used by legacy sampling helpers."""
        with self._lock:
            self.current_island = island_id % len(self.islands)

    def next_island(self) -> int:
        """Advance and return the legacy round-robin island pointer."""
        with self._lock:
            island_id = self.current_island
            self.current_island = (self.current_island + 1) % len(self.islands)
            return island_id

    def increment_island_generation(self, island_id: int) -> None:
        """Record one completed registration for the given island."""
        with self._lock:
            island_id %= len(self.island_generations)
            self.island_generations[island_id] += 1

    def should_migrate(self) -> bool:
        """Check whether enough registrations happened since the last migration."""
        with self._lock:
            if not self.island_generations:
                return False

            migration_interval = getattr(self.config, "migration_interval", 50)
            max_generation = max(self.island_generations)
            return (
                max_generation - self.last_migration_generation
            ) >= migration_interval

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the database state for logger snapshots/checkpoints."""
        with self._lock:
            return {
                "programs": {pid: p.to_dict() for pid, p in self.programs.items()},
                "islands": [list(s) for s in self.islands],
                "island_feature_maps": [m.copy() for m in self.island_feature_maps],
                "archive": list(self.archive),
                "best_program_id": self.best_program_id,
                "island_best_programs": self.island_best_programs.copy(),
                "current_island": self.current_island,
                "island_generations": self.island_generations.copy(),
                "last_migration_generation": self.last_migration_generation,
            }

    def _choose_sampling_island(self) -> int:
        """Pick any non-empty island, or a random island if all are empty."""
        non_empty_islands = [i for i, island in enumerate(self.islands) if island]
        if non_empty_islands:
            return random.choice(non_empty_islands)
        return random.randint(0, len(self.islands) - 1)

    def _get_program_field(self, program: Any, key: str, default: Any = None) -> Any:
        """Read one field from an AlgoProto first, with dict fallback for compatibility."""
        if isinstance(program, AlgoProto):
            return program.get(key, default)
        if isinstance(program, dict):
            return program.get(key, default)
        return default

    def _capture_parent_metadata(self, program: AlgoProto, parent: Any) -> None:
        """
        Store a small amount of parent metadata without keeping recursive objects.

        This preserves the useful provenance needed later while ensuring that
        database entries and logs stay compact and serializable.
        """
        parent_id = self._get_program_field(parent, "algo_id")
        parent_island_id = self._get_program_field(parent, "island_id")
        parent_metrics = copy.deepcopy(
            self._get_program_field(parent, "metrics", {}) or {}
        )
        parent_score = self._get_program_field(parent, "score")
        parent_evaluator_score = self._get_program_field(parent, "evaluator_score")
        parent_fitness_score = self._get_program_field(parent, "fitness_score")

        if parent_id is not None:
            program["parent_id"] = parent_id
        if parent_island_id is not None:
            program["parent_island_id"] = parent_island_id
        if parent_metrics and not program.get("parent_metrics"):
            program["parent_metrics"] = parent_metrics
        if parent_score is not None:
            program["parent_score"] = parent_score
        if parent_evaluator_score is not None:
            program["parent_evaluator_score"] = parent_evaluator_score
        if parent_fitness_score is not None:
            program["parent_fitness_score"] = parent_fitness_score

    def _sample_parent_from_island(self, island_id: int) -> AlgoProto:
        """Sample one parent from an island using explore/exploit/weighted modes."""
        island_id %= len(self.islands)
        island_programs = [
            self.programs[pid]
            for pid in self.islands[island_id]
            if pid in self.programs
        ]

        if not island_programs:
            raise ValueError("No programs available for island-local sampling")

        r = random.random()
        exploration_ratio = getattr(self.config, "exploration_ratio", 0.2)
        exploitation_ratio = getattr(self.config, "exploitation_ratio", 0.7)

        # Random exploration gives low-fitness or newly arrived programs a chance
        # to reproduce before exploitation dominates the island.
        if r < exploration_ratio:
            return random.choice(island_programs)

        # Archive sampling biases toward strong survivors while still allowing
        # cross-cell and cross-island information flow.
        if r < exploration_ratio + exploitation_ratio:
            archive_in_island = [
                self.programs[pid]
                for pid in self.archive
                if pid in self.programs
                and self.programs[pid].get("island_id") == island_id
            ]
            if archive_in_island:
                return random.choice(archive_in_island)

            valid_archive = [
                self.programs[pid] for pid in self.archive if pid in self.programs
            ]
            if valid_archive:
                return random.choice(valid_archive)

        if len(island_programs) == 1:
            return island_programs[0]

        # Weighted sampling is the fallback mode. Scores are floored at a tiny
        # epsilon so non-positive fitness values still remain sampleable.
        weights = [max(self._get_score(program), 1e-6) for program in island_programs]
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(island_programs)

        normalized = [w / total_weight for w in weights]
        return random.choices(island_programs, weights=normalized, k=1)[0]

    def _initialize_empty_island(self, island_id: int) -> Optional[AlgoProto]:
        """Legacy helper that seeds an empty island with a copy of the global best."""
        best = self.get_best_program()
        if best is None:
            if self.programs:
                return next(iter(self.programs.values()))
            return None

        island_id %= len(self.islands)
        best_copy = copy.deepcopy(best)
        best_copy["migrant"] = True
        best_copy["parents"] = [best]
        self.register_program(best_copy, island_id=island_id)
        return best_copy

    def _sample_global(
        self, num_inspirations: int
    ) -> Tuple[AlgoProto, List[AlgoProto]]:
        """Fallback sampling path used when the requested island is empty."""
        parent = self._sample_parent_global()
        parent_island = parent.get("island_id")
        if parent_island is not None and 0 <= parent_island < len(self.islands):
            # When possible, draw inspirations from the sampled parent's island
            # so the prompt still has coherent local context.
            inspirations = self._sample_inspirations(
                parent=parent,
                island_id=parent_island,
                n=num_inspirations,
            )
        else:
            inspirations = self._sample_inspirations_global(parent, num_inspirations)
        return parent, inspirations

    def _sample_parent_global(self) -> AlgoProto:
        """Sample a parent from the full population using the same policy mix."""
        all_programs = list(self.programs.values())
        if not all_programs:
            raise ValueError("No programs available for sampling")

        r = random.random()
        exploration_ratio = getattr(self.config, "exploration_ratio", 0.2)
        exploitation_ratio = getattr(self.config, "exploitation_ratio", 0.7)

        if r < exploration_ratio:
            return random.choice(all_programs)

        if r < exploration_ratio + exploitation_ratio:
            valid_archive = [
                self.programs[pid] for pid in self.archive if pid in self.programs
            ]
            if valid_archive:
                return random.choice(valid_archive)

        if len(all_programs) == 1:
            return all_programs[0]

        # The global fallback keeps the same weighting rule as island-local
        # sampling so behavior stays predictable across both paths.
        weights = [max(self._get_score(program), 1e-6) for program in all_programs]
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(all_programs)

        normalized = [w / total_weight for w in weights]
        return random.choices(all_programs, weights=normalized, k=1)[0]

    def _sample_inspirations_global(self, parent: AlgoProto, n: int) -> List[AlgoProto]:
        """Pick non-parent inspirations from the full population."""
        if n <= 0:
            return []

        candidates = [
            program
            for program in self.programs.values()
            if program.algo_id != parent.algo_id
        ]
        if not candidates:
            return []

        random.shuffle(candidates)
        return candidates[: min(n, len(candidates))]

    def _sample_inspirations(
        self, parent: AlgoProto, island_id: int, n: int
    ) -> List[AlgoProto]:
        """
        Assemble inspiration programs for prompt construction.

        The order is intentionally biased toward the local island champion, other
        strong local performers, nearby MAP-Elites cells, and only then random
        island members.
        """
        inspirations: List[AlgoProto] = []
        island_id %= len(self.islands)

        if n <= 0:
            return inspirations

        island_programs = [
            self.programs[pid]
            for pid in self.islands[island_id]
            if pid in self.programs
        ]
        if not island_programs:
            return inspirations

        island_best_id = self.island_best_programs[island_id]
        if (
            island_best_id is not None
            and island_best_id in self.programs
            and island_best_id != parent.algo_id
        ):
            # Always expose the island champion first when it is not the parent.
            inspirations.append(self.programs[island_best_id])

        # Seed inspirations with strong local performers before falling back to
        # more exploratory MAP-Elites neighbors and random island members.
        top_n = max(1, int(n * getattr(self.config, "elite_selection_ratio", 0.1)))
        top_programs = self.get_top_programs(top_n, island_id=island_id)
        for program in top_programs:
            if program.algo_id != parent.algo_id and program not in inspirations:
                inspirations.append(program)
            if len(inspirations) >= n:
                return inspirations[:n]

        # Nearby cell perturbation keeps inspirations local in feature space,
        # which helps explore adjacent bins before falling back to random picks.
        parent_coords = parent.get("feature_coords", [])
        if parent_coords:
            for _ in range(max(1, (n - len(inspirations)) * 3)):
                perturbed = [
                    # Small random perturbations probe adjacent bins without
                    # requiring an explicit nearest-neighbor structure.
                    max(
                        0,
                        min(
                            self.config.feature_bins - 1, coord + random.randint(-2, 2)
                        ),
                    )
                    for coord in parent_coords
                ]
                elite_id = self.island_feature_maps[island_id].get(
                    self._feature_coords_to_key(perturbed)
                )
                if (
                    elite_id
                    and elite_id in self.programs
                    and elite_id != parent.algo_id
                    and self.programs[elite_id] not in inspirations
                ):
                    inspirations.append(self.programs[elite_id])
                if len(inspirations) >= n:
                    return inspirations[:n]

        remaining = [
            program
            for program in island_programs
            if program.algo_id != parent.algo_id and program not in inspirations
        ]
        random.shuffle(remaining)
        inspirations.extend(remaining[: max(0, n - len(inspirations))])
        return inspirations[:n]

    def _calculate_feature_coords(self, program: AlgoProto) -> List[int]:
        """Map configured feature dimensions into discrete MAP-Elites bins."""
        coords = []
        features = getattr(
            self.config, "feature_dimensions", ["complexity", "diversity"]
        )
        bins = max(1, getattr(self.config, "feature_bins", 10))
        metrics = program.get("metrics", {}) or {}

        for feature in features:
            # Built-in dimensions are computed locally; any other configured
            # dimension must come from evaluator-returned numeric metrics.
            if feature in metrics:
                value = self._coerce_numeric(metrics.get(feature))
            elif feature == "score":
                value = self._get_score(program)
            elif feature == "complexity":
                value = self._calculate_complexity(program)
            elif feature == "diversity":
                value = self._get_cached_diversity(program)
            else:
                raise ValueError(
                    f"Feature dimension '{feature}' not found in evaluator metrics. "
                    "Built-in options are: 'complexity', 'diversity', 'score'."
                )

            # Normalize each dimension against running min/max so feature bins
            # adapt online as the search discovers new regions.
            stats = self.feature_stats.setdefault(feature, {"min": value, "max": value})
            stats["min"] = min(stats["min"], value)
            stats["max"] = max(stats["max"], value)

            min_v = stats["min"]
            max_v = stats["max"]
            # When a feature has not spread yet, place it into the center bin
            # instead of collapsing all early samples to the lowest bucket.
            norm = 0.5 if max_v <= min_v else (value - min_v) / (max_v - min_v)
            bin_idx = int(norm * bins)
            coords.append(max(0, min(bins - 1, bin_idx)))

        return coords

    def _calculate_complexity(self, program: AlgoProto) -> float:
        """Estimate structural complexity using code length or a Python AST walk."""
        complexity_mode = getattr(self.config, "complexity_mode", "code_length")
        code = program.program or ""

        # Keep complexity extraction cheap and deterministic. AST mode is only
        # used for Python; other languages fall back to code length.
        if complexity_mode != "ast" or program.language != "python":
            return float(len(code))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return float(len(code))

        node_count = 0
        max_depth = 0

        def visit(node: ast.AST, depth: int) -> None:
            # Count both total syntax nodes and nesting depth so wide and deeply
            # nested implementations both receive higher complexity values.
            nonlocal node_count, max_depth
            node_count += 1
            max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(node):
                visit(child, depth + 1)

        visit(tree, 1)
        return float(node_count + max_depth * 5)

    def _feature_coords_to_key(self, coords: List[int]) -> str:
        """Convert feature coordinates into a stable feature-map key."""
        return "|".join(map(str, coords))

    def _fast_code_diversity(self, code1: str, code2: str) -> float:
        """Cheap structural distance proxy used instead of heavier novelty models."""
        if code1 == code2:
            return 0.0

        # This heuristic is intentionally shallow: it reacts to scale, layout,
        # and character-set changes without depending on language-specific parsers.
        len1, len2 = len(code1), len(code2)
        length_diff = abs(len1 - len2)

        lines1 = code1.count("\n")
        lines2 = code2.count("\n")
        line_diff = abs(lines1 - lines2)

        chars1 = set(code1)
        chars2 = set(code2)
        char_diff = len(chars1.symmetric_difference(chars2))

        return length_diff * 0.1 + line_diff * 10 + char_diff * 0.5

    def _get_cached_diversity(self, program: AlgoProto) -> float:
        """Compute and cache diversity against a rolling reference set."""
        code_hash = hash(program.program)

        # Diversity is keyed by code content rather than algorithm id because
        # migrations and retries can create multiple ids for the same program.
        if code_hash in self.diversity_cache:
            return self.diversity_cache[code_hash]["value"]

        # Diversity is approximated against a rolling reference set to avoid
        # quadratic pairwise comparisons across the whole population.
        if (
            not self.diversity_reference_set
            or len(self.diversity_reference_set) < self.diversity_reference_size
        ):
            self._update_diversity_reference_set()

        diversity_scores = []
        for ref_code in self.diversity_reference_set:
            if ref_code != program.program:
                diversity_scores.append(
                    self._fast_code_diversity(program.program, ref_code)
                )

        # Use the mean distance to the reference set as one stable diversity
        # scalar that can be binned like any other feature dimension.
        diversity = (
            sum(diversity_scores) / max(1, len(diversity_scores))
            if diversity_scores
            else 0.0
        )

        if len(self.diversity_cache) >= self.diversity_cache_size:
            # Evict the oldest cached entry first. A full LRU is unnecessary here.
            oldest_hash = min(
                self.diversity_cache.items(), key=lambda x: x[1]["timestamp"]
            )[0]
            del self.diversity_cache[oldest_hash]

        self.diversity_cache[code_hash] = {"value": diversity, "timestamp": time.time()}
        return diversity

    def _update_diversity_reference_set(self) -> None:
        """Refresh the diversity reference set with spread-out program samples."""
        all_programs = list(self.programs.values())
        if not all_programs:
            return

        if len(all_programs) <= self.diversity_reference_size:
            self.diversity_reference_set = [p.program for p in all_programs]
            return

        # Use a simple farthest-point style selection so the reference set stays
        # spread out without introducing heavier embedding-based machinery.
        selected = []
        remaining = all_programs.copy()
        selected.append(remaining.pop(random.randint(0, len(remaining) - 1)))

        while len(selected) < self.diversity_reference_size and remaining:
            max_diversity = -1.0
            best_idx = -1

            for i, candidate in enumerate(remaining):
                # Greedily keep the next candidate that is farthest from the
                # already selected reference programs.
                min_div = float("inf")
                for selected_prog in selected:
                    div = self._fast_code_diversity(
                        candidate.program, selected_prog.program
                    )
                    min_div = min(min_div, div)

                if min_div > max_diversity:
                    max_diversity = min_div
                    best_idx = i

            if best_idx >= 0:
                selected.append(remaining.pop(best_idx))

        self.diversity_reference_set = [p.program for p in selected]

    def _is_better(self, program1: AlgoProto, program2: AlgoProto) -> bool:
        """Compare two programs using the internal fitness metric."""
        return self._get_score(program1) > self._get_score(program2)

    def _update_archive(self, program: AlgoProto) -> None:
        """Maintain a bounded archive of strong programs across all islands."""
        archive_size = getattr(self.config, "archive_size", 100)
        if len(self.archive) < archive_size:
            self.archive.add(program.algo_id)
            return

        # Clean up stale ids first because population pruning can remove archive
        # entries before the archive itself is refreshed.
        valid_archive_programs = [
            self.programs[pid] for pid in self.archive if pid in self.programs
        ]
        stale_ids = [pid for pid in self.archive if pid not in self.programs]
        for stale_id in stale_ids:
            self.archive.discard(stale_id)

        if len(self.archive) < archive_size:
            self.archive.add(program.algo_id)
            return

        if valid_archive_programs:
            # Replace only the weakest archive member so the archive remains a
            # small set of strong, globally reusable stepping stones.
            worst_program = min(valid_archive_programs, key=self._get_score)
            if self._is_better(program, worst_program):
                self.archive.discard(worst_program.algo_id)
                self.archive.add(program.algo_id)
        else:
            self.archive.add(program.algo_id)

    def _update_best_program(self, program: AlgoProto):
        """Refresh the global best pointer after registration."""
        if self.best_program_id is None or self.best_program_id not in self.programs:
            self.best_program_id = program.algo_id
            return

        current_best = self.programs[self.best_program_id]
        if self._is_better(program, current_best):
            self.best_program_id = program.algo_id

    def _update_island_best_program(self, program: AlgoProto, island_id: int):
        """Refresh the best-program pointer for one island."""
        island_id %= len(self.island_best_programs)
        current_best_id = self.island_best_programs[island_id]

        if current_best_id is None or current_best_id not in self.programs:
            self.island_best_programs[island_id] = program.algo_id
            return

        current_best = self.programs[current_best_id]
        if self._is_better(program, current_best):
            self.island_best_programs[island_id] = program.algo_id

    def _enforce_population_limit(
        self, exclude_program_id: Optional[str] = None
    ) -> None:
        """Prune the global population while preserving protected programs."""
        population_size = getattr(self.config, "population_size", None)
        if population_size is None or population_size <= 0:
            return

        if len(self.programs) <= population_size:
            return

        # Never evict the current global best or the program that was just
        # inserted, even if population pruning happens immediately afterward.
        protected_ids = {
            pid for pid in [self.best_program_id, exclude_program_id] if pid
        }
        sorted_programs = sorted(self.programs.values(), key=self._get_score)

        num_to_remove = len(self.programs) - population_size
        removed = 0

        for program in sorted_programs:
            if removed >= num_to_remove:
                break
            if program.algo_id in protected_ids:
                continue
            # Remove low-fitness programs first because all secondary indices can
            # be rebuilt from the surviving population afterward.
            self._remove_program(program.algo_id)
            removed += 1

        if removed > 0:
            self._cleanup_stale_island_bests()

    def _remove_program(self, program_id: str) -> None:
        """Remove a program from all indices and bookkeeping structures."""
        if program_id not in self.programs:
            return

        del self.programs[program_id]
        self.archive.discard(program_id)

        # The same program id can appear in multiple secondary structures, so
        # removal must clear every view of the population.
        for island in self.islands:
            island.discard(program_id)

        for island_idx, island_map in enumerate(self.island_feature_maps):
            keys_to_remove = [
                key for key, pid in island_map.items() if pid == program_id
            ]
            for key in keys_to_remove:
                del island_map[key]

            if self.island_best_programs[island_idx] == program_id:
                self.island_best_programs[island_idx] = None

    def _cleanup_stale_island_bests(self) -> None:
        """Recompute island champions after pruning or elite replacement."""
        for island_id, best_id in enumerate(self.island_best_programs):
            if (
                best_id is not None
                and best_id in self.programs
                and best_id in self.islands[island_id]
            ):
                continue

            # If the cached best is gone, recompute from the surviving members
            # of that island only.
            island_programs = [
                self.programs[pid]
                for pid in self.islands[island_id]
                if pid in self.programs
            ]
            if island_programs:
                self.island_best_programs[island_id] = max(
                    island_programs,
                    key=self._get_score,
                ).algo_id
            else:
                self.island_best_programs[island_id] = None

    def _get_score(self, program: AlgoProto) -> float:
        """Return the fitness value used by search and database bookkeeping."""
        metrics = program.get("metrics", {}) or {}
        if metrics:
            # Ranking/search decisions use the internal fitness aggregate rather
            # than the raw evaluator score stored on program.score.
            return get_fitness_score(metrics, self.config.feature_dimensions)

        if program.score is not None:
            try:
                return float(program.score)
            except (TypeError, ValueError, OverflowError):
                return -1e9

        return -1e9

    def _coerce_numeric(self, value: Any) -> float:
        """Validate that a feature value is numeric and finite."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"Feature value {value!r} is not numeric")

        numeric_value = float(value)
        if numeric_value != numeric_value:
            raise ValueError("Feature value cannot be NaN")
        return numeric_value
