"""Load prompt-facing task assets for the circle packing example."""

from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent

# Keep the text files as the canonical task assets so this task matches the
# organization used throughout ``task_examples``.
template_program = (TASK_DIR / "template_algo.txt").read_text(encoding="utf-8")
task_description = (TASK_DIR / "task_description.txt").read_text(encoding="utf-8")
