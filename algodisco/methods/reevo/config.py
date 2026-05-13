# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from algodisco.base.search_method import SearchConfigBase


@dataclass
class ReEvoConfig(SearchConfigBase):
    """Configuration for an iterative ReEvo-style search run.

    This adaptation keeps the ReEvo operator ideas but fits them into
    AlgoDisco's iterative lifecycle:

    1. evaluate the seed/template algorithm once;
    2. bootstrap an initial elite population with `init` prompts;
    3. alternate between `crossover` and `mutation` candidates;
    4. update a cached long-term reflection from accumulated short-term
       reflections.
    """

    template_program: str
    task_description: str = ""
    max_samples: Optional[int] = field(default=1000, kw_only=True)

    pop_size: int | Literal["auto"] = "auto"
    init_pop_size: int | Literal["auto"] = "auto"
    init_trial_multiplier: int = 10

    selection_mode: Literal["random", "rank"] = "random"
    crossover_operator_weight: int = 1
    mutation_operator_weight: int = 1
    mutation_rate: float = 0.5
    long_term_reflection_window_size: int = 3
    external_knowledge: str = ""

    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    algo_save_frequency: Optional[int] = 2000
    db_save_frequency: Optional[int] = 2000

    keep_metadata_keys: List[str] = field(
        default_factory=lambda: [
            "idea",
            "phase",
            "operator",
            "sample_time",
            "eval_time",
            "execution_time",
            "error_msg",
            "prompt",
            "response_text",
            "reflection_guidance",
            "long_term_reflection",
            "parent_scores",
        ]
    )

    def __post_init__(self):
        super().__post_init__()

        if self.pop_size == "auto":
            if self.max_samples is None:
                self.pop_size = 10
            elif self.max_samples >= 10000:
                self.pop_size = 40
            elif self.max_samples >= 1000:
                self.pop_size = 20
            elif self.max_samples >= 200:
                self.pop_size = 10
            else:
                self.pop_size = 5

        if self.init_pop_size == "auto":
            self.init_pop_size = self.pop_size

        if self.pop_size <= 0:
            raise ValueError("`pop_size` must be positive.")
        if self.init_pop_size <= 0:
            raise ValueError("`init_pop_size` must be positive.")
        if self.init_pop_size > self.pop_size:
            raise ValueError("`init_pop_size` cannot be larger than `pop_size` in iterative ReEvo.")
        if self.init_trial_multiplier <= 0:
            raise ValueError("`init_trial_multiplier` must be positive.")
        if self.crossover_operator_weight < 0 or self.mutation_operator_weight < 0:
            raise ValueError("Operator weights must be non-negative.")
        if self.crossover_operator_weight + self.mutation_operator_weight <= 0:
            raise ValueError("At least one operator must have a positive weight.")
        if not (0.0 <= self.mutation_rate <= 1.0):
            raise ValueError("`mutation_rate` must be in [0, 1].")
        if self.long_term_reflection_window_size <= 0:
            raise ValueError("`long_term_reflection_window_size` must be positive.")
