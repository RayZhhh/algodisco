import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from algodisco.base.evaluator import Evaluator, EvalResult as BaseEvalResult
from algodisco.toolkit.decorators import sandbox_run

try:
    from .task_definition import template_program
except ImportError:
    from task_definition import template_program


class EvalResult(BaseEvalResult):
    score: float
    behavior: list[list[float]]


def validate_packing(centers: np.ndarray, radii: np.ndarray) -> bool:
    """Check that a circle packing is finite, inside the square, and non-overlapping."""
    n_circles = centers.shape[0]

    # Reject any non-finite values early so later geometric checks stay safe.
    if not np.isfinite(centers).all():
        return False
    if not np.isfinite(radii).all():
        return False

    # Every radius must be non-negative.
    if np.any(radii < 0.0):
        return False

    # Every circle must stay inside the unit square.
    for index in range(n_circles):
        x_coord, y_coord = centers[index]
        radius = radii[index]
        if x_coord - radius < -1e-6:
            return False
        if y_coord - radius < -1e-6:
            return False
        if x_coord + radius > 1.0 + 1e-6:
            return False
        if y_coord + radius > 1.0 + 1e-6:
            return False

    # No two circles may overlap. A tiny tolerance is allowed for floating
    # point noise so numerically borderline solutions are not rejected unfairly.
    for left in range(n_circles):
        for right in range(left + 1, n_circles):
            center_distance = np.sqrt(np.sum((centers[left] - centers[right]) ** 2))
            if center_distance < radii[left] + radii[right] - 1e-6:
                return False

    return True


class CirclePackingEvaluator(Evaluator[EvalResult]):
    """Evaluate constructive circle packings for 26 circles in the unit square."""

    def __init__(self, n_circles: int = 26, **kwargs):
        super().__init__(**kwargs)
        self.n_circles = n_circles

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str) -> EvalResult:
        """Execute a candidate program and score its packing."""
        try:
            program_globals: dict[str, Any] = {}
            exec(program_str, program_globals)

            if "run_packing" not in program_globals:
                raise KeyError("Expected function `run_packing` was not defined.")

            centers, radii, reported_sum = program_globals["run_packing"]()

            # Convert outputs to NumPy arrays so shape and geometry checks are
            # consistent even if the candidate returned Python lists.
            centers_array = np.asarray(centers, dtype=float)
            radii_array = np.asarray(radii, dtype=float)

            # Behavior always stores the returned centers in plain Python list
            # form because downstream behavior analysis should not need NumPy.
            behavior = centers_array.tolist()

            shape_is_valid = (
                centers_array.shape == (self.n_circles, 2)
                and radii_array.shape == (self.n_circles,)
            )

            if not shape_is_valid:
                return {
                    "score": 0.0,
                    "behavior": behavior,
                }

            packing_is_valid = validate_packing(centers_array, radii_array)
            if not packing_is_valid:
                return {
                    "score": 0.0,
                    "behavior": behavior,
                }

            # Use the actual sum derived from radii as the score. The
            # separately reported sum is not trusted for scoring, but we still
            # parse it to validate the interface contract.
            _ = float(reported_sum)
            actual_sum = float(np.sum(radii_array))
            return {
                "score": actual_sum,
                "behavior": behavior,
            }
        except Exception:
            # Always return the required keys even when candidate execution
            # fails. The sandbox decorator will append `error_msg` separately.
            return {
                "score": 0.0,
                "behavior": [],
            }


def main() -> None:
    """Run a smoke test with the bundled template program."""
    evaluator = CirclePackingEvaluator()
    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    print("Circle Packing Template Evaluation")
    print(f"score: {result.get('score')}")
    print(f"num_centers: {len(result.get('behavior', []))}")
    print(f"execution_time: {result.get('execution_time')}")
    print(f"error_msg: {result.get('error_msg')}")


if __name__ == "__main__":
    main()
