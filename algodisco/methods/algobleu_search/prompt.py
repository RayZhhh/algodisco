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
        self, task_description: str, sorted_algos: List[AlgoProto]
    ) -> str:
        """Constructs a few-shot prompt to guide the LLM."""
        if task_description:
            prompt = (
                "Here is the task description:\n"
                f"<task>\n{task_description}\n</task>\n\n"
                "Below are some existing Python algorithms that attempt to solve this task. "
                "They are provided for context on different approaches.\n\n"
            )
        else:
            prompt = (
                "Please help me design an novel Python algorithm function. "
                "Here is an example algorithm function implementation: \n"
            )
        if len(sorted_algos) > 1:
            prompt += "[Version 1]\n"

        language = sorted_algos[0].language
        prompt += f"{self._wrap_markdown_code_block(str(sorted_algos[0].program), language)}"

        for i in range(1, len(sorted_algos)):
            prompt += f"\n\nWe find that the below version outperforms [Version {i}]."
            prompt += f"\n[Version {i + 1}]\n"
            prompt += self._wrap_markdown_code_block(
                str(sorted_algos[i].program), language
            )
        prompt += (
            "\n\nPlease generate an improved version of the algorithm. "
            "Think outside the box. Do not modify the function signature (i.e., function name, args, ...)"
            f"Please generate your algorithm in ```{language} ...``` block. "
            "Only output the code and do not give additional outputs. "
            # "Your code should be concise if possible."
        )
        return prompt

    def construct_idea_summary_prompt(self, algo: AlgoProto) -> str:
        """Constructs a prompt for the LLM to summarize the core idea of the code."""
        prompt = (
            "Please read the following Python code and summarize its core idea and algorithmic approach in natural language."
            "The summary should be concise and descriptive, capturing the essence of the algorithm."
            "\n\nCode:\n"
            f"{self._wrap_markdown_code_block(str(algo.program), algo.language)}"
            "\n\nSummary:"
        )
        return prompt

    def extract_code(self, response: str, language="python") -> Optional[str]:
        """Extracts the Python code block from the LLM's response."""
        if not response:
            return None
        # Extract code
        code_match = re.search(
            rf"```(?:{language})?\s*\n(.*?)\n```",
            response,
            re.DOTALL,
        )
        code = code_match.group(1).strip() if code_match else None
        return code


if __name__ == "__main__":
    code1 = """
def f1():
    return 0
    """

    code2 = """
def f2():
    return 1
    """

    code3 = """
def f3():
    return 2
        """
    res = PromptAdapter().construct_prompt(
        "task description", [code1, code2, code3]
    )
    print(res)
