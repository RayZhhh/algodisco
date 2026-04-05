"""Instance generation utilities for the constructive TSP task."""

import numpy as np


class TSPInstanceGenerator:
    """Generate deterministic Euclidean TSP instances."""

    def __init__(self, n_instances: int, n_cities: int, seed: int = 2024):
        self.n_instances = n_instances
        self.n_cities = n_cities
        self.seed = seed

    def generate_instances(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """Return coordinate arrays and their pairwise distance matrices."""
        rng = np.random.default_rng(self.seed)
        instance_data = []
        for _ in range(self.n_instances):
            coordinates = rng.random((self.n_cities, 2))
            distances = np.linalg.norm(coordinates[:, np.newaxis] - coordinates, axis=2)
            instance_data.append((coordinates, distances))
        return instance_data
