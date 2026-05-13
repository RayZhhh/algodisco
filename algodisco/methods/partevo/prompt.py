# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from textwrap import dedent
from typing import Dict, List, Optional

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

_REFLECTION_OUTPUT_TEMPLATE = dedent("""
    Return your answer in exactly the following format:

    ### Reflection
    1. ...
    2. ...

    Do not output anything before or after this section.
    """).strip()

_SUMMARY_OUTPUT_TEMPLATE = dedent("""
    Return your answer in exactly the following format:

    ### Summary
    ...

    Do not output anything before or after this section.
    """).strip()

_ALGO_TEMPLATE = dedent("""
    ### Idea
    {idea}

    ### Code
    {code}

    Evaluator score: {score}
    """).strip()


class PartEvoPromptAdapter:
    """Prompt constructor and response parser for PartEvo.

    The original PartEvo implementation uses multiple prompt families for
    different operator roles. This adapter keeps the same operator semantics but
    rewrites the prompt and parsing format to match the rest of this repository:

    - generated algorithms always use ``### Idea`` / ``### Code`` sections;
    - auxiliary reasoning calls use ``### Reflection`` or ``### Summary``.
    """

    def _wrap_markdown_code_block(self, code: str, language: str = "python") -> str:
        """Wrap raw code in a fenced Markdown block."""
        return f"```{language}\n{code.strip()}\n```"

    def _render_prompt(self, template: str, **kwargs: str) -> str:
        """Render one prompt template and trim leading/trailing whitespace."""
        return template.format(**kwargs).strip()

    def _format_output_instructions(self, language: str) -> str:
        """Render the standard algorithm-output constraint block."""
        return _OUTPUT_INSTRUCTIONS_TEMPLATE.format(language=language)

    def _format_algo(self, algo: AlgoProto, language: str = "python") -> str:
        """Format one algorithm with idea, code, and score for prompt context."""
        return _ALGO_TEMPLATE.format(
            idea=algo.get("idea", "No description"),
            code=self._wrap_markdown_code_block(str(algo.program), language),
            score=algo.score,
        )

    def _format_brief_catalog(self, algos: List[AlgoProto]) -> str:
        """Format a compact idea/score catalog used during initialization and summary."""
        if not algos:
            return "No accepted algorithms yet."

        lines = []
        for index, algo in enumerate(algos, start=1):
            lines.append(
                f"- Algorithm #{index} | Score: {algo.score}\n"
                f"  Idea: {algo.get('idea', 'No description')}"
            )
        return "\n".join(lines)

    def construct_prompt_init(
        self,
        task_description: str,
        current_population: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the initialization prompt used before clusters exist."""
        if current_population:
            context = dedent(f"""
                I already have the following accepted algorithms:

                {self._format_brief_catalog(current_population)}

                Please propose a new algorithm that is meaningfully different
                from the ideas above. Simple restyling or tiny parameter changes
                are not enough.
                """).strip()
        else:
            context = "Please propose a strong and novel algorithm for this task."

        prompt = dedent("""
            {task_description}

            {context}

            1. First, describe your new algorithm idea and its main mechanism under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            context=context,
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_reflection(
        self,
        task_description: str,
        parent: AlgoProto,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the auxiliary reflection prompt used before ``re``."""
        prompt = dedent("""
            {task_description}

            I have one existing algorithm:

            {algo_prompt}

            Please critique this algorithm and propose at most 3 concrete,
            high-impact improvements that could lead to a better successor.

            Keep your suggestions implementable within the following function template:
            ```{language}
            {template_program}
            ```

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            algo_prompt=self._format_algo(parent, language),
            language=language,
            template_program=template_program.strip(),
            output_instructions=_REFLECTION_OUTPUT_TEMPLATE,
        )

    def construct_prompt_re(
        self,
        task_description: str,
        parent: AlgoProto,
        reflection: str,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the reflection-guided evolution prompt for ``re``."""
        prompt = dedent("""
            {task_description}

            I have one current algorithm:

            {algo_prompt}

            Expert reflection:
            {reflection}

            Please create a new algorithm that directly addresses the most
            important weaknesses above. Superficial refactoring is not enough.

            1. First, describe the new algorithm idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            algo_prompt=self._format_algo(parent, language),
            reflection=reflection.strip() if reflection else "No reflection available.",
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_summary(
        self,
        task_description: str,
        archive_context: Dict[str, List[AlgoProto]],
        current_summary: str = "",
    ) -> str:
        """Construct the auxiliary archive-summary prompt used before ``se``."""
        elites = archive_context.get("elites", [])
        hard_negatives = archive_context.get("hard_negatives", [])
        prompt = dedent("""
            {task_description}

            You are reviewing search progress across many algorithm attempts.

            Elite algorithms:
            {elite_catalog}

            Strong but non-elite algorithms:
            {negative_catalog}

            Previous summary:
            {current_summary}

            Please summarize which ideas appear promising, which patterns seem
            weak, and what future search directions look worth exploring.

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            elite_catalog=self._format_brief_catalog(elites),
            negative_catalog=self._format_brief_catalog(hard_negatives),
            current_summary=(
                current_summary.strip() if current_summary else "No previous summary."
            ),
            output_instructions=_SUMMARY_OUTPUT_TEMPLATE,
        )

    def construct_prompt_se(
        self,
        task_description: str,
        parent: AlgoProto,
        global_summary: str,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the summary-guided evolution prompt for ``se``."""
        prompt = dedent("""
            {task_description}

            Current algorithm:

            {algo_prompt}

            Global search summary:
            {global_summary}

            Please create a new algorithm that improves the current one while
            following the useful high-level patterns in the summary. Superficial
            refactoring is not enough.

            1. First, describe the new algorithm idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            algo_prompt=self._format_algo(parent, language),
            global_summary=(
                global_summary.strip()
                if global_summary
                else "No global summary available."
            ),
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_cn(
        self,
        task_description: str,
        parents: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the cross-niche synthesis prompt for ``cn``."""
        main_parent = parents[0]
        aux_parents = parents[1:]

        aux_text = "\n\n".join(
            f"Auxiliary algorithm #{index}:\n{self._format_algo(parent, language)}"
            for index, parent in enumerate(aux_parents, start=2)
        )
        if not aux_text:
            aux_text = "No auxiliary algorithms available."

        prompt = dedent("""
            {task_description}

            Main algorithm to improve:

            {main_algo}

            Auxiliary algorithms from other niches:

            {aux_algos}

            Please keep the first algorithm as the foundation and integrate
            useful strengths from the auxiliary ones into a better hybrid.

            1. First, describe the new hybrid idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            main_algo=self._format_algo(main_parent, language),
            aux_algos=aux_text,
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=self._format_output_instructions(language),
        )

    def construct_prompt_lge(
        self,
        task_description: str,
        parents: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the local-global evolution prompt for ``lge``."""
        current_parent = parents[0]
        reference_text = "\n\n".join(
            f"Reference algorithm #{index}:\n{self._format_algo(parent, language)}"
            for index, parent in enumerate(parents[1:], start=2)
        )
        if not reference_text:
            reference_text = "No reference algorithm available."

        prompt = dedent("""
            {task_description}

            Current algorithm to evolve:

            {current_algo}

            Stronger references discovered elsewhere:

            {reference_algos}

            Please analyze why the references are stronger and use those
            lessons to push the current algorithm forward. Superficial
            refactoring is not enough.

            1. First, describe the new algorithm idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """)
        return self._render_prompt(
            prompt,
            task_description=task_description.strip(),
            current_algo=self._format_algo(current_parent, language),
            reference_algos=reference_text,
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
        """Extract one ``### Section`` block from a model response."""
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
        """Extract the idea section from an algorithm-generation response."""
        return self._extract_section(response, "Idea", next_sections=["Code"])

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extract code from a generation response."""
        return extract_code_from_response(response, language=language)

    def extract_reflection(self, response: str) -> Optional[str]:
        """Extract the reflection section from an auxiliary response."""
        return self._extract_section(response, "Reflection")

    def extract_summary(self, response: str) -> Optional[str]:
        """Extract the summary section from an auxiliary response."""
        return self._extract_section(response, "Summary")
