import sys
from pathlib import Path

import numpy as np

# When this file is executed directly, Python places the task folder on
# ``sys.path`` instead of the repository root. Insert the repository root so
# ``import algodisco...`` keeps working for smoke tests.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.decorators import sandbox_run

try:
    # Support package-style imports when the evaluator is imported as a module.
    from .dataset import weibull_5k
    from .task_definition import template_program
except ImportError:
    # Support direct execution from the command line for quick verification.
    from dataset import weibull_5k
    from task_definition import template_program


def get_valid_bin_indices(item: float, bins: np.ndarray) -> np.ndarray:
    """Return indices of bins whose remaining capacity can fit the item."""
    return np.nonzero((bins - item) >= 0)[0]


def online_binpack(
    items: tuple[float, ...], bins: np.ndarray, priority: callable
) -> tuple[list[list[float, ...], ...], np.ndarray]:
    """Pack items online using the provided priority rule.

    The evaluator passes only valid bins to the priority function. The function
    returns one score per valid bin, and the highest-scoring bin is chosen.
    """
    packing = [[] for _ in bins]
    for item in items:
        valid_bin_indices = get_valid_bin_indices(item, bins)
        if len(valid_bin_indices) == 0:
            continue
        priorities = priority(item, bins[valid_bin_indices])
        best_bin = valid_bin_indices[np.argmax(priorities)]
        bins[best_bin] -= item
        packing[best_bin].append(item)
    packing = [bin_items for bin_items in packing if bin_items]
    return packing, bins


class OnlineBinPackingEvaluator(Evaluator[EvalResult]):
    """Evaluate candidate priority functions for online bin packing."""

    def __init__(self, capacity=100, num_items=5000, **kwargs):
        super().__init__(**kwargs)
        self.capacity = capacity
        self.num_items = num_items
        # Load the bundled dataset from the local Python module instead of the
        # previous pickle-based loading path.
        self.instances = self._load_instances()

    def _load_instances(self):
        """Load evaluation instances from the bundled dataset module."""
        return weibull_5k

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str) -> EvalResult:
        """Execute a candidate program and score mean bin usage."""
        g = {}
        exec(program_str, g)
        priority_func = g["priority"]

        num_bins_list = []

        for name, instance in self.instances.items():
            # Each instance starts with one fresh bin per item, which is a safe
            # upper bound for any online packing strategy.
            capacity = instance["capacity"]
            items = tuple(instance["items"])
            bins = np.array([capacity for _ in range(instance["num_items"])])
            _, bins_packed = online_binpack(items, bins, priority_func)
            num_bins_list.append((bins_packed != capacity).sum())

        mean_bins = np.mean(num_bins_list)
        score = -mean_bins  # Negative because we want to minimize bins

        return {"score": score}


def main() -> None:
    """Run a simple smoke test with the bundled template program."""
    evaluator = OnlineBinPackingEvaluator()
    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    print("Online Bin Packing Template Evaluation")
    print(f"instances: {len(evaluator.instances)}")
    print(f"score: {result['score']}")
    print(f"execution_time: {result.get('execution_time')}")
    print(f"error_msg: {result.get('error_msg')}")


if __name__ == "__main__":
    main()
