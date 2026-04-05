"""Load prompt-facing task assets for the online bin packing example.

The canonical prompt assets remain in text files so the task layout matches the
rest of the repository examples and remains easy to inspect without importing
Python code.
"""

from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent

# Keep the text files as the single source of truth. This allows YAML configs,
# manual inspection, and Python imports to all share the same task assets.
template_program = (TASK_DIR / "template_algo.txt").read_text(encoding="utf-8")
task_description = (TASK_DIR / "task_description.txt").read_text(encoding="utf-8")
