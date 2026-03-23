# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from algodisco.base.search_method import SearchConfigBase


@dataclass
class OpenEvolveConfig(SearchConfigBase):
    """Configuration for an OpenEvolve run."""

    # fmt:off
    template_program: str
    task_description: str = ""
    max_samples: Optional[int] = field(default=1000, kw_only=True)

    # Evolution Mode
    diff_based_evolution: bool = False  # True: use SEARCH/REPLACE diffs, False: use Full Rewrite

    # Context Control (Prompt context)
    num_top_programs: int = 1           # Number of top-performing programs to include in prompt
    num_diverse_programs: int = 1       # Number of diverse programs (from other islands)
    include_artifacts: bool = False     # Whether to include execution logs/errors in the prompt
    template_dir: Optional[str] = None
    system_message: str = "system_message"
    evaluator_system_message: str = "evaluator_system_message"
    use_template_stochasticity: bool = True
    template_variations: Dict[str, List[str]] = field(default_factory=dict)
    max_artifact_bytes: int = 20 * 1024
    artifact_security_filter: bool = True
    suggest_simplification_after_chars: Optional[int] = 500
    include_changes_under_chars: Optional[int] = 100
    concise_implementation_max_lines: Optional[int] = 10
    comprehensive_implementation_min_lines: Optional[int] = 50
    diff_summary_max_line_len: int = 100
    diff_summary_max_lines: int = 30
    # fmt:on
    # Search Loop Config
    exploration_ratio: float = 0.2
    exploitation_ratio: float = 0.7
    elite_selection_ratio: float = 0.1
    samples_per_prompt: int = 1
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120

    # Database & MAP-Elites Config
    db_num_islands: int = 10
    db_reset_period: int = 4 * 60 * 60
    db_save_frequency: Optional[int] = 100

    # Feature dimensions for MAP-Elites
    # Built-in dimensions: "complexity", "diversity", "score"
    feature_dimensions: List[str] = field(
        default_factory=lambda: ["complexity", "diversity"]
    )
    feature_bins: int = 10
    complexity_mode: str = "code_length"  # "code_length" or "ast"
    diversity_reference_size: int = (
        20  # Size of reference set for diversity calculation
    )
    archive_size: int = 100
    population_size: Optional[int] = None
    migration_interval: int = 50
    migration_rate: float = 0.1

    # Metadata keys to keep when saving
    keep_metadata_keys: List[str] = field(
        default_factory=lambda: [
            "sample_time",
            "eval_time",
            "execution_time",
            "error_msg",
            "prompt",
            "response_text",
        ]
    )
