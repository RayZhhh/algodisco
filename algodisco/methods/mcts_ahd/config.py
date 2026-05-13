# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from algodisco.base.search_method import SearchConfigBase


@dataclass
class MCTSAHDConfig(SearchConfigBase):
    """Configuration for an MCTS-AHD search run.

    This config mirrors the high-level behavior of the original MCTS-AHD method
    while staying aligned with AlgoDisco's search-method conventions. The search
    runs in three phases:

    1. Evaluate the template program once as a logged baseline.
    2. Initialize a population with ``i1`` and ``e1`` style prompts.
    3. Build an MCTS tree on top of the initialized population and continue with
       tree-guided ``e1/e2/m1/m2/s1`` expansions.

    Sampler threads may run concurrently, but tree scheduling and registration
    remain synchronized so MCTS state stays coherent.

    Attributes:
        template_program: Template program source code used to build prompts.
        task_description: Natural-language task description injected into prompts.
        max_samples: Maximum number of evaluated samples before stopping.
        pop_size: Target population size maintained by the database.
        init_pop_size: Number of solutions required before the search enters the
            tree-search phase. ``"auto"`` resolves to ``pop_size``.
        selection_num: Number of parents used by the relevant multi-parent
            operators.
        alpha: MCTS branching-growth exponent. Larger values encourage wider
            branching as node visit counts increase.
        lambda_0: Base exploration coefficient used by the UCT score.
        max_tree_depth: Maximum search depth during the tree traversal stage.
        init_trial_multiplier: Hard cap multiplier for initialization attempts.
            The effective limit is ``init_trial_multiplier * init_pop_size``.
        expansion_retry_limit: Number of retries when an operator keeps
            producing invalid or duplicate candidates.
        use_e2_operator: Whether to enable the ``e2`` operator.
        use_m1_operator: Whether to enable the ``m1`` operator.
        use_m2_operator: Whether to enable the ``m2`` operator.
        use_s1_operator: Whether to enable the ``s1`` path-synthesis operator.
        e1_weight: Number of ``e1`` expansions scheduled at the selected node.
        e2_weight: Number of ``e2`` expansions scheduled at the selected node.
        m1_weight: Number of ``m1`` expansions scheduled at the selected node.
        m2_weight: Number of ``m2`` expansions scheduled at the selected node.
        s1_weight: Number of ``s1`` expansions scheduled at the selected node.
        llm_max_tokens: Optional max token limit for each LLM response.
        llm_timeout_seconds: Timeout in seconds for each LLM request.
        algo_save_frequency: Frequency for flushing algorithm logs.
        db_save_frequency: Frequency for persisting snapshots to the logger.
        keep_metadata_keys: Candidate metadata keys preserved when saving logs.
    """

    template_program: str
    task_description: str = ""
    max_samples: Optional[int] = field(default=1000, kw_only=True)

    # Population parameters
    pop_size: int | Literal["auto"] = "auto"
    init_pop_size: int | Literal["auto"] = "auto"
    selection_num: int = 2

    # Tree-search parameters
    alpha: float = 0.5
    lambda_0: float = 0.1
    max_tree_depth: int = 10
    init_trial_multiplier: int = 10
    expansion_retry_limit: int = 3

    # Operator flags
    use_e2_operator: bool = True
    use_m1_operator: bool = True
    use_m2_operator: bool = True
    use_s1_operator: bool = True

    # Operator schedule weights used after one tree node is selected
    e1_weight: int = 0
    e2_weight: int = 1
    m1_weight: int = 2
    m2_weight: int = 2
    s1_weight: int = 1

    # LLM / logging
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    algo_save_frequency: Optional[int] = 2000
    db_save_frequency: Optional[int] = 2000

    # Metadata keys to keep when saving
    keep_metadata_keys: List[str] = field(
        default_factory=lambda: [
            "idea",
            "phase",
            "tree_depth",
            "sample_time",
            "eval_time",
            "execution_time",
            "error_msg",
            "prompt",
            "response_text",
        ]
    )

    def __post_init__(self):
        """Resolve auto fields and validate critical numeric parameters."""
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
            raise ValueError("`init_pop_size` cannot be larger than `pop_size`.")
        if self.selection_num <= 0:
            raise ValueError("`selection_num` must be positive.")
        if self.selection_num > self.pop_size:
            raise ValueError("`selection_num` cannot be larger than `pop_size`.")
        if self.max_tree_depth <= 0:
            raise ValueError("`max_tree_depth` must be positive.")
        if self.init_trial_multiplier <= 0:
            raise ValueError("`init_trial_multiplier` must be positive.")
        if self.expansion_retry_limit <= 0:
            raise ValueError("`expansion_retry_limit` must be positive.")
        if self.alpha < 0:
            raise ValueError("`alpha` must be non-negative.")
        if self.lambda_0 < 0:
            raise ValueError("`lambda_0` must be non-negative.")
        if min(
            self.e1_weight,
            self.e2_weight,
            self.m1_weight,
            self.m2_weight,
            self.s1_weight,
        ) < 0:
            raise ValueError("Operator weights must be non-negative.")
