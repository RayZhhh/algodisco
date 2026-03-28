# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from algodisco.base.search_method import SearchConfigBase


@dataclass
class OpenEvolveConfig(SearchConfigBase):
    """Configuration for an OpenEvolve run.

    Attributes:
        template_program: Template program source code used to seed the search.
        task_description: Natural-language task description injected into prompts.
        max_samples: Maximum number of candidates to sample before stopping.
        diff_based_evolution: Whether to evolve with SEARCH/REPLACE diffs instead of full rewrites.
        num_top_programs: Number of top-performing programs included in prompt context.
        num_diverse_programs: Number of diverse cross-island programs included in prompt context.
        include_artifacts: Whether execution logs and errors are included in prompts.
        template_dir: Optional directory containing prompt template files.
        system_message: Template key or identifier for the main sampler system prompt.
        evaluator_system_message: Template key or identifier for the evaluator prompt.
        use_template_stochasticity: Whether to randomize among configured template variations.
        template_variations: Mapping of template slots to alternative prompt strings.
        max_artifact_bytes: Maximum artifact payload size included in prompts.
        artifact_security_filter: Whether to sanitize artifacts before injecting them into prompts.
        suggest_simplification_after_chars: Character threshold for asking the model to simplify outputs.
        include_changes_under_chars: Character threshold for including explicit change summaries.
        concise_implementation_max_lines: Line threshold used to classify concise implementations.
        comprehensive_implementation_min_lines: Line threshold used to classify comprehensive implementations.
        diff_summary_max_line_len: Maximum line length used when summarizing diffs.
        diff_summary_max_lines: Maximum number of lines included in diff summaries.
        exploration_ratio: Fraction of sampling budget allocated to exploration.
        exploitation_ratio: Fraction of sampling budget allocated to exploitation.
        elite_selection_ratio: Fraction of selections reserved for elite programs.
        samples_per_prompt: Number of candidates requested from the LLM per prompt.
        llm_max_tokens: Optional max token limit for each LLM response.
        llm_timeout_seconds: Timeout in seconds for each LLM request.
        db_num_islands: Number of islands maintained in the MAP-Elites archive.
        db_reset_period: Period in seconds for island reset/rebalancing.
        db_save_frequency: Frequency for persisting database snapshots to the logger.
        feature_dimensions: Feature dimensions used to index the MAP-Elites archive.
        feature_bins: Number of bins per feature dimension.
        complexity_mode: Complexity metric implementation, such as code length or AST-based.
        diversity_reference_size: Reference set size used for diversity calculation.
        archive_size: Maximum number of elites retained in the archive.
        population_size: Optional cap on the live population size.
        migration_interval: Number of samples between migration events.
        migration_rate: Fraction of population migrated during a migration event.
        keep_metadata_keys: Candidate metadata keys preserved when saving results.
    """

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
