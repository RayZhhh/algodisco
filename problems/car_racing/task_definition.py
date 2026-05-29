"""Load prompt-facing task assets for the car racing example.

The text files remain the source of truth so this task matches the layout used
by the other examples in the repository.
"""

from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent

# Load the task prompt assets from plain text files so they are easy to inspect
# and reuse from configs or scripts without importing evaluator code.
template_program = (TASK_DIR / "template_algo.txt").read_text(encoding="utf-8")
task_description = (TASK_DIR / "task_description.txt").read_text(encoding="utf-8")
