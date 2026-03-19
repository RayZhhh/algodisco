# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class EoHOperators(Enum): ...


@dataclass
class EoHConfig:
    """Configuration for an EoH (Evolution of Heuristics) Search run."""

    template_program: str
    task_description: str = ""
    language: str = "python"

    # Population parameters
    pop_size: int = 10
    selection_num: int = 2

    # Operator flags
    use_e2_operator: bool = True
    use_m1_operator: bool = True
    use_m2_operator: bool = True

    # Search parameters
    num_samplers: int = 4
    num_evaluators: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    db_save_frequency: Optional[int] = 100

    # Initialization phase
    init_samples_ratio: float = 2.0  # Sample 2 * pop_size to initialize

    # Metadata keys to keep when saving
    keep_metadata_keys: List[str] = field(
        default_factory=lambda: [
            "idea",
            "sample_time",
            "eval_time",
            "execution_time",
            "error_msg",
            "prompt",
            "response_text",
        ]
    )
