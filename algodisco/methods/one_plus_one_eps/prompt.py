# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from textwrap import dedent
from typing import Optional

from algodisco.base.algo import AlgoProto
from algodisco.toolkit.program_parser.utils import extract_code_from_response

_TASK_DESCRIPTION_TEMPLATE = "Task Description: {task_description}"

_INTRO_TEMPLATE = dedent("""
    Please help me design a novel {language_capitalized} algorithm.
    Here is the current best algorithm function implementation:
    """).strip()

_VERSION_TEMPLATE = dedent("""
    [Version 1]
    {code_block}
    """).strip()

_IMPROVEMENT_REQUEST_TEMPLATE = dedent("""
    Please generate an improved version of the algorithm.
    Think outside the box. Do not modify the function signature (i.e., function name, args, ...)
    Please generate your algorithm in ```{language} ...``` block.
    Only output the code and do not give additional outputs.
    """).strip()


class PromptAdapter:
    """Constructs prompts for the LLM to generate improved algorithm variations using (1+1)-EPS."""

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        return f"```{language}\n{code.strip()}\n```"

    def _render_prompt(self, template: str, **kwargs: str) -> str:
        return template.format(**kwargs).strip()

    def construct_prompt(
        self, best_program: AlgoProto, task_description: str = ""
    ) -> str:
        """Constructs a prompt based on the best program found so far."""
        language = best_program.language or "python"
        language_capitalized = language.capitalize()

        prompt = ""
        if task_description:
            prompt += self._render_prompt(
                _TASK_DESCRIPTION_TEMPLATE,
                task_description=task_description,
            )
            prompt += "\n\n"

        prompt += self._render_prompt(
            _INTRO_TEMPLATE,
            language_capitalized=language_capitalized,
        )
        prompt += "\n\n"
        prompt += self._render_prompt(
            _VERSION_TEMPLATE,
            code_block=self._wrap_markdown_code_block(
                str(best_program.program), language
            ),
        )

        prompt += "\n\n"
        prompt += self._render_prompt(
            _IMPROVEMENT_REQUEST_TEMPLATE,
            language=language,
        )
        return prompt

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extracts the code block from the LLM's response."""
        return extract_code_from_response(response, language)
