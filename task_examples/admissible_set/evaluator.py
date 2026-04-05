import itertools
import sys
from pathlib import Path
from typing import Any

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
    # Support package-style imports such as
    # ``import task_examples.admissible_set.evaluator``.
    from .task_definition import template_program
except ImportError:
    # Support direct execution such as
    # ``python task_examples/admissible_set/evaluator.py``.
    from task_definition import template_program


class AdmissibleSetEvaluator(Evaluator):
    """Evaluate candidate priority functions for the admissible set task."""

    def __init__(self, dimension=15, weight=10, **kwargs):
        super().__init__(**kwargs)
        self.dimension = dimension
        self.weight = weight

        # These are the allowed 3-coordinate patterns used by the compressed
        # representation of the admissible-set construction process.
        self.TRIPLES = [
            (0, 0, 0),
            (0, 0, 1),
            (0, 0, 2),
            (0, 1, 2),
            (0, 2, 1),
            (1, 1, 1),
            (2, 2, 2),
        ]
        self.INT_TO_WEIGHT = [0, 1, 1, 2, 2, 3, 3]
        self.Optimal_Set_Length = {
            "n12w7": 792,
            "n15w10": 3003,
            "n21w15": 43596,
            "n24w17": 237984,
        }

    def _get_valid_children(self):
        """Enumerate all compressed vectors with the requested weight."""
        num_groups = self.dimension // 3
        valid_children = []
        for child in itertools.product(range(7), repeat=num_groups):
            weight = sum(self.INT_TO_WEIGHT[x] for x in child)
            if weight == self.weight:
                valid_children.append(np.array(child, dtype=np.int32))
        return valid_children

    def expand_admissible_set(self, pre_admissible_set):
        """Expand compressed 3-coordinate groups into full vectors."""
        num_groups = len(pre_admissible_set[0])
        admissible_set_result = []
        for row in pre_admissible_set:
            rotations = [[] for _ in range(num_groups)]
            for i in range(num_groups):
                x, y, z = self.TRIPLES[row[i]]
                rotations[i].append((x, y, z))
                if not (x == y == z):
                    rotations[i].append((z, x, y))
                    rotations[i].append((y, z, x))
            product = list(itertools.product(*rotations))
            concatenated = [sum(xs, ()) for xs in product]
            admissible_set_result.extend(concatenated)
        return admissible_set_result

    def get_surviving_children(self, extant_elements, new_element, valid_children):
        """Filter children that remain compatible after adding one element."""
        # fmt:off
        bad_triples = {
            (0, 0, 0), (0, 1, 1), (0, 2, 2), (0, 3, 3), (0, 4, 4), (0, 5, 5), (0, 6, 6),
            (1, 1, 1), (1, 1, 2), (1, 2, 2), (1, 2, 3), (1, 2, 4), (1, 3, 3), (1, 4, 4), (1, 5, 5), (1, 6, 6),
            (2, 2, 2), (2, 3, 3), (2, 4, 4), (2, 5, 5), (2, 6, 6),
            (3, 3, 3), (3, 3, 4), (3, 4, 4), (3, 4, 5), (3, 4, 6), (3, 5, 5), (3, 6, 6),
            (4, 4, 4), (4, 5, 5), (4, 6, 6),
            (5, 5, 5), (5, 5, 6), (5, 6, 6),
            (6, 6, 6),
        }
        # fmt:on
        valid_indices = []
        for index, child in enumerate(valid_children):
            if all(
                self.INT_TO_WEIGHT[x] <= self.INT_TO_WEIGHT[y]
                for x, y in zip(new_element, child)
            ):
                continue
            if all(
                self.INT_TO_WEIGHT[x] >= self.INT_TO_WEIGHT[y]
                for x, y in zip(new_element, child)
            ):
                continue

            is_invalid = False
            for extant_element in extant_elements:
                if all(
                    tuple(sorted((x, y, z))) in bad_triples
                    for x, y, z in zip(extant_element, new_element, child)
                ):
                    is_invalid = True
                    break
            if is_invalid:
                continue

            valid_indices.append(index)
        return valid_indices

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str):
        """Execute a candidate program and score the resulting admissible set."""
        g = {}
        exec(program_str, g)
        priority_func = g["priority"]

        # Score every valid compressed child once before the greedy selection
        # loop starts. The raw score vector is also returned as behavior data.
        valid_children = self._get_valid_children()
        scores_list = []
        for xs in valid_children:
            full_vector_tuple = sum([self.TRIPLES[x] for x in xs], ())
            scores_list.append(
                priority_func(full_vector_tuple, self.dimension, self.weight)
            )

        valid_scores = np.array(scores_list)
        behavior = valid_scores.copy()

        pre_admissible_set = np.empty((0, self.dimension // 3), dtype=np.int32)
        while valid_children:
            # Greedily pick the highest-scoring remaining child, then keep only
            # children that are still feasible with the growing solution.
            max_index = np.argmax(valid_scores)
            max_child = valid_children[max_index]
            surviving_indices = self.get_surviving_children(
                pre_admissible_set, max_child, valid_children
            )
            valid_children = [valid_children[i] for i in surviving_indices]
            valid_scores = valid_scores[surviving_indices]
            pre_admissible_set = np.concatenate(
                [pre_admissible_set, max_child[None]], axis=0
            )

        admissible_set = np.array(self.expand_admissible_set(pre_admissible_set))
        score = float(
            len(admissible_set)
            - self.Optimal_Set_Length[f"n{self.dimension}w{self.weight}"]
        )

        return {"score": score, "behavior": behavior}


def main() -> None:
    """Run a simple smoke test with the bundled template program."""
    evaluator = AdmissibleSetEvaluator()
    result = evaluator.evaluate_program(template_program)
    if result is None:
        raise RuntimeError("Template evaluation failed inside the sandbox.")

    # Printing a short summary keeps the smoke test readable while still
    # exposing enough information to confirm that evaluation succeeded.
    print("Admissible Set Template Evaluation")
    print(f"score: {result['score']}")
    print(f"behavior_length: {len(result['behavior'])}")
    print(f"execution_time: {result.get('execution_time')}")
    print(f"error_msg: {result.get('error_msg')}")


if __name__ == "__main__":
    main()
