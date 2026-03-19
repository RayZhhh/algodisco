# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from typing import List, Optional
from algodisco.base.algo import AlgoProto


class EoHPromptAdapter:
    """Constructs prompts for EoH operators: i1, e1, e2, m1, m2."""

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        return f"```{language}\n{code.strip()}\n```"

    def _format_indiv(self, index: int, indi: AlgoProto, language: str) -> str:
        idea = indi.get("idea", "No description")
        code = self._wrap_markdown_code_block(str(indi.program), language)
        return (
            f"No. {index} algorithm idea and the corresponding code are:\n"
            f"<idea>{idea}</idea>\n"
            f"{code}"
        )

    def construct_prompt_i1(self, task_description: str, template_program: str, language: str = "python") -> str:
        return f"""{task_description.strip()}

Please help me design an novel {language.capitalize()} algorithm. 

1. First, describe your new algorithm idea and main steps in one sentence. The description must be inside <idea></idea> tags.
2. Next, implement the following Python function:
{template_program.strip()}

Please generate your algorithm in ```{language} ...``` block.
Do not give additional explanations.
""".strip()

    def construct_prompt_e1(self, task_description: str, indivs: List[AlgoProto], template_program: str, language: str = "python") -> str:
        indivs_prompt = "\n\n".join(
            self._format_indiv(i + 1, indi, language) for i, indi in enumerate(indivs)
        )
        return f"""{task_description.strip()}

I have {len(indivs)} existing algorithms with their codes as follows:

{indivs_prompt}

Please help me create a new algorithm that has a totally different form from the given ones. 

1. First, describe your new algorithm idea and main steps in one sentence. The description must be inside <idea></idea> tags.
2. Next, implement the following Python function:
{template_program.strip()}

Please generate your algorithm in ```{language} ...``` block.
Do not give additional explanations.
""".strip()

    def construct_prompt_e2(self, task_description: str, indivs: List[AlgoProto], template_program: str, language: str = "python") -> str:
        indivs_prompt = "\n\n".join(
            self._format_indiv(i + 1, indi, language) for i, indi in enumerate(indivs)
        )
        return f"""{task_description.strip()}

I have {len(indivs)} existing algorithms with their codes as follows:

{indivs_prompt}

Please help me create a new algorithm that has a totally different form from the given ones but can be motivated from them.

1. Firstly, identify the common backbone idea in the provided algorithms. 
2. Secondly, based on the backbone idea describe your new algorithm idea in one sentence. The description must be inside <idea></idea> tags.
3. Thirdly, implement the following Python function:
{template_program.strip()}

Please generate your algorithm in ```{language} ...``` block.
Do not give additional explanations.
""".strip()

    def construct_prompt_m1(self, task_description: str, indi: AlgoProto, template_program: str, language: str = "python") -> str:
        idea = indi.get("idea", "No description")
        code = self._wrap_markdown_code_block(str(indi.program), language)
        return f"""{task_description.strip()}

I have one algorithm with its code as follows. 

Idea: <idea>{idea}</idea>
Code:
{code}

Please assist me in creating a new algorithm that has a different form but can be a modified version of the algorithm provided.

1. First, describe your new algorithm idea and main steps in one sentence. The description must be inside <idea></idea> tags.
2. Next, implement the following Python function:
{template_program.strip()}

Please generate your algorithm in ```{language} ...``` block.
Do not give additional explanations.
""".strip()

    def construct_prompt_m2(self, task_description: str, indi: AlgoProto, template_program: str, language: str = "python") -> str:
        idea = indi.get("idea", "No description")
        code = self._wrap_markdown_code_block(str(indi.program), language)
        return f"""{task_description.strip()}

I have one algorithm with its code as follows. 

Idea: <idea>{idea}</idea>
Code:
{code}

Please identify the main algorithm parameters and assist me in creating a new algorithm that has a different parameter settings of the score function provided.

1. First, describe your new algorithm idea and main steps in one sentence. The description must be inside <idea></idea> tags.
2. Next, implement the following Python function:
{template_program.strip()}

Please generate your algorithm in ```{language} ...``` block.
Do not give additional explanations.
""".strip()

    def extract_idea(self, response: str) -> Optional[str]:
        if not response:
            return None
        match = re.search(r'<idea>(.*?)</idea>', response, re.DOTALL)
        return match.group(1).strip() if match else None

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        if not response:
            return None
        # Robust regex for markdown code blocks
        match = re.search(rf"```(?:{language})?\s*\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None
