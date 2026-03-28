# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from dataclasses import dataclass, field
from typing import Optional, List
from algodisco.base.search_method import SearchConfigBase


@dataclass
class OnePlusOneEPSConfig(SearchConfigBase):
    """Configuration for a (1+1)-EPS run.

    Attributes:
        template_program: Template program source code used to initialize search.
        task_description: Natural-language task description injected into prompts.
        idea_prompt: Whether to use idea-oriented prompting variants.
        max_samples: Maximum number of candidates to sample before stopping.
        samples_per_prompt: Number of candidates requested from the LLM per prompt.
        llm_max_tokens: Optional max token limit for each LLM response.
        llm_timeout_seconds: Timeout in seconds for each LLM request.
        keep_metadata_keys: Candidate metadata keys preserved when saving results.
    """

    template_program: str
    task_description: str = ""
    idea_prompt: bool = False
    max_samples: Optional[int] = field(default=1000, kw_only=True)
    samples_per_prompt: int = 4
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
