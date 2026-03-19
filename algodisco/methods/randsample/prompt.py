# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from typing import Optional

from algodisco.base.algo import AlgoProto


class PromptAdapter:
    """Constructs prompts for the LLM to generate algorithm variations using RandSample."""

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        return f"```{language}\\n{code.strip()}\\n```"

    def construct_prompt(
        self, template_program: AlgoProto, task_description: str = ""
    ) -> str:
        """Constructs a prompt based on the template program."""
        language = template_program.language or "python"
        lang_display = language.capitalize()

        prompt = ""
        if task_description:
            prompt += f"Task Description: {task_description}\\n\\n"

        prompt += (
            f"Please help me design an novel {lang_display} algorithm. "
            "Here is the template algorithm function implementation: \\n"
        )
        prompt += "[Version 1]\\n"
        prompt += (
            f"{self._wrap_markdown_code_block(str(template_program.program), language)}"
        )

        prompt += (
            "\\n\\nPlease generate a new version of the algorithm. "
            "Think outside the box. Do not modify the function signature (i.e., function name, args, ...)\\n"
            f"Please generate your algorithm in ```{language} ...``` block. "
            "Only output the code and do not give additional outputs. "
        )
        return prompt

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extracts the code block from the LLM's response."""
        if not response:
            return None
        match = re.search(rf"```(?:{language})?\s*\n(.*?)\n```", response, re.DOTALL)
        return match.group(1).strip() if match else None
