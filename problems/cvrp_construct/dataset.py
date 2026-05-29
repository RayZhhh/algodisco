"""Instance generation utilities for the constructive CVRP task."""

import numpy as np


class CVRPInstanceGenerator:
    """Generate deterministic Euclidean CVRP instances."""

    def __init__(
        self,
        n_instances: int,
        n_customers: int,
        vehicle_capacity: int,
        seed: int = 2024,
    ):
        self.n_instances = n_instances
        self.n_customers = n_customers
        self.vehicle_capacity = vehicle_capacity
        self.seed = seed

    def generate_instances(self) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, int]]:
        """Return coordinate arrays, pairwise distances, demands, and capacity."""
        rng = np.random.default_rng(self.seed)
        instance_data = []
        n_nodes = self.n_customers + 1  # Customer nodes plus depot 0.

        for _ in range(self.n_instances):
            coordinates = rng.random((n_nodes, 2))
            demands = np.zeros(n_nodes, dtype=int)
            demands[1:] = rng.integers(1, 10, size=self.n_customers)
            distances = np.linalg.norm(coordinates[:, np.newaxis] - coordinates, axis=2)
            instance_data.append(
                (coordinates, distances, demands, self.vehicle_capacity)
            )

        return instance_data
