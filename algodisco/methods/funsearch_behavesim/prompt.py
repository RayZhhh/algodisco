# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from typing import List, Optional

from algodisco.base.algo import AlgoProto


class PromptAdapter:
    """Constructs prompts for the LLM to generate new algorithm variations."""

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        return f"```{language}\n{code.strip()}\n```"

    def construct_prompt(
        self, task_description: str, sorted_algos: List[AlgoProto]
    ) -> str:
        """Constructs a few-shot prompt to guide the LLM."""
        language = sorted_algos[0].language if sorted_algos else "python"
        lang_display = language.capitalize()

        if task_description:
            prompt = (
                "Here is the task description:\n"
                f"<task>\n{task_description}\n</task>\n\n"
                f"Below are some existing {lang_display} algorithms that attempt to solve this task. "
                "They are provided for context on different approaches.\n\n"
            )
        else:
            prompt = (
                f"Please help me design an novel {lang_display} algorithm function. "
                "Here is an example algorithm function implementation: \n"
            )

        if len(sorted_algos) > 1:
            prompt += "[Version 1]\n"
        
        prompt += f"{self._wrap_markdown_code_block(str(sorted_algos[0].program), language)}"

        for i in range(1, len(sorted_algos)):
            prompt += f"\n\nWe find that the below version outperforms [Version {i}]."
            prompt += f"\n[Version {i + 1}]\n"
            prompt += self._wrap_markdown_code_block(str(sorted_algos[i].program), language)
        
        prompt += (
            "\n\nPlease generate an improved version of the algorithm. "
            "Think outside the box. Do not modify the function signature (i.e., function name, args, ...)\n"
            f"Please generate your algorithm in ```{language} ...``` block. "
            "Only output the code and do not give additional outputs. "
            "Your code should be concise if possible."
        )
        return prompt

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extracts the Python code block from the LLM's response."""
        if not response:
            return None
        # Extract code
        code_match = re.search(rf"```(?:{language})?\s*\n(.*?)\n```", response, re.DOTALL)
        code = code_match.group(1).strip() if code_match else None
        return code

if __name__ == "__main__":
    code1 = AlgoProto(program="def f1():\n    return 0", language="python")
    code2 = AlgoProto(program="def f2():\n    return 1", language="python")
    code3 = AlgoProto(program="def f3():\n    return 2", language="python")
    res = PromptAdapter().construct_prompt(
        "task description", [code1, code2, code3]
    )
    print(res)