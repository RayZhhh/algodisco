# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from typing import List, Optional, Tuple

from algodisco.base.algo import AlgoProto


class PromptAdapter:
    """Constructs prompts for the LLM to generate new algorithm variations."""

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        return f"```{language}\n{code.strip()}\n```"

    def construct_prompt(
        self, sorted_programs: List[AlgoProto], task_description: str = ""
    ) -> str:
        """Constructs a few-shot prompt to guide the LLM."""
        language = sorted_programs[0].language if sorted_programs else "python"
        lang_display = language.capitalize()

        prompt = ""
        if task_description:
            prompt += f"Task Description: {task_description}\n\n"

        prompt += (
            f"Please help me design an novel {lang_display} algorithm. "
            "Here is an example algorithm function implementation: \n"
        )
        if len(sorted_programs) > 1:
            prompt += "[Version 1]\n"
        prompt += f"{self._wrap_markdown_code_block(str(sorted_programs[0].program), language)}"

        for i in range(1, len(sorted_programs)):
            prompt += f"\n\nWe find that the below version outperforms [Version {i}]."
            prompt += f"\n[Version {i + 1}]\n"
            prompt += self._wrap_markdown_code_block(
                str(sorted_programs[i].program), language
            )
        prompt += (
            "\n\nPlease generate an improved version of the algorithm. "
            "Think outside the box. Do not modify the function signature (i.e., function name, args, ...)\n"
            f"Please generate your algorithm in ```{language} ...``` block. "
            "Only output the code and do not give additional outputs. "
            # "Your code should be concise if possible."
        )
        return prompt

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extracts the code block from the LLM's response."""
        if not response:
            return None
        match = re.search(rf"```(?:{language})?\s*\n(.*?)\n```", response, re.DOTALL)
        return match.group(1).strip() if match else None
