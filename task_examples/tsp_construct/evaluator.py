import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.decorators import sandbox_run

try:
    from .dataset import TSPInstanceGenerator
    from .task_definition import template_program
except ImportError:
    from dataset import TSPInstanceGenerator
    from task_definition import template_program


def _extract_callable(program_globals: dict[str, Any], func_name: str) -> Any:
    """Return the expected callable from an executed program namespace."""
    if func_name not in program_globals:
        raise KeyError(f"Expected function `{func_name}` was not defined.")
    return program_globals[func_name]


class TSPConstructEvaluator(Evaluator):
    """Evaluate constructive heuristics for the Traveling Salesman Problem."""

    def __init__(
        self,
        n_instances: int = 16,
        problem_size: int = 50,
        dataset_seed: int = 2024,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.n_instances = n_instances
        self.problem_size = problem_size
        self.dataset_seed = dataset_seed
        self.instances = TSPInstanceGenerator(
            n_instances=self.n_instances,
            n_cities=self.problem_size,
            seed=self.dataset_seed,
        ).generate_instances()

    def _tour_cost(
        self, instance: np.ndarray, solution: np.ndarray, problem_size: int
    ) -> float:
        """Compute the length of a completed TSP tour."""
        cost = 0.0
        for index in range(problem_size - 1):
            cost += np.linalg.norm(
                instance[int(solution[index])] - instance[int(solution[index + 1])]
            )
        cost += np.linalg.norm(
            instance[int(solution[-1])] - instance[int(solution[0])]
        )
        return float(cost)

    def _generate_neighborhood_matrix(self, instance: np.ndarray) -> np.ndarray:
        """Rank all nodes by distance from every node."""
        n_nodes = len(instance)
        neighborhood_matrix = np.zeros((n_nodes, n_nodes), dtype=int)
        for node_index in range(n_nodes):
            distances = np.linalg.norm(instance[node_index] - instance, axis=1)
            neighborhood_matrix[node_index] = np.argsort(distances)
        return neighborhood_matrix

    def _evaluate_callable(self, select_next_node: callable) -> tuple[float, list[float]]:
        """Evaluate one constructive heuristic across all bundled instances."""
        distances = np.ones(self.n_instances, dtype=float)
        n_ins = 0

        for instance, distance_matrix in self.instances:
            neighbor_matrix = self._generate_neighborhood_matrix(instance)
            destination_node = 0
            current_node = 0

            # Route position 0 is intentionally left as node 0 by zero
            # initialization because the evaluator always starts from the depot.
            route = np.zeros(self.problem_size, dtype=int)

            for step_index in range(1, self.problem_size - 1):
                near_nodes = neighbor_matrix[current_node][1:]
                mask = ~np.isin(near_nodes, route[:step_index])
                unvisited_near_nodes = near_nodes[mask]

                next_node = select_next_node(
                    current_node,
                    destination_node,
                    unvisited_near_nodes,
                    distance_matrix,
                )

                # Reject invalid heuristics immediately so search methods cannot
                # quietly exploit undefined behavior.
                if next_node in route[:step_index]:
                    raise ValueError("The heuristic selected an already-visited node.")
                if next_node not in unvisited_near_nodes:
                    raise ValueError("The heuristic selected a node outside `unvisited_nodes`.")

                current_node = int(next_node)
                route[step_index] = current_node

            mask = ~np.isin(np.arange(self.problem_size), route[: self.problem_size - 1])
            last_node = np.arange(self.problem_size)[mask]
            route[self.problem_size - 1] = int(last_node[0])

            distances[n_ins] = self._tour_cost(instance, route, self.problem_size)
            n_ins += 1

            if n_ins == self.n_instances:
                break

        average_distance = float(np.average(distances))
        return -average_distance, distances.tolist()

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str):
        """Execute a candidate program and score mean tour length."""
        program_globals: dict[str, Any] = {}
        exec(program_str, program_globals)
        select_next_node = _extract_callable(program_globals, "select_next_node")
        score, per_instance = self._evaluate_callable(select_next_node)
        return {
            "score": score,
            "per_instance": per_instance,
        }


def main() -> None:
    """Run a smoke test with the bundled constructive TSP template."""
    evaluator = TSPConstructEvaluator()
    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    print("TSP Construct Template Evaluation")
    print(f"instances: {evaluator.n_instances}")
    print(f"problem_size: {evaluator.problem_size}")
    print(f"score: {result['score']}")
    print(f"execution_time: {result.get('execution_time')}")
    print(f"error_msg: {result.get('error_msg')}")


if __name__ == "__main__":
    main()
