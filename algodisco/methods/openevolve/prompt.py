# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
import logging
from typing import List, Optional, Dict, Any

from algodisco.base.algo import AlgoProto
from algodisco.methods.openevolve.config import OpenEvolveConfig

logger = logging.getLogger(__name__)


_BASE_SYSTEM_PROMPT = """You are an expert software developer tasked with iteratively improving a codebase.
Your goal is to maximize the FITNESS SCORE while exploring diverse solutions across feature dimensions.
The system maintains a collection of diverse programs - both high fitness AND diversity are valuable."""

# Framework for Diff-based evolution
_DIFF_USER_FRAMEWORK = """{task_description_block}# Current Program Information
- Fitness: {fitness_score}
- Feature coordinates: {feature_coords}
- Focus areas: {improvement_areas}

{artifacts}

# Program Evolution History
{evolution_history}

# Current Program
```{language}
{current_program}
```

# Task
Suggest improvements to the program that will improve its FITNESS SCORE.
The system maintains diversity across these dimensions: {feature_dimensions}
Different solutions with similar fitness but different features are valuable.

You MUST use the exact SEARCH/REPLACE diff format shown below to indicate changes:

<<<<<<< SEARCH
# Original code to find and replace (must match exactly)
=======
# New replacement code
>>>>>>> REPLACE

Example of valid diff format:
<<<<<<< SEARCH
for i in range(m):
    for j in range(p):
        for k in range(n):
            C[i, j] += A[i, k] * B[k, j]
=======
# Reorder loops for better memory access pattern
for i in range(m):
    for k in range(n):
        for j in range(p):
            C[i, j] += A[i, k] * B[k, j]
>>>>>>> REPLACE

You can suggest multiple changes. Each SEARCH section must exactly match code in the current program.
Be thoughtful about your changes and explain your reasoning thoroughly.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements."""

# Framework for Full Rewrite evolution
_REWRITE_USER_FRAMEWORK = """{task_description_block}# Current Program Information
- Fitness: {fitness_score}
- Feature coordinates: {feature_coords}
- Focus areas: {improvement_areas}

{artifacts}

# Program Evolution History
{evolution_history}

# Current Program
```{language}
{current_program}
```

# Task
Rewrite the program to improve its FITNESS SCORE.
The system maintains diversity across these dimensions: {feature_dimensions}
Different solutions with similar fitness but different features are valuable.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs
as the original program, but with improved internal implementation.

```{language}
# Your rewritten program here
```"""

_HISTORY_SECTION = """## Previous Attempts
{previous_attempts}

## Reference Programs (Best so far)
{top_programs}

## Inspiration Programs (Diverse approaches)
{inspirations}"""


