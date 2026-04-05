# Task Examples

This directory contains small, self-contained task folders that show how to
package an optimization problem for `algodisco`.

Each task folder should follow the same structure so new contributors can
understand it at a glance.

## Recommended Layout

For a task named `<task_name>`, the folder should typically contain:

- `template_algo.txt`
  - Stores the initial program to optimize.
  - This file should remain present so task folders match the examples layout
    used elsewhere in the repository.
- `task_description.txt`
  - Stores the English task description injected into prompts.
- `task_definition.py`
  - Loads `template_algo.txt` and `task_description.txt` and exposes them as
    Python strings.
  - This gives Python code a clean import target with a more explicit filename
    than `problem.py`, while preserving the text files.
- `evaluator.py`
  - Implements the task-specific evaluator.
  - Exposes an evaluator class with `evaluate_program(...)`.
  - Includes a `main()` entrypoint that evaluates the bundled template program,
    which makes smoke testing easy.
- `dataset.py` (optional)
  - Stores local datasets or dataset utilities that are specific to the task.
  - This file is only needed when the evaluator depends on bundled data.
- Any other task-specific helper modules (optional)
  - Add helpers only when they make the evaluator or dataset meaningfully
    cleaner.

## Current Tasks

### `admissible_set/`

- `template_algo.txt`
  - Contains the bundled seed `priority(...)` implementation.
- `task_description.txt`
  - Contains the admissible-set task description.
- `task_definition.py`
  - Loads the two text files and exposes them as Python variables.
- `evaluator.py`
  - Evaluates a candidate `priority(...)` function by greedily constructing an
    admissible set and scoring the resulting set size.

### `online_bin_packing/`

- `template_algo.txt`
  - Contains the bundled seed `priority(...)` implementation.
- `task_description.txt`
  - Contains the online bin packing task description.
- `task_definition.py`
  - Loads the two text files and exposes them as Python variables.
- `dataset.py`
  - Bundles the evaluation instances used by the online bin packing evaluator.
- `evaluator.py`
  - Evaluates a candidate `priority(...)` function on the bundled dataset and
    scores it by the mean number of bins used.

### `car_racing/`

- `template_algo.txt`
  - Contains the bundled heuristic `choose_action(...)` controller.
- `task_description.txt`
  - Contains the car racing task description.
- `task_definition.py`
  - Loads the two text files and exposes them as Python variables.
- `dataset.py`
  - Stores the default seed split used by the evaluator.
- `evaluator.py`
  - Evaluates a controller on seeded `CarRacing-v3` episodes and scores it by
    mean track coverage.

### `moon_lander/`

- `template_algo.txt`
  - Contains the bundled heuristic `choose_action(...)` controller.
- `task_description.txt`
  - Contains the moon lander task description.
- `task_definition.py`
  - Loads the two text files and exposes them as Python variables.
- `dataset.py`
  - Stores the default seed split used by the evaluator.
- `feature_pipeline.py`
  - Provides a helper feature extractor based on passive trajectories.
- `evaluator.py`
  - Evaluates a controller on seeded `LunarLander-v3` episodes and scores it
    with a reward-fuel-success composite objective.

### `tsp_construct/`

- `template_algo.txt`
  - Contains the bundled constructive heuristic `select_next_node(...)`.
- `task_description.txt`
  - Contains the TSP constructive task description.
- `task_definition.py`
  - Loads the two text files and exposes them as Python variables.
- `dataset.py`
  - Generates deterministic Euclidean TSP instances.
- `evaluator.py`
  - Evaluates a constructive heuristic by average tour length across bundled
    instances.

### `circle_packing/`

- `template_algo.txt`
  - Contains the bundled constructive `run_packing()` template.
- `task_description.txt`
  - Contains the circle packing task description.
- `task_definition.py`
  - Loads the two text files and exposes them as Python variables.
- `evaluator.py`
  - Validates a 26-circle packing in the unit square, scores it by the sum of
    radii, and returns the full list of circle-center coordinates as
    `behavior`.

## Design Notes

- Keep all task-facing text in English.
- Keep `template_algo.txt` and `task_description.txt` in every task folder so
  the layout stays consistent with `examples/`.
- Prefer explicit filenames such as `task_definition.py` over vague names such
  as `problem.py` for the Python wrapper module.
- Add a runnable `main()` to each evaluator so a contributor can quickly verify
  that the bundled template still executes.
- Add comments where the control flow or data flow is not obvious, especially in
  evaluators.
- Some environment-control tasks require extra runtime dependencies. In this
  directory, `car_racing/` and `moon_lander/` need `gymnasium` with Box2D
  support.
