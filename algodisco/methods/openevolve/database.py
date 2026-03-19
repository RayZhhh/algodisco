# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import threading
import random
import logging
import time
import uuid
import copy
from typing import List, Dict, Any, Optional, Tuple, Set

from algodisco.base.algo import AlgoProto
from algodisco.methods.openevolve.config import OpenEvolveConfig

logger = logging.getLogger(__name__)


class ProgramDatabase:
    """
    A multi-island program database implementing MAP-Elites.
    Strictly follows the original OpenEvolve logic for diversity and complexity.
    """

    def __init__(self, config: OpenEvolveConfig):
        self.config = config
        self.programs: Dict[str, AlgoProto] = {}

        # Multi-island structure
        self.island_feature_maps: List[Dict[str, str]] = [
            {} for _ in range(config.db_num_islands)
        ]
        self.islands: List[Set[str]] = [set() for _ in range(config.db_num_islands)]

        # Archive of elite programs
        self.archive: Set[str] = set()

        # Diversity tracking (exactly as original OpenEvolve)
        self.diversity_cache: Dict[int, Dict[str, Any]] = {}
        self.diversity_cache_size: int = 1000
        self.diversity_reference_set: List[str] = []
        self.diversity_reference_size: int = getattr(
            config, "diversity_reference_size", 20
        )

        # Feature min/max for scaling into bins
        self.feature_stats: Dict[str, Dict[str, float]] = {}

        self.best_program_id: Optional[str] = None
        self._lock = threading.RLock()

    def register_program(self, program: AlgoProto, island_id: Optional[int] = None):
        """Registers a program into the MAP-Elites grid."""
        with self._lock:
            if program.algo_id not in self.programs:
                self.programs[program.algo_id] = program

            if island_id is None:
                island_id = program.get("island_id", 0)
            island_id = island_id % len(self.island_feature_maps)

            # Calculate coordinates
            coords = self._calculate_feature_coords(program)
            coord_key = "|".join(map(str, coords))
            program["feature_coords"] = coords

            island_map = self.island_feature_maps[island_id]
            should_add = True

            if coord_key in island_map:
                existing_id = island_map[coord_key]
                existing_prog = self.programs.get(existing_id)
                if existing_prog and self._get_score(existing_prog) >= self._get_score(
                    program
                ):
                    should_add = False

            if should_add:
                if coord_key in island_map:
                    self.islands[island_id].discard(island_map[coord_key])

                island_map[coord_key] = program.algo_id
                self.islands[island_id].add(program.algo_id)

            self._update_archive(program)
            self._update_best_program(program)
            logger.debug(
                f"Program {program.algo_id} processed for Island {island_id} bin {coord_key}"
            )

    def _calculate_feature_coords(self, program: AlgoProto) -> List[int]:
        """Calculates grid coordinates using the original logic."""
        coords = []
        features = getattr(
            self.config, "feature_dimensions", ["complexity", "diversity"]
        )
        bins = getattr(self.config, "feature_bins", 10)

        for feature in features:
            if feature == "score":
                val = self._get_score(program)
            elif feature == "complexity":
                # Original OpenEvolve simply uses code length
                val = float(len(program.program))
            elif feature == "diversity":
                # Original OpenEvolve calculates fast code diversity against a reference set
                val = self._get_cached_diversity(program)
            else:
                metrics = program.get("metrics", {})
                val = float(metrics.get(feature, 0.0))

            # Dynamic scaling
            if feature not in self.feature_stats:
                self.feature_stats[feature] = {"min": val, "max": val}
            else:
                self.feature_stats[feature]["min"] = min(
                    self.feature_stats[feature]["min"], val
                )
                self.feature_stats[feature]["max"] = max(
                    self.feature_stats[feature]["max"], val
                )

            min_v = self.feature_stats[feature]["min"]
            max_v = self.feature_stats[feature]["max"]

            if max_v > min_v:
                norm = (val - min_v) / (max_v - min_v)
            else:
                norm = 0.5

            bin_idx = int(norm * bins)
            coords.append(max(0, min(bins - 1, bin_idx)))

        return coords

    def _fast_code_diversity(self, code1: str, code2: str) -> float:
        """Fast approximation of code diversity using simple metrics (Original Logic)."""
        if code1 == code2:
            return 0.0

        len1, len2 = len(code1), len(code2)
        length_diff = abs(len1 - len2)

        lines1 = code1.count("\\n")
        lines2 = code2.count("\\n")
        line_diff = abs(lines1 - lines2)

        chars1 = set(code1)
        chars2 = set(code2)
        char_diff = len(chars1.symmetric_difference(chars2))

        return length_diff * 0.1 + line_diff * 10 + char_diff * 0.5

    def _get_cached_diversity(self, program: AlgoProto) -> float:
        """Get diversity score for a program using cache and reference set."""
        code_hash = hash(program.program)

        if code_hash in self.diversity_cache:
            return self.diversity_cache[code_hash]["value"]

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

        diversity = (
            sum(diversity_scores) / max(1, len(diversity_scores))
            if diversity_scores
            else 0.0
        )

        # Cache LRU logic
        if len(self.diversity_cache) >= self.diversity_cache_size:
            oldest_hash = min(
                self.diversity_cache.items(), key=lambda x: x[1]["timestamp"]
            )[0]
            del self.diversity_cache[oldest_hash]

        self.diversity_cache[code_hash] = {"value": diversity, "timestamp": time.time()}
        return diversity

    def _update_diversity_reference_set(self) -> None:
        """Update the reference set for diversity calculation with greedy maximization."""
        all_programs = list(self.programs.values())
        if not all_programs:
            return

        if len(all_programs) <= self.diversity_reference_size:
            self.diversity_reference_set = [p.program for p in all_programs]
        else:
            selected = []
            remaining = all_programs.copy()
            first_idx = random.randint(0, len(remaining) - 1)
            selected.append(remaining.pop(first_idx))

            while len(selected) < self.diversity_reference_size and remaining:
                max_diversity = -1
                best_idx = -1

                for i, candidate in enumerate(remaining):
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

    def _update_archive(self, program: AlgoProto) -> None:
        """Update the global archive of elite programs based on fitness score."""
        archive_size = getattr(self.config, "archive_size", 100)
        if len(self.archive) < archive_size:
            self.archive.add(program.algo_id)
            return

        valid_archive_programs = [
            self.programs[pid] for pid in self.archive if pid in self.programs
        ]

        if valid_archive_programs:
            worst_program = min(
                valid_archive_programs,
                key=lambda p: self._get_score(p),
            )

            if self._get_score(program) > self._get_score(worst_program):
                self.archive.discard(worst_program.algo_id)
                self.archive.add(program.algo_id)
        else:
            self.archive.add(program.algo_id)

    def select_programs(self, num_programs: int) -> Tuple[List[AlgoProto], int]:
        with self._lock:
            island_id = random.randint(0, len(self.island_feature_maps) - 1)
            island_set = self.islands[island_id]

            if not island_set:
                best = self.get_best_program()
                return ([best] if best else [], island_id)

            island_progs = [
                self.programs[pid] for pid in island_set if pid in self.programs
            ]
            if not island_progs:
                best = self.get_best_program()
                return ([best] if best else [], island_id)

            r = random.random()
            exploration_ratio = getattr(self.config, "exploration_ratio", 0.2)
            exploitation_ratio = getattr(self.config, "exploitation_ratio", 0.7)
            elite_ratio = getattr(self.config, "elite_selection_ratio", 0.1)

            if r < exploration_ratio:
                # Random exploration
                selected = random.sample(
                    island_progs, min(num_programs, len(island_progs))
                )
            elif r < exploration_ratio + exploitation_ratio:
                # Exploitation: sample from Archive (Elite global pool)
                valid_archive = [
                    self.programs[pid] for pid in self.archive if pid in self.programs
                ]
                if valid_archive:
                    selected = random.sample(
                        valid_archive, min(num_programs, len(valid_archive))
                    )
                else:
                    island_progs.sort(key=lambda p: self._get_score(p), reverse=True)
                    top_k = max(1, int(len(island_progs) * elite_ratio))
                    elite_pool = island_progs[:top_k]
                    selected = random.sample(
                        elite_pool, min(num_programs, len(elite_pool))
                    )
            else:
                # Fitness weighted sampling
                scores = [self._get_score(p) for p in island_progs]
                min_score = min(scores)
                # Normalize to positive weights
                weights = [max(s - min_score + 1e-6, 1e-6) for s in scores]
                selected = random.choices(
                    island_progs,
                    weights=weights,
                    k=min(num_programs, len(island_progs)),
                )

            return (selected, island_id)

    def get_top_programs(self, num_programs: int) -> List[AlgoProto]:
        with self._lock:
            all_progs = list(self.programs.values())
            all_progs.sort(key=lambda p: self._get_score(p), reverse=True)
            return all_progs[:num_programs]

    def migrate(self):
        with self._lock:
            num_islands = len(self.island_feature_maps)
            if num_islands <= 1:
                return

            migration_rate = getattr(self.config, "migration_rate", 0.1)
            for i in range(num_islands):
                source_set = self.islands[i]
                if not source_set:
                    continue

                island_progs = [
                    self.programs[pid] for pid in source_set if pid in self.programs
                ]
                island_progs.sort(key=lambda p: self._get_score(p), reverse=True)

                num_to_move = max(1, int(len(source_set) * migration_rate))
                migrants = island_progs[:num_to_move]

                target_island = (i + 1) % num_islands

                # Duplicate prevention: get existing codes in target island
                target_progs = [
                    self.programs[pid].program
                    for pid in self.islands[target_island]
                    if pid in self.programs
                ]
                target_code_set = set(target_progs)

                for migrant in migrants:
                    if migrant.program in target_code_set:
                        continue

                    # Create a true clone to enter the new island's MAP-Elites grid properly
                    migrant_copy = copy.deepcopy(migrant)
                    migrant_copy.algo_id = str(uuid.uuid4())
                    migrant_copy["migrant"] = True

                    # Temporarily unlock to call register_program safely or just execute inline
                    # Since register_program acquires the lock, and RLock is reentrant, it's safe.
                    self.register_program(migrant_copy, island_id=target_island)

    def get_best_program(self) -> Optional[AlgoProto]:
        with self._lock:
            return self.programs.get(self.best_program_id)

    def _get_score(self, program: AlgoProto) -> float:
        try:
            return float(program.score if program.score is not None else -1e9)
        except:
            return -1e9

    def _update_best_program(self, program: AlgoProto):
        if self.best_program_id is None:
            self.best_program_id = program.algo_id
            return

        current_best = self.programs.get(self.best_program_id)
        if current_best and self._get_score(program) > self._get_score(current_best):
            self.best_program_id = program.algo_id

    def get_island_stats(self) -> Dict[int, int]:
        with self._lock:
            return {i: len(s) for i, s in enumerate(self.islands)}

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "programs": {pid: p.to_dict() for pid, p in self.programs.items()},
                "islands": [list(s) for s in self.islands],
                "best_program_id": self.best_program_id,
            }
