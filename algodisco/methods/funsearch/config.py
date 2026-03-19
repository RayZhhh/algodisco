# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class FunSearchConfig:
    """Configuration for a FunSearch run."""

    template_program: str
    task_description: str = ""
    language: str = "python"
    num_samplers: int = 4
    num_evaluators: int = 4
    examples_per_prompt: int = 2
    samples_per_prompt: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120

    # Database specific configs
    db_num_islands: int = 10
    db_max_island_capacity: Optional[int] = None
    db_reset_period: int = 4 * 60 * 60
    db_cluster_sampling_temperature_init: float = 0.1
    db_cluster_sampling_temperature_period: int = 30_000
    db_save_frequency: Optional[int] = 100

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
