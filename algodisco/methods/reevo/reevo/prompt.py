# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import re
from textwrap import dedent
from typing import List, Optional

from algodisco.base.algo import AlgoProto
from algodisco.toolkit.program_parser.utils import extract_code_from_response

_OUTPUT_INSTRUCTIONS = dedent("""
    Return your answer in exactly the following format:

    ### Idea
    <algorithm idea>

    ### Code
    ```{language}
    ...
    ```

    Do not output anything before or after these two sections.
    """).strip()

_REFLECTION_OUTPUT = dedent("""
    Return your answer in exactly the following format:

    ### Reflection
    1. ...
    2. ...

    Do not output anything before or after this section.
    """).strip()

_ALGO_TEMPLATE = dedent("""
    ### Idea
    {idea}

    ### Code
    {code}

    Evaluator score: {score}
    """).strip()


class ReEvoPromptAdapter:
    """Prompt constructor and parser for iterative ReEvo.

    The iterative adaptation uses three prompt families:

    - bootstrap prompts for early diversity around the seed algorithm;
    - short-term reflection + crossover prompts for pairwise comparison;
    - long-term reflection + mutation prompts for memory-guided refinement.
    """

    def _wrap_code(self, code: str, language: str) -> str:
        """Wrap code in a fenced Markdown block for prompt readability."""
        return f"```{language}\n{code.strip()}\n```"

    def _format_algo(self, algo: AlgoProto, language: str) -> str:
        """Format one algorithm with idea, code, and evaluator score."""
        return _ALGO_TEMPLATE.format(
            idea=algo.get("idea", "No description"),
            code=self._wrap_code(str(algo.program), language),
            score=algo.score,
        )

    def _format_brief_population(self, population: List[AlgoProto]) -> str:
        """Format a compact catalog of accepted algorithms."""
        if not population:
            return "No accepted algorithms yet."
        lines = []
        for index, algo in enumerate(population, start=1):
            lines.append(
                f"- Algorithm #{index} | Score: {algo.score}\n"
                f"  Idea: {algo.get('idea', 'No description')}"
            )
        return "\n".join(lines)

    def construct_prompt_init(
        self,
        task_description: str,
        seed_algo: AlgoProto,
        current_population: List[AlgoProto],
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the bootstrap prompt used before pairwise search starts."""
        context = self._format_brief_population(current_population)
        return dedent("""
            {task_description}

            I already have this seed algorithm:

            {seed_algo}

            Current accepted algorithms:
            {population_catalog}

            Please create a new algorithm that is meaningfully different from the
            current accepted ones while remaining competitive with the seed.

            1. First, describe the new algorithm idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """).strip().format(
            task_description=task_description.strip(),
            seed_algo=self._format_algo(seed_algo, language),
            population_catalog=context,
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=_OUTPUT_INSTRUCTIONS.format(language=language),
        )

    def construct_prompt_short_reflection(
        self,
        task_description: str,
        better_parent: AlgoProto,
        worse_parent: AlgoProto,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct one short-term reflection prompt for a parent pair."""
        return dedent("""
            {task_description}

            Better algorithm:
            {better_algo}

            Worse algorithm:
            {worse_algo}

            Compare the two algorithms and extract the most important reasons
            the better one is stronger. Focus on actionable insights that can
            be used to generate an improved offspring.

            The offspring must still fit inside this function template:
            ```{language}
            {template_program}
            ```

            {output_instructions}
            """).strip().format(
            task_description=task_description.strip(),
            better_algo=self._format_algo(better_parent, language),
            worse_algo=self._format_algo(worse_parent, language),
            language=language,
            template_program=template_program.strip(),
            output_instructions=_REFLECTION_OUTPUT,
        )

    def construct_prompt_crossover(
        self,
        task_description: str,
        better_parent: AlgoProto,
        worse_parent: AlgoProto,
        reflection_text: str,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the offspring-generation prompt that consumes short memory."""
        return dedent("""
            {task_description}

            Better parent:
            {better_algo}

            Worse parent:
            {worse_algo}

            Short-term reflection:
            {reflection_text}

            Create a new algorithm that inherits the best mechanisms from the
            stronger parent, fixes weaknesses in the weaker one, and is not a
            trivial rewrite of either parent.

            1. First, describe the new offspring idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """).strip().format(
            task_description=task_description.strip(),
            better_algo=self._format_algo(better_parent, language),
            worse_algo=self._format_algo(worse_parent, language),
            reflection_text=reflection_text.strip() if reflection_text else "No reflection available.",
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=_OUTPUT_INSTRUCTIONS.format(language=language),
        )

    def construct_prompt_long_reflection(
        self,
        task_description: str,
        prior_reflection: str,
        new_reflections: List[str],
    ) -> str:
        """Construct the long-term reflection refresh prompt."""
        joined_reflections = "\n\n".join(new_reflections) if new_reflections else "No new reflections."
        return dedent("""
            {task_description}

            You are maintaining a long-term search memory for algorithm design.

            Prior long-term reflection:
            {prior_reflection}

            New short-term reflections:
            {new_reflections}

            Synthesize the stable lessons, promising patterns, and recurring
            mistakes into one compact guidance note for future mutations.

            {output_instructions}
            """).strip().format(
            task_description=task_description.strip(),
            prior_reflection=prior_reflection.strip() if prior_reflection else "No prior reflection.",
            new_reflections=joined_reflections,
            output_instructions=_REFLECTION_OUTPUT,
        )

    def construct_prompt_mutation(
        self,
        task_description: str,
        elitist: AlgoProto,
        long_term_reflection: str,
        template_program: str,
        language: str = "python",
    ) -> str:
        """Construct the mutation prompt driven by long-term reflection."""
        return dedent("""
            {task_description}

            Current elitist algorithm:
            {elitist_algo}

            Long-term reflection:
            {long_term_reflection}

            Mutate the elitist into a new algorithm that keeps its strongest
            backbone while exploring a promising alternative suggested by the
            long-term reflection.

            1. First, describe the mutated idea under `### Idea`.
            2. Next, implement the following {language_capitalized} function under `### Code`:
            {template_program}

            {output_instructions}
            """).strip().format(
            task_description=task_description.strip(),
            elitist_algo=self._format_algo(elitist, language),
            long_term_reflection=long_term_reflection.strip() if long_term_reflection else "No long-term reflection available.",
            language_capitalized=language.capitalize(),
            template_program=template_program.strip(),
            output_instructions=_OUTPUT_INSTRUCTIONS.format(language=language),
        )

    def _extract_section(
        self,
        response: str,
        section_name: str,
        next_sections: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Extract one named Markdown section from a model response."""
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
        """Extract the `### Idea` section from a generation response."""
        return self._extract_section(response, "Idea", next_sections=["Code"])

    def extract_code(self, response: str, language: str = "python") -> Optional[str]:
        """Extract the fenced code block from a generation response."""
        return extract_code_from_response(response, language=language)

    def extract_reflection(self, response: str) -> Optional[str]:
        """Extract the `### Reflection` section from an auxiliary response."""
        return self._extract_section(response, "Reflection")
