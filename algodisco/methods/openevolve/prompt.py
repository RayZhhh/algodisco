# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import json
import logging
from pathlib import Path
import random
import re
from typing import Any, Dict, List, Optional

from algodisco.base.algo import AlgoProto
from algodisco.methods.openevolve.config import OpenEvolveConfig
from algodisco.methods.openevolve.database import get_fitness_score
from algodisco.toolkit.program_parser.utils import extract_code_from_response

logger = logging.getLogger(__name__)

# System-level instruction shared by both diff and rewrite prompt modes.
_BASE_SYSTEM_PROMPT = """You are an expert software developer tasked with iteratively improving a codebase.
Your goal is to maximize the FITNESS SCORE while exploring diverse solutions across feature dimensions.
The system maintains a collection of diverse programs - both high fitness AND diversity are valuable."""

# User prompt used when the search expects targeted SEARCH/REPLACE edits.
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

# User prompt used when the search expects a full program rewrite.
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

# Shared history block injected into both prompt modes.
_HISTORY_SECTION = """## Previous Attempts

{previous_attempts}

## Top Performing Programs

{top_programs}

{inspirations_section}"""

# Small reusable templates for history, top programs, and inspirations.
_PREVIOUS_ATTEMPT_TEMPLATE = """### Attempt {attempt_number}
- Changes: {changes}
- Metrics: {performance}
- Outcome: {outcome}"""

_TOP_PROGRAM_TEMPLATE = """### Program {program_number} (Score: {score})
```{language}
{program_snippet}
```
Key features: {key_features}"""

_INSPIRATIONS_SECTION_TEMPLATE = """## Inspiration Programs

These programs represent diverse approaches and creative solutions that may inspire new ideas:

{inspiration_programs}"""

_INSPIRATION_PROGRAM_TEMPLATE = """### Inspiration {program_number} (Score: {score}, Type: {program_type})
```{language}
{program_snippet}
```
Unique approach: {unique_features}"""

_DEFAULT_FRAGMENTS = {
    "fitness_improved": "Fitness improved: {prev:.4f} → {current:.4f}",
    "fitness_declined": "Fitness declined: {prev:.4f} → {current:.4f}. Consider revising recent changes.",
    "fitness_stable": "Fitness unchanged at {current:.4f}",
    "exploring_region": "Exploring {features} region of solution space",
    "code_too_long": "Consider simplifying - code length exceeds {threshold} characters",
    "no_specific_guidance": "Focus on improving fitness while maintaining diversity",
    "attempt_unknown_changes": "Unknown changes",
    "attempt_all_metrics_improved": "Improvement in all metrics",
    "attempt_all_metrics_regressed": "Regression in all metrics",
    "attempt_mixed_metrics": "Mixed results",
    "top_program_metrics_prefix": "Performs well on",
    "diverse_programs_title": "Diverse Programs",
    "inspiration_type_diverse": "Diverse",
    "inspiration_type_migrant": "Migrant",
    "inspiration_type_random": "Random",
    "inspiration_type_score_high_performer": "High-Performer",
    "inspiration_type_score_alternative": "Alternative",
    "inspiration_type_score_experimental": "Experimental",
    "inspiration_type_score_exploratory": "Exploratory",
    "inspiration_changes_prefix": "Modification: {changes}",
    "inspiration_metrics_excellent": "Excellent {metric_name} ({value:.3f})",
    "inspiration_metrics_alternative": "Alternative {metric_name} approach",
    "inspiration_code_with_class": "Object-oriented approach",
    "inspiration_code_with_numpy": "NumPy-based implementation",
    "inspiration_code_with_mixed_iteration": "Mixed iteration strategies",
    "inspiration_code_with_concise_line": "Concise implementation",
    "inspiration_code_with_comprehensive_line": "Comprehensive implementation",
    "inspiration_no_features_postfix": "{program_type} approach to the problem",
    "artifact_title": "Last Execution Output",
}


