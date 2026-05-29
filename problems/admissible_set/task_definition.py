"""Load prompt-facing task assets for the admissible set example.

The task keeps the same visible files as the example directories:

- ``template_algo.txt`` stores the seed program.
- ``task_description.txt`` stores the natural-language task description.

This module provides a clearer Python entrypoint than ``problem.py`` while
preserving the text files that configs and contributors may expect to exist.
"""

from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent

# Keep the text files as the single source of truth so the folder layout stays
# aligned with the examples directory structure used elsewhere in the repo.
template_program = (TASK_DIR / "template_algo.txt").read_text(encoding="utf-8")
task_description = (TASK_DIR / "task_description.txt").read_text(encoding="utf-8")
