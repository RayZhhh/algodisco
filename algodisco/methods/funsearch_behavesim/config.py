# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Optional, List
from algodisco.base.search_method import SearchConfigBase
from algodisco.methods.funsearch_behavesim.database import AlgoDatabaseConfig


@dataclass
class BehaveSimSearchConfig(SearchConfigBase):
    """Configuration for an BehaveSim Search run."""

    template_program: str
    task_description: str = ""
    max_samples: Optional[int] = field(default=1000, kw_only=True)
    database_config: AlgoDatabaseConfig = field(default_factory=AlgoDatabaseConfig)
    examples_per_prompt: int = 2
    samples_per_prompt: int = 4
    inter_island_selection_p: float = 0.5
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    db_save_frequency: Optional[int] = 100
    enable_database_reclustering: bool = True
    recluster_threshold: int = 100

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