class TemplateManager:
    """Store prompt templates and reusable text fragments."""

    def __init__(self, custom_template_dir: Optional[str] = None):
        self.templates = {
            "system_message": _BASE_SYSTEM_PROMPT,
            "diff_user": _DIFF_USER_FRAMEWORK,
            "full_rewrite_user": _REWRITE_USER_FRAMEWORK,
            "evolution_history": _HISTORY_SECTION,
            "previous_attempt": _PREVIOUS_ATTEMPT_TEMPLATE,
            "top_program": _TOP_PROGRAM_TEMPLATE,
            "inspirations_section": _INSPIRATIONS_SECTION_TEMPLATE,
            "inspiration_program": _INSPIRATION_PROGRAM_TEMPLATE,
        }
        self.fragments = dict(_DEFAULT_FRAGMENTS)
        if custom_template_dir:
            self._load_from_directory(Path(custom_template_dir))

    def _load_from_directory(self, directory: Path) -> None:
        """Override built-in templates/fragments from a user-supplied directory."""
        if not directory.exists():
            logger.warning("Custom template directory does not exist: %s", directory)
            return

        for txt_file in directory.glob("*.txt"):
            self.templates[txt_file.stem] = txt_file.read_text()

        fragments_file = directory / "fragments.json"
        if fragments_file.exists():
            self.fragments.update(json.loads(fragments_file.read_text()))

    def get_template(self, name: str) -> str:
        """Return one named prompt template."""
        return self.templates[name]

    def get_fragment(self, name: str, **kwargs: Any) -> str:
        """Render one reusable fragment with best-effort formatting."""
        template = self.fragments.get(name, f"[Missing fragment: {name}]")
        try:
            return template.format(**kwargs)
        except KeyError as exc:
            return f"[Fragment formatting error: {exc}]"


