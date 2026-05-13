# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from textwrap import dedent
from typing import List, Optional

from algodisco.base.algo import AlgoProto
from algodisco.toolkit.program_parser.utils import extract_code_from_response

_OUTPUT_INSTRUCTIONS_TEMPLATE = dedent("""
    Return your answer in exactly the following format:

    ### Idea
    <algorithm idea>

    ### Code
    ```{language}
    ...
    ```

    Do not output anything before or after these two sections.
    """).strip()

_INDIV_TEMPLATE = dedent("""
    No. {index} algorithm idea and the corresponding code are:
    ### Idea
    {idea}

    ### Code
    {code}

    Evaluator score: {score}
    """).strip()

_ALGO_TEMPLATE = dedent("""
    ### Idea
    {idea}

    ### Code
    {code}

    Evaluator score: {score}
    """).strip()

_PROMPT_TEMPLATE_I1 = dedent("""
    {task_description}

    Please help me design a novel {language_capitalized} algorithm.

    1. First, describe your new algorithm idea and main steps under `### Idea`.
    2. Next, implement the following {language_capitalized} function under `### Code`:
    {template_program}

    {output_instructions}
    """).strip()

_PROMPT_TEMPLATE_E1 = dedent("""
    {task_description}

    I have {num_indivs} existing algorithms with their codes as follows:

    {indivs_prompt}

    Please help me create a new algorithm that is structurally different from the given ones and is likely to achieve stronger evaluator performance.

    1. First, describe your new algorithm idea and main steps under `### Idea`.
    2. Next, implement the following {language_capitalized} function under `### Code`:
    {template_program}

    {output_instructions}
    """).strip()

_PROMPT_TEMPLATE_E2 = dedent("""
    {task_description}

    I have {num_indivs} existing algorithms with their codes as follows:

    {indivs_prompt}

    Please help me create a new algorithm that keeps a useful backbone from the given ones while changing the structure enough to form a genuinely new candidate.

    1. First, infer the useful common or complementary backbone idea from the provided algorithms internally.
    2. Next, describe your new algorithm idea under `### Idea`.
    3. Then, implement the following {language_capitalized} function under `### Code`:
    {template_program}

    {output_instructions}
    """).strip()

_PROMPT_TEMPLATE_M1 = dedent("""
    {task_description}

    I have one algorithm with its code as follows.

    {algo_prompt}

    Please create a new algorithm that can be seen as a modified version of the provided one, but with a noticeably different structure or mechanism.

    1. First, describe your new algorithm idea and main steps under `### Idea`.
    2. Next, implement the following {language_capitalized} function under `### Code`:
    {template_program}

    {output_instructions}
    """).strip()

_PROMPT_TEMPLATE_M2 = dedent("""
    {task_description}

    I have one algorithm with its code as follows.

    {algo_prompt}

    Please identify the main scoring logic, priorities, or parameters in the provided algorithm, then create a new algorithm that adjusts them in a meaningful way.

    1. First, describe your new algorithm idea and main steps under `### Idea`.
    2. Next, implement the following {language_capitalized} function under `### Code`:
    {template_program}

    {output_instructions}
    """).strip()

_PROMPT_TEMPLATE_S1 = dedent("""
    {task_description}

    I have {num_indivs} algorithms collected along one promising search path:

    {indivs_prompt}

    Please synthesize a new algorithm that meaningfully combines the strongest ideas from all of them while remaining a coherent single design.

    1. First, identify the most helpful ideas that recur or complement each other in these algorithms internally.
    2. Next, describe your synthesized algorithm idea under `### Idea`.
    3. Then, implement the following {language_capitalized} function under `### Code`:
    {template_program}

    {output_instructions}
    """).strip()


