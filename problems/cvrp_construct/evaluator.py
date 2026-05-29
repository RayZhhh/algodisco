import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from algodisco.base.evaluator import Evaluator
from algodisco.toolkit.decorators import sandbox_run

from problems.cvrp_construct.dataset import CVRPInstanceGenerator
from problems.cvrp_construct.task_definition import template_program

REQUIRED_FUNCTION_NAME = "select_next_node"


def _extract_required_callable(program_globals: dict[str, Any]) -> Any:
    """Return the task-required callable from an executed program namespace."""
    if REQUIRED_FUNCTION_NAME not in program_globals:
        raise KeyError(
            f"Expected function `{REQUIRED_FUNCTION_NAME}` was not defined. "
            f"Do not rename the required task entrypoint."
        )
    return program_globals[REQUIRED_FUNCTION_NAME]


class CVRPConstructEvaluator(Evaluator):
    """Evaluate constructive heuristics for the Capacitated Vehicle Routing Problem."""

    def __init__(
        self,
        n_instances: int = 16,
        problem_size: int = 50,
        vehicle_capacity: int = 40,
        dataset_seed: int = 2024,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.n_instances = n_instances
        self.problem_size = problem_size
        self.vehicle_capacity = vehicle_capacity
        self.dataset_seed = dataset_seed
        self.n_nodes = self.problem_size + 1
        self.instances = CVRPInstanceGenerator(
            n_instances=self.n_instances,
            n_customers=self.problem_size,
            vehicle_capacity=self.vehicle_capacity,
            seed=self.dataset_seed,
        ).generate_instances()

    def _route_cost(self, distance_matrix: np.ndarray, route: list[int]) -> float:
        """Compute the total travel length of a depot-delimited CVRP route."""
        return float(
            sum(
                distance_matrix[int(route[index]), int(route[index + 1])]
                for index in range(len(route) - 1)
            )
        )

    def _construct_route(
        self,
        distance_matrix: np.ndarray,
        demands: np.ndarray,
        vehicle_capacity: int,
        select_next_node: callable,
    ) -> list[int]:
        """Build one feasible route sequence using the candidate heuristic."""
        depot = 0
        current_node = depot
        current_load = 0
        route = [depot]
        unvisited_customers = set(range(1, self.n_nodes))
        max_steps = 2 * self.problem_size + 1
        steps = 0

        while unvisited_customers:
            steps += 1
            if steps > max_steps:
                raise ValueError(
                    "The heuristic did not finish constructing a route within the "
                    "expected number of steps."
                )

            feasible_customers = np.array(
                [
                    node
                    for node in sorted(unvisited_customers)
                    if current_load + int(demands[node]) <= vehicle_capacity
                ],
                dtype=int,
            )

            if len(feasible_customers) == 0:
                if current_node == depot:
                    raise ValueError(
                        "No feasible customer can be served from the depot under the "
                        "provided vehicle capacity."
                    )
                route.append(depot)
                current_node = depot
                current_load = 0
                continue

            next_node = select_next_node(
                current_node,
                depot,
                feasible_customers.copy(),
                vehicle_capacity - current_load,
                demands.copy(),
                distance_matrix,
            )

            if int(next_node) == depot:
                if current_node == depot:
                    raise ValueError(
                        "The heuristic returned the depot while already at the depot, "
                        "which makes no progress."
                    )
                route.append(depot)
                current_node = depot
                current_load = 0
                continue

            if int(next_node) not in feasible_customers:
                raise ValueError(
                    "The heuristic selected a node outside `feasible_customers`."
                )

            route.append(int(next_node))
            current_load += int(demands[int(next_node)])
            current_node = int(next_node)
            unvisited_customers.remove(current_node)

        if current_node != depot:
            route.append(depot)

        visited_customers = [node for node in route if node != depot]
        if len(visited_customers) != self.problem_size:
            raise ValueError("The heuristic failed to visit every customer exactly once.")
        if len(set(visited_customers)) != self.problem_size:
            raise ValueError("The heuristic visited at least one customer more than once.")

        return route

    def _evaluate_callable(
        self, select_next_node: callable
    ) -> tuple[float, list[float]]:
        """Evaluate one constructive heuristic across all bundled instances."""
        distances = np.ones(self.n_instances, dtype=float)

        for instance_index, (_, distance_matrix, demands, vehicle_capacity) in enumerate(
            self.instances
        ):
            route = self._construct_route(
                distance_matrix=distance_matrix,
                demands=demands,
                vehicle_capacity=vehicle_capacity,
                select_next_node=select_next_node,
            )
            distances[instance_index] = self._route_cost(distance_matrix, route)

        average_distance = float(np.average(distances))
        return -average_distance, distances.tolist()

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str):
        """Execute a candidate program and score mean CVRP route length."""
        program_globals: dict[str, Any] = {}
        exec(program_str, program_globals)
        select_next_node = _extract_required_callable(program_globals)
        score, per_instance = self._evaluate_callable(select_next_node)
        return {
            "score": score,
            "per_instance": per_instance,
        }


def main() -> None:
    """Run a smoke test with the bundled constructive CVRP template."""
    evaluator = CVRPConstructEvaluator()
    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    print("CVRP Construct Template Evaluation")
    print(f"instances: {evaluator.n_instances}")
    print(f"problem_size: {evaluator.problem_size}")
    print(f"vehicle_capacity: {evaluator.vehicle_capacity}")
    print(f"score: {result['score']}")
    print(f"execution_time: {result.get('execution_time')}")
    print(f"error_msg: {result.get('error_msg')}")


if __name__ == "__main__":
    main()
