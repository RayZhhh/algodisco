import os
import pickle

import numpy as np

from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.decorators import sandbox_run

# Get the directory where this file is located
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_valid_bin_indices(item: float, bins: np.ndarray) -> np.ndarray:
    """Returns indices of bins in which item can fit."""
    return np.nonzero((bins - item) >= 0)[0]


def online_binpack(
    items: tuple[float, ...], bins: np.ndarray, priority: callable
) -> tuple[list[list[float, ...], ...], np.ndarray]:
    """Performs online binpacking of `items` into `bins`."""
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


class OnlineBinPackingEvaluator(Evaluator):
    """Evaluator for Online Bin Packing problem."""

    def __init__(self, capacity=100, num_items=5000, **kwargs):
        super().__init__(**kwargs)
        self.capacity = capacity
        self.num_items = num_items
        # Load test instances
        self.instances = self._load_instances()

    def _load_instances(self):
        """Load test instances from dataset."""
        pkl_path = os.path.join(MODULE_DIR, "weibull_train.pkl")
        with open(pkl_path, "rb") as f:
            weibull_5k = pickle.load(f)
            return weibull_5k["weibull_5k_train"]

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str) -> EvalResult:
        g = {}
        exec(program_str, g)
        priority_func = g["priority"]

        num_bins_list = []

        for name, instance in self.instances.items():
            capacity = instance["capacity"]
            items = tuple(instance["items"])
            bins = np.array([capacity for _ in range(instance["num_items"])])
            _, bins_packed = online_binpack(items, bins, priority_func)
            num_bins_list.append((bins_packed != capacity).sum())

        mean_bins = np.mean(num_bins_list)
        score = -mean_bins  # Negative because we want to minimize bins

        return {"score": score}


if __name__ == "__main__":
    with open("weibull_train.pkl", "rb") as f:
        weibull_5k = pickle.load(f)
        print(weibull_5k.keys())