class MCTSAHDPromptAdapter:
    """Prompt constructor and response parser for MCTS-AHD.

    Each operator gets its own prompt family because the tree search uses
    different kinds of context:

    - `i1` for pure initialization;
    - `e1` / `e2` for exploratory or crossover-style expansion;
    - `m1` / `m2` for single-parent mutations;
    - `s1` for path-level synthesis.
    """

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        """Wrap raw code into a fenced Markdown block."""
        return f"```{language}\n{code.strip()}\n```"

    def _format_output_instructions(self, language: str) -> str:
        """Render the fixed output-format instructions."""
        return _OUTPUT_INSTRUCTIONS_TEMPLATE.format(language=language)

    def _format_indiv(self, index: int, indi: AlgoProto, language: str) -> str:
        """Format one numbered parent algorithm for prompt injection."""
        return _INDIV_TEMPLATE.format(
            index=index,
            idea=indi.get("idea", "No description"),
            code=self._wrap_markdown_code_block(str(indi.program), language),
            score=indi.score,
        )

    def _format_algo(self, indi: AlgoProto, language: str) -> str:
        """Format one single-parent algorithm block."""
        return _ALGO_TEMPLATE.format(
            idea=indi.get("idea", "No description"),
            code=self._wrap_markdown_code_block(str(indi.program), language),
            score=indi.score,
        )

    def _render_prompt(self, template: str, **kwargs: str) -> str:
        """Render and normalize one prompt template."""
        return template.format(**kwargs).strip()

    def construct_prompt_i1(
        self,
        task_description: str,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the initialization prompt for the ``i1`` operator."""
        return self._render_prompt(
            _PROMPT_TEMPLATE_I1,
            task_description=task_description.strip(),
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_e1(
        self,
        task_description: str,
        indivs: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the exploratory prompt for the ``e1`` operator."""
        indivs_prompt = "\n\n".join(
            self._format_indiv(index + 1, indi, language)
            for index, indi in enumerate(indivs)
        )
        return self._render_prompt(
            _PROMPT_TEMPLATE_E1,
            task_description=task_description.strip(),
            num_indivs=str(len(indivs)),
            indivs_prompt=indivs_prompt,
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_e2(
        self,
        task_description: str,
        indivs: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the crossover prompt for the ``e2`` operator."""
        indivs_prompt = "\n\n".join(
            self._format_indiv(index + 1, indi, language)
            for index, indi in enumerate(indivs)
        )
        return self._render_prompt(
            _PROMPT_TEMPLATE_E2,
            task_description=task_description.strip(),
            num_indivs=str(len(indivs)),
            indivs_prompt=indivs_prompt,
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_m1(
        self,
        task_description: str,
        indi: AlgoProto,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the structural mutation prompt for ``m1``."""
        return self._render_prompt(
            _PROMPT_TEMPLATE_M1,
            task_description=task_description.strip(),
            algo_prompt=self._format_algo(indi, language),
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_m2(
        self,
        task_description: str,
        indi: AlgoProto,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the parameter-priority mutation prompt for ``m2``."""
        return self._render_prompt(
            _PROMPT_TEMPLATE_M2,
            task_description=task_description.strip(),
            algo_prompt=self._format_algo(indi, language),
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_s1(
        self,
        task_description: str,
        indivs: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the path-synthesis prompt for ``s1``."""
        indivs_prompt = "\n\n".join(
            self._format_indiv(index + 1, indi, language)
            for index, indi in enumerate(indivs)
        )
        return self._render_prompt(
            _PROMPT_TEMPLATE_S1,
            task_description=task_description.strip(),
            num_indivs=str(len(indivs)),
            indivs_prompt=indivs_prompt,
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def _extract_section(
        self,
        response: str,
        section_name: str,
        next_sections: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Extract one named Markdown section from the model response."""
        if not response:
            return None

        next_sections = next_sections or []
        if next_sections:
            next_pattern = "|".join(re.escape(section) for section in next_sections)
            pattern = (
                rf"^\s*###\s*{re.escape(section_name)}\s*$\s*"
                rf"(.*?)(?=^\s*###\s*(?:{next_pattern})\s*$|\Z)"
            )
        else:
            pattern = rf"^\s*###\s*{re.escape(section_name)}\s*$\s*(.*)\Z"

        match = re.search(pattern, response, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def extract_idea(self, response: str) -> Optional[str]:
        """Extract the `### Idea` section from a response."""
        section_idea = self._extract_section(response, "Idea", next_sections=["Code"])
        return section_idea.strip() if section_idea else None

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extract the `### Code` section and parse the code block from it."""
        code_section = self._extract_section(response, "Code")
        if not code_section:
            return None
        # Parsing only the code section makes extraction more robust to models
        # that accidentally include extra fenced blocks elsewhere in the reply.
        return extract_code_from_response(code_section, language)
