# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional
from algodisco.base.search_method import SearchConfigBase
from algodisco.methods.algobleu_search.similarity_calculator import AlgoSimCalculator


LEGACY_DB_FIELD_MAP = {
    "algo_sim_calculator": "db_algo_sim_calculator",
    "n_islands": "db_num_islands",
    "island_capacity": "db_max_island_capacity",
    "selection_exploitation_intensity": "db_selection_exploitation_intensity",
    "num_sim_caculator_workers": "db_num_sim_caculator_workers",
    "async_register": "db_async_register",
    "island_selection_mechanism": "db_island_selection_mechanism",
    "island_survival_mechanism": "db_island_survival_mechanism",
    "multi_obj_survival_topk": "db_multi_obj_survival_topk",
    "multi_obj_score_rank_weight": "db_multi_obj_score_rank_weight",
    "ast_dfg_weight": "db_ast_dfg_weight",
    "embedding_weight": "db_embedding_weight",
    "behavioral_weight": "db_behavioral_weight",
}


def normalize_algobleu_method_config(
    method_config_data: dict[str, Any],
) -> dict[str, Any]:
    """Flattens legacy `database_config` fields into method-level `db_*` fields."""
    normalized = dict(method_config_data)
    legacy_database_config = normalized.pop("database_config", None)

    if not isinstance(legacy_database_config, dict):
        return normalized

    for legacy_field, flat_field in LEGACY_DB_FIELD_MAP.items():
        if legacy_field in legacy_database_config and flat_field not in normalized:
            normalized[flat_field] = legacy_database_config[legacy_field]

    return normalized


@dataclass
class AlgoBLEUSearchConfig(SearchConfigBase):
    """Configuration for an AlgoBLEU Search run.

    Attributes:
        template_program: Template program source code used to seed the search.
        task_description: Natural-language task description injected into prompts.
        max_samples: Maximum number of candidates to sample before stopping.
        examples_per_prompt: Number of archived examples included in each prompt.
        samples_per_prompt: Number of candidates requested from the LLM per prompt.
        inter_island_selection_p: Probability of selecting parents across islands.
        llm_max_tokens: Optional max token limit for each LLM response.
        llm_timeout_seconds: Timeout in seconds for each LLM request.
        db_save_frequency: Frequency for persisting database snapshots to the logger.
        db_algo_sim_calculator: Similarity calculator used by the algorithm database.
        db_num_islands: Number of islands maintained in the algorithm database.
        db_max_island_capacity: Optional per-island archive capacity limit.
        db_selection_exploitation_intensity: Selection pressure used inside islands.
        db_num_sim_caculator_workers: Number of worker processes for similarity computation.
        db_async_register: Whether to register algorithms asynchronously.
        db_island_selection_mechanism: Selection strategy used inside each island.
        db_island_survival_mechanism: Survival strategy used inside each island.
        db_multi_obj_survival_topk: Top-k preserved before multi-objective pruning.
        db_multi_obj_score_rank_weight: Weight assigned to score rank in multi-objective ranking.
        db_ast_dfg_weight: Weight of AST/DFG similarity in the combined similarity score.
        db_embedding_weight: Weight of embedding similarity in the combined similarity score.
        db_behavioral_weight: Weight of behavioral similarity in the combined similarity score.
        keep_metadata_keys: Candidate metadata keys preserved when saving results.
    """

    template_program: str
    task_description: str = ""
    max_samples: Optional[int] = field(default=1000, kw_only=True)
    examples_per_prompt: int = 2
    samples_per_prompt: int = 4
    inter_island_selection_p: float = 0.5
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    db_save_frequency: Optional[int] = 100
    db_algo_sim_calculator: AlgoSimCalculator = field(default_factory=AlgoSimCalculator)
    db_num_islands: int = 10
    db_max_island_capacity: Optional[int] = 100
    db_selection_exploitation_intensity: float = 1.0
    db_num_sim_caculator_workers: int = 1
    db_async_register: bool = True
    db_island_selection_mechanism: Literal["single_obj", "multi_obj"] = "single_obj"
    db_island_survival_mechanism: Literal["single_obj", "multi_obj"] = "single_obj"
    db_multi_obj_survival_topk: int = 1
    db_multi_obj_score_rank_weight: float = 0.5
    db_ast_dfg_weight: float = 1.0
    db_embedding_weight: float = 1.0
    db_behavioral_weight: float = 1.0

    # Metadata keys to keep when saving
    keep_metadata_keys: List[str] = field(
        default_factory=lambda: [
            "sample_time",
            "eval_time",
            "execution_time",
            "error_msg",
            "idea_time",
            "emb_time",
            "prompt",
            "response_text",
        ]
    )

    def __post_init__(self):
        super().__post_init__()

        if self.db_max_island_capacity is not None:
            assert (
                self.db_multi_obj_survival_topk <= self.db_max_island_capacity
            ), "db_multi_obj_survival_topk must be <= db_max_island_capacity"

        assert (
            0 <= self.db_multi_obj_score_rank_weight <= 1.0
        ), "db_multi_obj_score_rank_weight must be between 0 and 1."
