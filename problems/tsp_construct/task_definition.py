"""Load prompt-facing task assets for the TSP constructive heuristic example."""

from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent

template_program = (TASK_DIR / "template_algo.txt").read_text(encoding="utf-8")
task_description = (TASK_DIR / "task_description.txt").read_text(encoding="utf-8")
