# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class OnePlusOneEPSConfig:
    """Configuration for a (1+1)-EPS run."""

    template_program: str
    task_description: str = ""
    language: str = "python"
    num_samplers: int = 4
    num_evaluators: int = 4
    samples_per_prompt: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120

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
