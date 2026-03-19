# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Optional, List
from algodisco.methods.algobleu_search.algo_database import AlgoDatabaseConfig


@dataclass
class AlgoBLEUSearchConfig:
    """Configuration for an AlgoBLEU Search run."""

    template_program: str
    task_description: str = ""
    language: str = "python"
    database_config: AlgoDatabaseConfig = field(default_factory=AlgoDatabaseConfig)
    num_samplers: int = 4
    num_evaluators: int = 4
    examples_per_prompt: int = 2
    samples_per_prompt: int = 4
    max_samples: Optional[int] = 1000
    inter_island_selection_p: float = 0.5
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    db_save_frequency: Optional[int] = 100

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