class PromptConstructor:
    """Constructs modular prompts for OpenEvolve (Restoring full logic)."""

    def __init__(self, config: OpenEvolveConfig):
        self.config = config

    def _format_metrics(self, metrics: Any) -> str:
        """Helper to format metrics dictionary for prompt using original format."""
        if not metrics:
            return "None"
        if isinstance(metrics, dict):
            formatted_parts = []
            for name, value in metrics.items():
                if isinstance(value, (int, float)):
                    formatted_parts.append(f"- {name}: {value:.4f}")
                else:
                    formatted_parts.append(f"- {name}: {value}")
            return "\n".join(formatted_parts)
        return str(metrics)

    def _identify_improvement_areas(self, parent: AlgoProto) -> str:
        metrics = parent.get("metrics", {})
        areas = []
        
        if "error" in metrics and metrics["error"]:
            areas.append(
                "The previous version encountered an error. Please review the artifacts/logs and fix the bug."
            )
        
        current_fitness = parent.score if parent.score is not None else 0.0
        
        # Try to find parent's parent to show trend
        parent_lineage = parent.get("parents", [])
        if parent_lineage and isinstance(parent_lineage, list):
            prev_parent = parent_lineage[0]
            prev_fitness = getattr(prev_parent, "score", 0.0) if prev_parent else 0.0
            
            if current_fitness > prev_fitness:
                areas.append(f"Fitness improved: {prev_fitness:.4f} → {current_fitness:.4f}")
            elif current_fitness < prev_fitness:
                areas.append(f"Fitness declined: {prev_fitness:.4f} → {current_fitness:.4f}. Consider revising recent changes.")
            else:
                areas.append(f"Fitness stable at {current_fitness:.4f}")

        # Feature exploration note
        coords = parent.get("feature_coords", [])
        if coords:
            coords_str = ", ".join(map(str, coords))
            areas.append(f"Exploring {coords_str} region of solution space")

        if not areas:
            areas.append("Focus on improving the fitness score while maintaining diversity.")
        
        return "\n".join(f"- {area}" for area in areas)

    def construct_prompt(
        self,
        parent: AlgoProto,
        top_programs: List[AlgoProto],
        inspirations: List[AlgoProto],
    ) -> Dict[str, str]:
        """Builds a complete prompt with system and user messages (Restoring original logic)."""

        language = self.config.language
        feature_dimensions = getattr(self.config, "feature_dimensions", ["complexity", "diversity"])

        # 1. Format Evolution History (Previous Attempts from lineage)
        previous_attempts_str = ""
        current_ancestor = parent
        ancestors = []
        # Trace up to 3 ancestors
        for _ in range(3):
            lineage = current_ancestor.get("parents", [])
            if lineage and isinstance(lineage, list) and len(lineage) > 0:
                current_ancestor = lineage[0]
                ancestors.append(current_ancestor)
            else:
                break
        
        for i, ancestor in enumerate(ancestors):
            # Handle if ancestor is AlgoProto or Dict
            if isinstance(ancestor, AlgoProto):
                score = ancestor.score if ancestor.score is not None else 0.0
            elif isinstance(ancestor, dict):
                score = ancestor.get("score", 0.0)
            else:
                score = 0.0

            previous_attempts_str += f"### Attempt {i+1} (Fitness: {score:.4f})\n"
            # Briefly describe outcome
            outcome = "Baseline"
            if i == 0:
                if parent.score > score: outcome = "Fitness Improved"
                elif parent.score < score: outcome = "Fitness Declined"
                else: outcome = "Fitness Stable"
            previous_attempts_str += f"Outcome: {outcome}\n\n"

        if not previous_attempts_str:
            previous_attempts_str = "No previous attempts in this lineage."

        # 2. Format Reference History
        top_str = ""
        for i, p in enumerate(top_programs):
            top_str += f"### Program {i+1} (Score: {p.score})\n```{language}\n{p.program}\n```\n"

        insp_str = ""
        for i, p in enumerate(inspirations):
            # Try to identify inspiration type if metadata is available
            insp_type = "Inspiration"
            if p.get("migrant"):
                insp_type = "Migrant"
            elif p.get("diverse"):
                insp_type = "Diverse"

            insp_str += f"### {insp_type} {i+1} (Score: {p.score})\n```{language}\n{p.program}\n```\n"

        history_section = _HISTORY_SECTION.format(
            previous_attempts=previous_attempts_str.strip(),
            top_programs=top_str.strip(), 
            inspirations=insp_str.strip()
        )

        # 3. Identify Improvement Areas
        improvement_areas = self._identify_improvement_areas(parent)

        # 4. Handle Artifacts (e.g., error logs from last run)
        artifacts_str = ""
        if self.config.include_artifacts:
            # Check for error logs or metrics metadata
            metrics_meta = parent.get("metrics", {})
            if "error" in metrics_meta:
                artifacts_str = (
                    f"\n## Last Execution Output\n### Error log\n```\n{metrics_meta['error']}\n```"
                )
            elif "logs" in parent:
                artifacts_str = (
                    f"\n## Last Execution Output\n### Log output\n```\n{parent['logs']}\n```"
                )

        # 5. Get Fitness and Coords
        fitness_score = parent.score if parent.score is not None else 0.0
        coords = parent.get("feature_coords", [])
        feature_coords_str = ", ".join(map(str, coords)) if coords else "None"

        # 5. Select Framework
        framework = (
            _DIFF_USER_FRAMEWORK
            if self.config.diff_based_evolution
            else _REWRITE_USER_FRAMEWORK
        )

        # 6. Handle Task Description
        task_desc_block = ""
        if hasattr(self.config, "task_description") and self.config.task_description:
            task_desc_block = f"# Task Description\n{self.config.task_description}\n\n"

        user_msg = framework.format(
            task_description_block=task_desc_block,
            fitness_score=f"{fitness_score:.4f}",
            feature_coords=feature_coords_str,
            feature_dimensions=", ".join(feature_dimensions),
            improvement_areas=improvement_areas,
            artifacts=artifacts_str,
            evolution_history=history_section,
            current_program=parent.program,
            language=language,
        )

        return {"system": _BASE_SYSTEM_PROMPT, "user": user_msg}

    def extract_code(self, response: str, original_code: str) -> Optional[str]:
        """Extracts code from LLM response, handling both diffs and full blocks."""
        if not response:
            return None

        # Logic for Diff-based evolution
        if self.config.diff_based_evolution:
            diff_pattern = r"<<<<<<< SEARCH\n(.*?)=======\n(.*?)>>>>>>> REPLACE"
            diffs = re.findall(diff_pattern, response, re.DOTALL)

            if diffs:
                lines = original_code.split("\n")
                for search_text, replace_text in diffs:
                    search_lines = search_text.rstrip().split("\n")
                    replace_lines = replace_text.rstrip().split("\n")

                    # Exact line-by-line matching
                    matched = False
                    for i in range(len(lines) - len(search_lines) + 1):
                        if lines[i : i + len(search_lines)] == search_lines:
                            lines[i : i + len(search_lines)] = replace_lines
                            matched = True
                            break

                    if not matched:
                        # Fallback: stripped match
                        for i in range(len(lines) - len(search_lines) + 1):
                            if [
                                l.strip() for l in lines[i : i + len(search_lines)]
                            ] == [l.strip() for l in search_lines]:
                                # Even in fallback, we must maintain original indentation if possible,
                                # but simplest is to just apply the replace_lines as provided by LLM.
                                lines[i : i + len(search_lines)] = replace_lines
                                break
                return "\n".join(lines)

        # Fallback to full code block extraction (for Rewrite mode or failed Diffs)
        match = re.search(
            rf"```(?:{self.config.language})?\s*\n(.*?)\n```", response, re.DOTALL
        )
        return match.group(1).strip() if match else None


