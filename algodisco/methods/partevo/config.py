# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from algodisco.base.search_method import SearchConfigBase


@dataclass
class PartEvoConfig(SearchConfigBase):
    """Configuration for a PartEvo search run.

    PartEvo is a niching-oriented evolutionary search method. Compared with
    simpler methods such as EoH, it explicitly maintains:

    - a global elite population;
    - a partition of that population into clusters/niches;
    - an external archive used to summarize global search progress.

    The implementation in this repository adapts the original method to the
    standard AlgoDisco lifecycle and uses threaded samplers with synchronized
    cluster and archive state.

    Attributes:
        template_program: Template program source code used to build prompts.
        task_description: Natural-language task description injected into prompts.
        max_samples: Maximum number of evaluated samples before stopping.
        pop_size: Maximum size of the global elite population.
        init_pop_size: Number of accepted candidates required before the first
            clustering step. ``"auto"`` resolves to ``pop_size``.
        num_clusters: Number of niches maintained during the clustered search
            phase. ``"auto"`` resolves from ``pop_size``.
        cluster_refresh_interval: Number of accepted clustered candidates after
            which the global population is re-clustered. ``"auto"`` resolves
            from ``pop_size``.
        init_trial_multiplier: Hard cap multiplier for initialization attempts. The
            effective budget is ``init_trial_multiplier * init_pop_size``.
        use_resource_tilt: Whether high-performing clusters should receive more
            search traffic.
        resource_tilt_alpha: Softmax temperature scale for resource tilt.
        re_operator_weight: Relative frequency of the reflection-based operator.
        se_operator_weight: Relative frequency of the summary-guided operator.
        cn_operator_weight: Relative frequency of the cross-niche crossover
            operator.
        lge_operator_weight: Relative frequency of the local-global evolution
            operator.
        archive_elite_size: Number of top archive entries retained as elites.
        archive_hard_negative_size: Number of high-quality non-elites retained
            as hard negatives.
        summary_update_interval: Number of SE requests between archive-summary
            refresh opportunities. ``"auto"`` resolves from ``num_clusters``.
        llm_max_tokens: Optional max token limit for each LLM response.
        llm_timeout_seconds: Timeout in seconds for each LLM request.
        algo_save_frequency: Frequency for flushing algorithm logs.
        db_save_frequency: Frequency for persisting snapshots to the logger.
        keep_metadata_keys: Candidate metadata keys preserved in structured logs.
    """

    template_program: str
    task_description: str = ""
    max_samples: Optional[int] = field(default=1000, kw_only=True)

    # Population / clustering.
    pop_size: int | Literal["auto"] = "auto"
    init_pop_size: int | Literal["auto"] = "auto"
    num_clusters: int | Literal["auto"] = "auto"
    cluster_refresh_interval: int | Literal["auto"] = "auto"
    init_trial_multiplier: int = 10

    # Cluster-allocation behavior.
    use_resource_tilt: bool = False
    resource_tilt_alpha: float = 2.0

    # Operator scheduling.
    re_operator_weight: int = 1
    se_operator_weight: int = 1
    cn_operator_weight: int = 1
    lge_operator_weight: int = 1

    # Archive summarization.
    archive_elite_size: int = 5
    archive_hard_negative_size: int = 30
    summary_update_interval: int | Literal["auto"] = "auto"

    # LLM / logging.
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    algo_save_frequency: Optional[int] = 2000
    db_save_frequency: Optional[int] = 2000

    keep_metadata_keys: List[str] = field(
        default_factory=lambda: [
            "idea",
            "phase",
            "cluster_id",
            "reflection_guidance",
            "archive_summary",
            "sample_time",
            "eval_time",
            "execution_time",
            "error_msg",
            "prompt",
            "response_text",
        ]
    )

    def __post_init__(self):
        """Resolve ``auto`` fields and validate critical parameters."""
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

        if self.num_clusters == "auto":
            if self.pop_size <= 6:
                self.num_clusters = 2
            elif self.pop_size <= 12:
                self.num_clusters = 3
            else:
                self.num_clusters = 4

        # Avoid configurations where clustering requests more clusters than the
        # initialization phase can ever provide.
        self.num_clusters = min(self.num_clusters, self.init_pop_size)

        if self.cluster_refresh_interval == "auto":
            self.cluster_refresh_interval = max(4, self.pop_size // 2)

        if self.summary_update_interval == "auto":
            self.summary_update_interval = max(3, self.num_clusters * 3)

        if self.pop_size <= 0:
            raise ValueError("`pop_size` must be positive.")
        if self.init_pop_size <= 0:
            raise ValueError("`init_pop_size` must be positive.")
        if self.init_pop_size > self.pop_size:
            raise ValueError("`init_pop_size` cannot be larger than `pop_size`.")
        if self.num_clusters <= 0:
            raise ValueError("`num_clusters` must be positive.")
        if self.cluster_refresh_interval <= 0:
            raise ValueError("`cluster_refresh_interval` must be positive.")
        if self.init_trial_multiplier <= 0:
            raise ValueError("`init_trial_multiplier` must be positive.")
        if self.resource_tilt_alpha < 0:
            raise ValueError("`resource_tilt_alpha` must be non-negative.")
        if self.archive_elite_size <= 0:
            raise ValueError("`archive_elite_size` must be positive.")
        if self.archive_hard_negative_size <= 0:
            raise ValueError("`archive_hard_negative_size` must be positive.")
        if self.summary_update_interval <= 0:
            raise ValueError("`summary_update_interval` must be positive.")
        if min(
            self.re_operator_weight,
            self.se_operator_weight,
            self.cn_operator_weight,
            self.lge_operator_weight,
        ) < 0:
            raise ValueError("Operator weights must be non-negative.")
        if (
            self.re_operator_weight
            + self.se_operator_weight
            + self.cn_operator_weight
            + self.lge_operator_weight
            <= 0
        ):
            raise ValueError("At least one operator must have a positive weight.")