class PromptConstructor:
    """Build prompts and parse model responses for OpenEvolve search."""

    def __init__(self, config: OpenEvolveConfig):
        self.config = config
        # Templates can be overridden from disk without changing search code.
        self.template_manager = TemplateManager(config.template_dir)

    def _format_metrics(self, metrics: Any) -> str:
        """Render metrics as a multi-line block for prompt sections."""
        if not metrics:
            return "None"
        if isinstance(metrics, dict):
            formatted_parts = []
            for name, value in metrics.items():
                # Keep numeric metrics consistently formatted so repeated prompt
                # snapshots remain easy for the model to compare.
                if isinstance(value, (int, float)):
                    formatted_parts.append(f"- {name}: {value:.4f}")
                else:
                    formatted_parts.append(f"- {name}: {value}")
            return "\n".join(formatted_parts)
        return str(metrics)

    def _get_program_value(self, program: Any, key: str, default: Any = None) -> Any:
        """Read metadata from either AlgoProto instances or plain dict snapshots."""
        if isinstance(program, AlgoProto):
            return program.get(key, default)
        if isinstance(program, dict):
            return program.get(key, default)
        return default

    def _get_program_code(self, program: Any) -> str:
        """Extract code text from either a live AlgoProto or a lineage snapshot."""
        if isinstance(program, AlgoProto):
            return program.program
        if isinstance(program, dict):
            return program.get("program", "")
        return ""

    def _format_metrics_inline(self, metrics: Dict[str, Any]) -> str:
        """Render metrics as a compact comma-separated summary."""
        if not metrics:
            return "None"

        parts = []
        for name, value in metrics.items():
            if isinstance(value, (int, float)):
                try:
                    parts.append(f"{name}: {float(value):.4f}")
                except (TypeError, ValueError):
                    parts.append(f"{name}: {value}")
            else:
                parts.append(f"{name}: {value}")
        return ", ".join(parts)

    def _get_fitness(self, program: Any) -> float:
        metrics = self._get_program_value(program, "metrics", {}) or {}
        if metrics:
            # Prompt ranking should use the same aggregate fitness that drives
            # archive/selection decisions, not only the raw evaluator score.
            return get_fitness_score(metrics, self.config.feature_dimensions)

        if isinstance(program, AlgoProto):
            score = program.score
        elif isinstance(program, dict):
            score = program.get("score")
        else:
            score = None
        if score is None:
            return 0.0

        try:
            return float(score)
        except (TypeError, ValueError):
            return 0.0

    def _get_program_type(self, program: Any) -> str:
        """Assign a lightweight label used in inspiration sections."""
        # Explicit metadata tags win first because they usually encode search
        # intent more directly than the scalar fitness value.
        if self._get_program_value(program, "diverse"):
            return self.template_manager.get_fragment("inspiration_type_diverse")
        if self._get_program_value(program, "migrant"):
            return self.template_manager.get_fragment("inspiration_type_migrant")
        if self._get_program_value(program, "random"):
            return self.template_manager.get_fragment("inspiration_type_random")

        score = self._get_fitness(program)
        if score >= 0.8:
            return self.template_manager.get_fragment(
                "inspiration_type_score_high_performer"
            )
        if score >= 0.6:
            return self.template_manager.get_fragment(
                "inspiration_type_score_alternative"
            )
        if score >= 0.4:
            return self.template_manager.get_fragment(
                "inspiration_type_score_experimental"
            )
        return self.template_manager.get_fragment("inspiration_type_score_exploratory")

    def _get_feature_summary(self, program: Any) -> str:
        """Summarize the features that make a top program notable in the prompt."""
        metrics = self._get_program_value(program, "metrics", {}) or {}
        feature_parts = []

        for feature in self.config.feature_dimensions:
            # Prefer configured feature dimensions because they explain why the
            # program occupies a specific MAP-Elites region.
            if feature in metrics:
                value = metrics[feature]
                if isinstance(value, (int, float)):
                    feature_parts.append(f"{feature}={float(value):.4f}")
                else:
                    feature_parts.append(f"{feature}={value}")

        if not feature_parts:
            coords = self._get_program_value(program, "feature_coords", [])
            if coords:
                feature_parts.append("coords=" + ", ".join(map(str, coords)))

        if feature_parts:
            return ", ".join(feature_parts)

        # Fall back to the first few metrics when no explicit feature dimensions
        # are available in the stored metadata.
        for name, value in list(metrics.items())[:2]:
            if isinstance(value, (int, float)):
                feature_parts.append(
                    f"{self.template_manager.get_fragment('top_program_metrics_prefix')} {name} ({float(value):.4f})"
                )
            else:
                feature_parts.append(
                    f"{self.template_manager.get_fragment('top_program_metrics_prefix')} {name} ({value})"
                )
        return (
            ", ".join(feature_parts) if feature_parts else "No standout feature markers"
        )

    def _extract_unique_features(self, program: Any) -> str:
        # These heuristics are intentionally lightweight; they recover the
        # "why this program is interesting" prompt context without extra models.
        features = []

        changes = self._get_program_value(program, "changes")
        if not changes:
            changes = self._get_program_value(program, "changes_summary")
        if (
            isinstance(changes, str)
            and self.config.include_changes_under_chars
            and len(changes) < self.config.include_changes_under_chars
        ):
            features.append(
                self.template_manager.get_fragment(
                    "inspiration_changes_prefix",
                    changes=changes,
                )
            )

        metrics = self._get_program_value(program, "metrics", {}) or {}
        for metric_name, value in metrics.items():
            if not isinstance(value, (int, float)):
                continue
            if value >= 0.9:
                features.append(
                    self.template_manager.get_fragment(
                        "inspiration_metrics_excellent",
                        metric_name=metric_name,
                        value=float(value),
                    )
                )
            elif value <= 0.3:
                features.append(
                    self.template_manager.get_fragment(
                        "inspiration_metrics_alternative",
                        metric_name=metric_name,
                    )
                )

        code = self._get_program_code(program)
        code_lower = code.lower()
        # Add a few style and structure hints so inspirations are not presented
        # as raw code only.
        if "class " in code_lower and "def __init__" in code_lower:
            features.append(
                self.template_manager.get_fragment("inspiration_code_with_class")
            )
        if "numpy" in code_lower or "np." in code_lower:
            features.append(
                self.template_manager.get_fragment("inspiration_code_with_numpy")
            )
        if "for " in code_lower and "while " in code_lower:
            features.append(
                self.template_manager.get_fragment(
                    "inspiration_code_with_mixed_iteration"
                )
            )

        line_count = len([line for line in code.splitlines() if line.strip()])
        if (
            self.config.concise_implementation_max_lines
            and line_count <= self.config.concise_implementation_max_lines
        ):
            features.append(
                self.template_manager.get_fragment("inspiration_code_with_concise_line")
            )
        elif (
            self.config.comprehensive_implementation_min_lines
            and line_count >= self.config.comprehensive_implementation_min_lines
        ):
            features.append(
                self.template_manager.get_fragment(
                    "inspiration_code_with_comprehensive_line"
                )
            )

        if not features:
            features.append(
                self.template_manager.get_fragment(
                    "inspiration_no_features_postfix",
                    program_type=self._get_program_type(program),
                )
            )

        return ", ".join(features[: max(1, self.config.num_top_programs)])

    def _identify_improvement_areas(self, parent: Any) -> str:
        """Turn parent state into concrete guidance for the next model call."""
        metrics = self._get_program_value(parent, "metrics", {}) or {}
        areas = []

        # Surface execution failures directly in the prompt so the model can
        # repair them before optimizing for fitness again.
        error_info = self._get_program_value(parent, "error_msg") or metrics.get(
            "error"
        )
        if error_info:
            areas.append(
                "The previous version encountered an error. Please review the artifacts/logs and fix the bug."
            )

        current_fitness = self._get_fitness(parent)
        previous_metrics = self._get_program_value(parent, "parent_metrics", {}) or {}
        if previous_metrics:
            # Compare against the stored parent metrics when available so the
            # prompt can describe the local search direction.
            previous_fitness = get_fitness_score(
                previous_metrics, self.config.feature_dimensions
            )
            if current_fitness > previous_fitness:
                areas.append(
                    self.template_manager.get_fragment(
                        "fitness_improved",
                        prev=previous_fitness,
                        current=current_fitness,
                    )
                )
            elif current_fitness < previous_fitness:
                areas.append(
                    self.template_manager.get_fragment(
                        "fitness_declined",
                        prev=previous_fitness,
                        current=current_fitness,
                    )
                )
            else:
                areas.append(
                    self.template_manager.get_fragment(
                        "fitness_stable",
                        current=current_fitness,
                    )
                )

        coords = self._get_program_value(parent, "feature_coords", [])
        if coords:
            # Coordinates provide an explicit reminder that diversity across bins
            # is part of the search objective.
            areas.append(
                self.template_manager.get_fragment(
                    "exploring_region",
                    features=", ".join(map(str, coords)),
                )
            )

        code = self._get_program_code(parent)
        threshold = self.config.suggest_simplification_after_chars
        if threshold and len(code) > threshold:
            areas.append(
                self.template_manager.get_fragment(
                    "code_too_long",
                    threshold=threshold,
                )
            )

        if not areas:
            areas.append(self.template_manager.get_fragment("no_specific_guidance"))

        return "\n".join(f"- {area}" for area in areas)

    def _compute_attempt_outcome(
        self, metrics: Dict[str, Any], parent_metrics: Dict[str, Any]
    ) -> str:
        """Describe whether a previous attempt improved or regressed numerically."""
        if not parent_metrics:
            return self.template_manager.get_fragment("attempt_unknown_changes")

        improved = []
        regressed = []
        for key, value in metrics.items():
            # Only compare numeric metrics that exist on both sides.
            parent_value = parent_metrics.get(key)
            if isinstance(value, (int, float)) and isinstance(
                parent_value, (int, float)
            ):
                improved.append(float(value) > float(parent_value))
                regressed.append(float(value) < float(parent_value))

        if improved and all(improved):
            return self.template_manager.get_fragment("attempt_all_metrics_improved")
        if regressed and all(regressed):
            return self.template_manager.get_fragment("attempt_all_metrics_regressed")
        return self.template_manager.get_fragment("attempt_mixed_metrics")

    def _format_previous_attempts(
        self,
        previous_programs: List[Any],
        parent_parent_metrics: Dict[str, Any],
    ) -> str:
        """Render a small history of recent attempts for the current prompt."""
        if not previous_programs:
            return "No previous attempts available."

        template = self.template_manager.get_template("previous_attempt")
        blocks = []
        # Keep this section short and local to the current island context so the
        # prompt focuses on nearby search history instead of long ancestry.
        previous_slice = previous_programs[:3]

        for i, program in enumerate(previous_slice):
            metrics = self._get_program_value(program, "metrics", {}) or {}
            parent_metrics = parent_parent_metrics if i == 0 else {}
            block = template.format(
                attempt_number=i + 1,
                changes=(
                    self._get_program_value(program, "changes")
                    or self._get_program_value(program, "changes_summary")
                    or self.template_manager.get_fragment("attempt_unknown_changes")
                ),
                performance=self._format_metrics_inline(metrics),
                outcome=self._compute_attempt_outcome(metrics, parent_metrics),
            )
            blocks.append(block)

        return "\n\n".join(blocks)

    def _format_top_programs(self, programs: List[Any], language: str) -> str:
        """Render the highest-fitness reference programs for the prompt."""
        template = self.template_manager.get_template("top_program")
        blocks = []
        for i, program in enumerate(programs[: self.config.num_top_programs]):
            blocks.append(
                template.format(
                    program_number=i + 1,
                    score=f"{self._get_fitness(program):.4f}",
                    language=language,
                    program_snippet=self._get_program_code(program),
                    key_features=self._get_feature_summary(program),
                )
            )
        return "\n\n".join(blocks)

    def _format_inspirations_section(self, programs: List[Any], language: str) -> str:
        """Render diverse inspiration programs if any were sampled."""
        if not programs:
            return ""

        # Inspirations are intentionally separate from "top programs" so the
        # prompt can present exploration examples without implying they are best.
        program_template = self.template_manager.get_template("inspiration_program")
        section_template = self.template_manager.get_template("inspirations_section")
        blocks = []
        for i, program in enumerate(programs[: self.config.num_diverse_programs]):
            blocks.append(
                program_template.format(
                    program_number=i + 1,
                    score=f"{self._get_fitness(program):.4f}",
                    program_type=self._get_program_type(program),
                    language=language,
                    program_snippet=self._get_program_code(program),
                    unique_features=self._extract_unique_features(program),
                )
            )

        return section_template.format(inspiration_programs="\n\n".join(blocks))

    def _apply_template_variations(self, template: str) -> str:
        """Optionally replace variation placeholders to diversify phrasing."""
        result = template
        if not self.config.use_template_stochasticity:
            return result

        # Placeholder replacement happens late so custom templates can still
        # reuse the same variation keys.
        for key, variations in self.config.template_variations.items():
            if variations and f"{{{key}}}" in result:
                result = result.replace(f"{{{key}}}", random.choice(variations))
        return result

    def _apply_security_filter(self, text: str) -> str:
        """Strip obvious control sequences and secret-like substrings from artifacts."""
        # Artifacts can include terminal escapes or accidental secrets; strip the
        # obvious cases before feeding them back into the model.
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        filtered = ansi_escape.sub("", text)

        secret_patterns = [
            (r"[A-Za-z0-9]{32,}", "<REDACTED_TOKEN>"),
            (r"sk-[A-Za-z0-9]{48}", "<REDACTED_API_KEY>"),
            (r"password[=:]\s*[^\s]+", "password=<REDACTED>"),
            (r"token[=:]\s*[^\s]+", "token=<REDACTED>"),
        ]
        for pattern, replacement in secret_patterns:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        return filtered

    def _safe_decode_artifact(self, value: Any) -> str:
        """Decode artifact payloads into safe prompt text."""
        if isinstance(value, str):
            return (
                self._apply_security_filter(value)
                if self.config.artifact_security_filter
                else value
            )
        if isinstance(value, bytes):
            decoded = value.decode("utf-8", errors="replace")
            return (
                self._apply_security_filter(decoded)
                if self.config.artifact_security_filter
                else decoded
            )
        return str(value)

    def _render_artifacts(self, parent: Any) -> str:
        """Render recent error/log artifacts into a bounded prompt section."""
        if not self.config.include_artifacts:
            return ""

        metrics = self._get_program_value(parent, "metrics", {}) or {}
        artifacts: Dict[str, Any] = {}
        error_info = self._get_program_value(parent, "error_msg") or metrics.get(
            "error"
        )
        if error_info:
            artifacts["error"] = error_info
        if self._get_program_value(parent, "logs"):
            artifacts["logs"] = self._get_program_value(parent, "logs")
        if not artifacts:
            return ""

        sections = []
        for key, value in artifacts.items():
            content = self._safe_decode_artifact(value)
            # Keep artifacts bounded so one verbose traceback does not dominate
            # the entire prompt budget.
            if len(content) > self.config.max_artifact_bytes:
                content = (
                    content[: self.config.max_artifact_bytes] + "\n... (truncated)"
                )
            sections.append(f"### {key}\n```\n{content}\n```")

        return (
            "## "
            + self.template_manager.get_fragment("artifact_title")
            + "\n\n"
            + "\n\n".join(sections)
        )

    def summarize_changes(self, response: str) -> str:
        """Compress a diff-style model response into a short history string."""
        if not response:
            return self.template_manager.get_fragment("attempt_unknown_changes")

        if not self.config.diff_based_evolution:
            return "Full rewrite"

        # Collapse multi-hunk diffs into a compact summary so later prompts can
        # reference recent edits without carrying full patch text around.
        diff_pattern = r"<<<<<<< SEARCH\n(.*?)=======\n(.*?)>>>>>>> REPLACE"
        diffs = re.findall(diff_pattern, response, re.DOTALL)
        if not diffs:
            return self.template_manager.get_fragment("attempt_unknown_changes")

        summaries = []
        max_lines = max(1, self.config.diff_summary_max_lines)
        max_line_len = max(10, self.config.diff_summary_max_line_len)

        for search_text, replace_text in diffs[:3]:
            search_lines = [
                line.strip()
                for line in search_text.strip().splitlines()
                if line.strip()
            ]
            replace_lines = [
                line.strip()
                for line in replace_text.strip().splitlines()
                if line.strip()
            ]
            before = " ".join(search_lines[:1])[:max_line_len]
            after = " ".join(replace_lines[:1])[:max_line_len]
            if before or after:
                summaries.append(f"{before} -> {after}")
            if len(summaries) >= max_lines:
                break

        return (
            " | ".join(summaries)
            if summaries
            else self.template_manager.get_fragment("attempt_unknown_changes")
        )

    def construct_prompt(
        self,
        parent: AlgoProto,
        top_programs: List[AlgoProto],
        inspirations: List[AlgoProto],
        previous_programs: Optional[List[AlgoProto]] = None,
    ) -> Dict[str, str]:
        """
        Build the full system/user prompt pair without changing the search API.

        The prompt combines the current parent, recent attempt history, top local
        programs, diverse inspirations, evaluator artifacts, and task-specific
        guidance into one structured prompt package.
        """

        language = self.config.language
        feature_dimensions = getattr(
            self.config,
            "feature_dimensions",
            ["complexity", "diversity"],
        )

        if not previous_programs:
            # Fall back to lineage only when the caller did not provide explicit
            # island-local history, preserving backward compatibility.
            lineage = self._get_program_value(parent, "parents", [])
            previous_programs = lineage[:3] if lineage else []

        previous_attempts_str = self._format_previous_attempts(
            previous_programs,
            self._get_program_value(parent, "parent_metrics", {}) or {},
        )
        top_programs_str = self._format_top_programs(top_programs, language)
        inspirations_section = self._format_inspirations_section(inspirations, language)

        history_section = self.template_manager.get_template(
            "evolution_history"
        ).format(
            previous_attempts=previous_attempts_str.strip(),
            top_programs=top_programs_str.strip(),
            inspirations_section=inspirations_section.strip(),
        )

        # The remaining fields are all parent-centric because the model is asked
        # to mutate or rewrite this specific baseline implementation.
        improvement_areas = self._identify_improvement_areas(parent)
        artifacts_str = self._render_artifacts(parent)
        fitness_score = self._get_fitness(parent)
        coords = self._get_program_value(parent, "feature_coords", [])
        feature_coords_str = ", ".join(map(str, coords)) if coords else "None"

        framework = (
            self.template_manager.get_template("diff_user")
            if self.config.diff_based_evolution
            else self.template_manager.get_template("full_rewrite_user")
        )
        # Apply stochastic phrasing only after choosing the concrete template.
        framework = self._apply_template_variations(framework)

        task_desc_block = ""
        if self.config.task_description:
            task_desc_block = f"# Task Description\n{self.config.task_description}\n\n"

        # All prompt content is assembled into one final user message because
        # the current LLM interface accepts a single prompt string.
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

        system_message = self.config.system_message
        if system_message in self.template_manager.templates:
            system_message = self.template_manager.get_template(system_message)

        return {"system": system_message, "user": user_msg}

    def extract_code(self, response: str, original_code: str) -> Optional[str]:
        """
        Extract code from an LLM response in diff mode or full-rewrite mode.

        In diff mode, the method applies SEARCH/REPLACE hunks onto the parent
        source. If no valid diff is found, it falls back to fenced code block
        extraction.
        """
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

                    # Apply the strict exact match first so we do not silently
                    # rewrite the wrong region when the model preserved spacing.
                    matched = False
                    for i in range(len(lines) - len(search_lines) + 1):
                        if lines[i : i + len(search_lines)] == search_lines:
                            lines[i : i + len(search_lines)] = replace_lines
                            matched = True
                            break

                    if not matched:
                        # Fall back to stripped matching because the model often
                        # changes indentation or trailing whitespace in SEARCH.
                        for i in range(len(lines) - len(search_lines) + 1):
                            if [
                                l.strip() for l in lines[i : i + len(search_lines)]
                            ] == [l.strip() for l in search_lines]:
                                # In the fallback path, trust the replacement
                                # block as emitted by the model.
                                lines[i : i + len(search_lines)] = replace_lines
                                break
                return "\n".join(lines)

        # Fallback to full code block extraction (for Rewrite mode or failed Diffs)
        return extract_code_from_response(response, self.config.language)


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