if __name__ == "__main__":
    # --- Mock Setup for Demonstration ---
    mock_config = OpenEvolveConfig(
        template_program="",
        language="python",
        diff_based_evolution=True,  # Toggle this to see different modes
        include_artifacts=False,
    )

    constructor = PromptConstructor(mock_config)

    # 1. Create an ancestor and parent program
    ancestor_code = "def sort(arr): return sorted(arr)"
    ancestor = AlgoProto(program=ancestor_code, language="python")
    ancestor.score = 0.40

    parent_code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""
    parent = AlgoProto(program=parent_code, language="python")
    parent.score = 0.45
    parent["metrics"] = {"accuracy": 1.0, "runtime": 0.45}
    parent["parents"] = [ancestor]
    parent["feature_coords"] = [5, 2]
    # Mocking a log/error from previous run
    parent["logs"] = (
        "Performance Warning: Bubble sort is O(n^2). Efficiency is too low for large inputs."
    )

    # 2. Create a top performing program (for context)
    top_code = """
def quick_sort(arr):
    if len(arr) <= 1: return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
"""
    top_prog = AlgoProto(program=top_code, language="python")
    top_prog.score = 0.95

    # 3. Create an inspiration program (diverse approach)
    insp_code = """
import numpy as np
def numpy_sort(arr):
    return np.sort(arr).tolist()
"""
    insp_prog = AlgoProto(program=insp_code, language="python")
    insp_prog.score = 0.99

    # --- Scenario 1: Diff Mode ---
    print("=" * 30 + " SCENARIO 1: DIFF MODE " + "=" * 30)
    prompt_diff = constructor.construct_prompt(parent, [top_prog], [insp_prog])
    print(f"SYSTEM MESSAGE:\n{prompt_diff['system']}\n")
    print(f"USER MESSAGE:\n{prompt_diff['user']}\n")

    # --- Scenario 2: Rewrite Mode ---
    print("\n" + "=" * 30 + " SCENARIO 2: REWRITE MODE " + "=" * 30)
    mock_config.diff_based_evolution = False
    prompt_rewrite = constructor.construct_prompt(parent, [top_prog], [insp_prog])
    print(f"USER MESSAGE:\n{prompt_rewrite['user']}\n")
