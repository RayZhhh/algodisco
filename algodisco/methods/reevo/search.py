# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from __future__ import annotations

import copy
import logging
import math
import random
import threading
import time
import traceback
from typing import List, Optional

try:
    from typing import override
except ImportError:
    from typing_extensions import override

from algodisco.base.algo import AlgoProto
from algodisco.base.evaluator import Evaluator
from algodisco.base.llm import LanguageModel
from algodisco.base.logger import AlgoSearchLoggerBase
from algodisco.base.search_method import IterativeSearchBase
from algodisco.common.logging_utils import format_error_box, format_time_info
from algodisco.common.timer import Timer

from algodisco.methods.reevo.config import ReEvoConfig
from algodisco.methods.reevo.database import ReEvoDatabase
from algodisco.methods.reevo.prompt import ReEvoPromptAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ReEvoSearch(IterativeSearchBase):
    """Iterative ReEvo adaptation for AlgoDisco.

    This version deliberately follows AlgoDisco's iterative-search lifecycle
    rather than the upstream batched generational runner. Each sampler thread
    repeatedly selects one operator context, generates one candidate, evaluates
    it with the standard evaluator, and registers it back into an elite
    population.
    """

    def __init__(
        self,
        config: ReEvoConfig,
        evaluator: Evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: ReEvoPromptAdapter = ReEvoPromptAdapter(),
        *,
        tool_mode: bool = False,
    ):
        assert llm or tool_mode

        self._config = config
        self._template_program_str = str(self._config.template_program)
        if not self._template_program_str:
            raise ValueError("The provided template program is empty.")

        self._llm = llm
        self._evaluator = evaluator
        self._logger = logger
        self._prompt_constructor = prompt_constructor
        self._database = ReEvoDatabase(self._config.pop_size)

        # `_lock` protects phase transitions, population registration, and
        # sample accounting. Threads are allowed to run LLM/evaluator work
        # outside this lock for better throughput.
        self._lock = threading.RLock()
        # Short-term reflections feed a shared long-term memory, so their
        # history and refresh state use a dedicated lock.
        self._reflection_lock = threading.Lock()
        # Evaluator capacity is often more constrained than prompt sampling.
        self._evaluator_semaphore = threading.Semaphore(self._config.num_evaluators)
        self._stop_event = threading.Event()

        self._samples_count = 0
        self._last_db_saved_at: int = -1
        self._bootstrap_trials = 0
        self._max_bootstrap_trials = (
            self._config.init_trial_multiplier * self._config.init_pop_size
        )
        self._phase = "bootstrap"

        self._seed_algo: Optional[AlgoProto] = None
        self._searched_algos: List[AlgoProto] = []
        self._long_term_reflection = self._config.external_knowledge.strip()
        self._short_term_reflection_history: List[str] = []
        self._short_term_reflection_version = 0
        self._last_long_term_reflection_version = -1

        self.debug_mode = False
        self.debug_mode_crash = False

    def _has_valid_score(self, score) -> bool:
        """Return whether `score` is finite and therefore usable."""
        if score is None:
            return False
        try:
            return math.isfinite(score)
        except (TypeError, ValueError):
            return False

    def _save_database(self, sample_num: int) -> None:
        """Persist the searchable population plus reflection memory."""
        if not self._logger:
            return

        database_dict = self._database.to_dict()
        database_dict["sample_num"] = sample_num
        database_dict["phase"] = self._phase
        database_dict["long_term_reflection"] = self._long_term_reflection
        self._logger.log_dict(database_dict, "database")
        self._last_db_saved_at = sample_num
        logging.info("Saved database snapshot for sample #%s to logger.", sample_num)

    @override
    def initialize(self) -> None:
        """Evaluate the template once and treat it as the initial seed."""
        if self._logger:
            self._logger.set_log_item_flush_frequency(
                {
                    "database": 1,
                    "algo": self._config.algo_save_frequency,
                }
            )
        logging.info("Evaluating template program...")
        template_proto = AlgoProto(
            program=self._template_program_str,
            language=self._config.language,
        )
        template_proto["phase"] = "template"
        template_proto["operator"] = "seed"
        template_proto["idea"] = "Initial seed/template algorithm."

        with Timer(template_proto, "eval_time"):
            results = self._evaluator.evaluate_program(template_proto.program)

        if results is not None:
            metadata = results.get("metadata", {})
            template_proto["execution_time"] = metadata.get("execution_time", 0.0)
            template_proto["error_msg"] = metadata.get("error_msg", "")
            if results.get("score") is not None:
                template_proto.score = results["score"]

        if not self._has_valid_score(template_proto.score):
            raise RuntimeError("The template program failed evaluation.")

        self._database.register_algo(template_proto)
        self._seed_algo = copy.deepcopy(template_proto)

        with self._lock:
            self._samples_count += 1
            self._searched_algos.append(self._copy_algo_for_storage(template_proto))
            self._log(template_proto, is_template=True, accepted_by_population=True)

    def run(self) -> None:
        """Run the threaded iterative ReEvo loop until termination."""
        try:
            self.initialize()
            logging.info("Starting %s ReEvo sampler threads...", self._config.num_samplers)

            threads = []
            for _ in range(self._config.num_samplers):
                thread = threading.Thread(target=self._bootstrap)
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

        except (KeyboardInterrupt, SystemExit):
            logging.info("Search interrupted by user.")
            self._stop_event.set()
        except Exception:
            error_msg = traceback.format_exc()
            logging.error("An unexpected error occurred during the search process.")
            if self.debug_mode:
                logging.error(format_error_box(error_msg))
                if self.debug_mode_crash:
                    import sys

                    sys.exit(1)
            self._stop_event.set()
        finally:
            with self._lock:
                if self._samples_count != self._last_db_saved_at:
                    self._save_database(self._samples_count)
            if self._logger:
                logging.info("Finalizing logger...")
                self._logger.finish()
            logging.info("Search finished.")

    @override
    def is_stopped(self) -> bool:
        """Return whether the search has reached any stop condition."""
        return self._stop_event.is_set() or (
            self._config.max_samples is not None
            and self._samples_count >= self._config.max_samples
        )

    @override
    def current_num_samples(self) -> int:
        """Return the global number of evaluated samples."""
        with self._lock:
            return self._samples_count

    @override
    def get_config(self) -> ReEvoConfig:
        """Return the active method configuration."""
        return self._config

    @override
    def get_top_k_algos(self, k: int) -> List[AlgoProto]:
        with self._lock:
            return self._get_top_k_algos_from_list(self._searched_algos, k)

    def _try_enter_search_phase(self) -> None:
        """Switch from bootstrap into iterative search once population is ready."""
        if self._phase != "bootstrap":
            return

        if len(self._database) >= self._config.init_pop_size:
            self._phase = "search"
            logging.info(
                "ReEvo bootstrap completed with %s accepted algorithms. Entering search.",
                len(self._database),
            )
            return

        if self._bootstrap_trials >= self._max_bootstrap_trials:
            if len(self._database) >= 2:
                self._phase = "search"
                logging.info(
                    "Bootstrap trial budget exhausted; continuing search with %s accepted algorithms.",
                    len(self._database),
                )
                return

            logging.warning(
                "Bootstrap ended after %s attempts without enough feasible candidates.",
                self._bootstrap_trials,
            )
            self._phase = "finished"
            self._stop_event.set()

    def _call_aux_llm(self, prompt: str) -> str:
        """Execute an auxiliary LLM call used for reflection prompts."""
        assert self._llm is not None
        return self._llm.chat_completion(
            prompt,
            self._config.llm_max_tokens,
            self._config.llm_timeout_seconds,
        )

    def _build_candidate(
        self,
        *,
        operator: str,
        prompt: str,
        phase: str,
        parents: Optional[List[AlgoProto]] = None,
        reflection_guidance: str = "",
        long_term_reflection: str = "",
    ) -> AlgoProto:
        """Create the mutable candidate object shared across one lifecycle."""
        candidate = AlgoProto(language=self._config.language)
        candidate["operator"] = operator
        candidate["prompt"] = prompt
        candidate["phase"] = phase
        if parents is not None:
            candidate["parents"] = parents
            candidate["parent_scores"] = [parent.score for parent in parents]
        if reflection_guidance:
            candidate["reflection_guidance"] = reflection_guidance
        if long_term_reflection:
            candidate["long_term_reflection"] = long_term_reflection
        return candidate

    def _build_init_candidate(self) -> Optional[AlgoProto]:
        """Build one bootstrap candidate around the template seed."""
        if self._seed_algo is None:
            return None

        prompt = self._prompt_constructor.construct_prompt_init(
            self._config.task_description,
            self._seed_algo,
            self._database.population,
            self._template_program_str,
            self._config.language,
        )
        return self._build_candidate(
            operator="init",
            prompt=prompt,
            phase="bootstrap",
            parents=[copy.deepcopy(self._seed_algo)],
        )

    def _refresh_long_term_reflection_if_needed(self, *, force: bool = False) -> str:
        """Refresh long-term memory from the latest short-term reflections."""
        with self._reflection_lock:
            if not self._short_term_reflection_history:
                return self._long_term_reflection

            if not force and (
                self._short_term_reflection_version
                == self._last_long_term_reflection_version
            ):
                return self._long_term_reflection

            # ReEvo's iterative variant uses a sliding window instead of a
            # generational barrier. This makes long-term memory refresh cheap
            # and naturally compatible with threaded sampling.
            reflections = self._short_term_reflection_history[
                -self._config.long_term_reflection_window_size :
            ]
            prompt = self._prompt_constructor.construct_prompt_long_reflection(
                self._config.task_description,
                self._long_term_reflection,
                reflections,
            )
            response = self._call_aux_llm(prompt)
            parsed_reflection = self._prompt_constructor.extract_reflection(response)
            if parsed_reflection:
                self._long_term_reflection = parsed_reflection
                self._last_long_term_reflection_version = (
                    self._short_term_reflection_version
                )
            return self._long_term_reflection

    def _build_crossover_candidate(self) -> Optional[AlgoProto]:
        """Build one reflection-guided crossover candidate."""
        pair = self._database.select_pair(self._config.selection_mode)
        if pair is None:
            return None

        parent_a, parent_b = pair
        better_parent, worse_parent = (
            (parent_a, parent_b) if parent_a.score >= parent_b.score else (parent_b, parent_a)
        )

        # The short-term reflection always compares one better parent against
        # one worse parent. That keeps the prompt sharply focused on a concrete
        # superiority signal rather than vague population-level discussion.
        reflection_prompt = self._prompt_constructor.construct_prompt_short_reflection(
            self._config.task_description,
            better_parent,
            worse_parent,
            self._template_program_str,
            self._config.language,
        )
        reflection_response = self._call_aux_llm(reflection_prompt)
        reflection_text = self._prompt_constructor.extract_reflection(reflection_response) or ""

        prompt = self._prompt_constructor.construct_prompt_crossover(
            self._config.task_description,
            better_parent,
            worse_parent,
            reflection_text,
            self._template_program_str,
            self._config.language,
        )
        return self._build_candidate(
            operator="crossover",
            prompt=prompt,
            phase="search",
            parents=[copy.deepcopy(better_parent), copy.deepcopy(worse_parent)],
            reflection_guidance=reflection_text,
        )

    def _build_mutation_candidate(self) -> Optional[AlgoProto]:
        """Build one mutation candidate from the current elitist and memory."""
        elitist = self._database.get_elitist()
        if elitist is None:
            return None

        long_term_reflection = self._refresh_long_term_reflection_if_needed()
        prompt = self._prompt_constructor.construct_prompt_mutation(
            self._config.task_description,
            elitist,
            long_term_reflection,
            self._template_program_str,
            self._config.language,
        )
        return self._build_candidate(
            operator="mutation",
            prompt=prompt,
            phase="search",
            parents=[copy.deepcopy(elitist)],
            long_term_reflection=long_term_reflection,
        )

    @override
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Select one iterative operator and build the corresponding prompt."""
        with self._lock:
            if self.is_stopped():
                return None

            self._try_enter_search_phase()
            phase = self._phase

        if phase == "finished":
            return None
        if phase == "bootstrap":
            return self._build_init_candidate()
        if phase == "search":
            operators = []
            if len(self._database) >= 2:
                operators.extend(["crossover"] * self._config.crossover_operator_weight)
            if self._database.get_elitist() is not None:
                operators.extend(["mutation"] * self._config.mutation_operator_weight)
            if not operators:
                return None

            # Mutation gets an explicit rate override because it usually has a
            # higher prompt cost after long-term reflection refresh.
            if random.random() < self._config.mutation_rate and "mutation" in operators:
                preferred_operator = "mutation"
            else:
                preferred_operator = random.choice(operators)

            if preferred_operator == "crossover":
                candidate = self._build_crossover_candidate()
                if candidate is not None:
                    return candidate
                return self._build_mutation_candidate()
            return self._build_mutation_candidate()

        return None

    def _bootstrap(self) -> None:
        """Main lifecycle loop for one ReEvo sampler thread."""
        while not self.is_stopped():
            with self._lock:
                if self.is_stopped():
                    self._stop_event.set()
                    break

            try:
                # Threads only synchronize when selecting work and committing
                # results. Prompt generation and evaluation are intentionally
                # left concurrent so ReEvo scales like EoH-style samplers.
                candidate = self.select_and_create_prompt()
                if candidate is None:
                    time.sleep(0.05)
                    continue

                candidate = self.generate(candidate)
                candidate = self.extract_algo_from_response(candidate)
                candidate = self.evaluate(candidate)
                self.register(candidate)
            except (KeyboardInterrupt, SystemExit):
                self._stop_event.set()
                break
            except Exception as exc:
                logging.warning(
                    "Exception in ReEvo sampler thread: %s",
                    traceback.format_exc(),
                )
                if self.debug_mode:
                    logging.error("Debug mode: error in ReEvo sampler thread: %s", exc)
                    logging.error(format_error_box(traceback.format_exc()))
                    if self.debug_mode_crash:
                        self._stop_event.set()
                        raise
                time.sleep(0.2)

    @override
    def generate(self, candidate: AlgoProto) -> AlgoProto:
        """Call the LLM and store the raw text response on the candidate."""
        assert self._llm is not None, "LLM is required for generate()."
        with Timer(candidate, "sample_time"):
            response_text = self._llm.chat_completion(
                candidate["prompt"],
                self._config.llm_max_tokens,
                self._config.llm_timeout_seconds,
            )
        candidate["response_text"] = response_text
        return candidate

    @override
    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """Parse the model response into idea text and executable code."""
        response_text = candidate.get("response_text", "")
        idea = self._prompt_constructor.extract_idea(response_text)
        code = self._prompt_constructor.extract_code(
            response_text,
            language=candidate.language,
        )

        if idea:
            candidate["idea"] = idea
        if code:
            candidate.program = code
        return candidate

    @override
    def evaluate(self, candidate: AlgoProto) -> AlgoProto:
        """Evaluate one candidate program and copy useful metrics back."""
        if not candidate or not candidate.program:
            return candidate

        with Timer(candidate, "eval_time"):
            with self._evaluator_semaphore:
                results = self._evaluator.evaluate_program(candidate.program)

        if results is not None:
            metadata = results.get("metadata", {})
            candidate["execution_time"] = metadata.get("execution_time", 0.0)
            candidate["error_msg"] = metadata.get("error_msg", "")
            if results.get("score") is not None:
                candidate.score = results["score"]
        return candidate

    @override
    def register(self, algo_proto: AlgoProto) -> None:
        """Register one evaluated candidate into memory, population, and logs."""
        if algo_proto is None:
            return

        with self._lock:
            if self.is_stopped():
                return

            self._samples_count += 1
            accepted_by_population = False

            if algo_proto.get("phase") == "bootstrap":
                self._bootstrap_trials += 1

            reflection_guidance = algo_proto.get("reflection_guidance", "")
            if reflection_guidance:
                with self._reflection_lock:
                    # Every successful short-term reflection becomes part of the
                    # rolling evidence base for future long-term reflection.
                    self._short_term_reflection_history.append(reflection_guidance)
                    self._short_term_reflection_version += 1

            if algo_proto.program and self._has_valid_score(algo_proto.score):
                registered_algo_proto = self._copy_algo_for_storage(algo_proto)
                self._searched_algos.append(copy.deepcopy(registered_algo_proto))
                accepted_by_population = self._database.register_algo(
                    registered_algo_proto
                )

            self._try_enter_search_phase()
            self._log(algo_proto, accepted_by_population=accepted_by_population)

    def _log(
        self,
        algo_proto: AlgoProto,
        *,
        is_template: bool = False,
        accepted_by_population: bool = False,
    ) -> None:
        """Write terminal output and structured logger entries for one sample."""
        current_sample_num = self._samples_count
        operator = algo_proto.get("operator", "template")
        phase = algo_proto.get("phase", self._phase)

        if (
            self._config.db_save_frequency is not None
            and current_sample_num % self._config.db_save_frequency == 0
        ):
            # Snapshotting is keyed off the global sample counter so logs stay
            # deterministic even when candidates finish out of order.
            self._save_database(current_sample_num)

        tag = " (Template)" if is_template else f" ({operator}/{phase})"
        algo_id_str = f"#{current_sample_num}{tag}"

        score_val = algo_proto.score
        score_str = f"{score_val:10.4f}" if score_val is not None else f"{'None':>10}"
        sample_time_val = algo_proto.get("sample_time", 0.0)
        sample_time_str = (
            f"{sample_time_val:6.2f}s" if not is_template else f"{'N/A':>7}"
        )

        eval_time_val = algo_proto.get("eval_time", 0.0)
        execution_time_val = algo_proto.get("execution_time", None)
        time_info = format_time_info(eval_time_val, execution_time_val)
        log_population_acceptance = (not is_template) or accepted_by_population

        status_parts = [
            f"Algo {algo_id_str:<24}",
            f"Score: {score_str}",
            f"Sample: {sample_time_str}",
            time_info,
        ]
        if log_population_acceptance:
            status_parts.append(f"Pop: {'Y' if accepted_by_population else 'N'}")
        status_parts.append(f"Phase: {self._phase}")
        logging.info(
            " | ".join(status_parts)
        )

        if self._logger:
            log_algo_proto = copy.deepcopy(algo_proto)
            log_algo_proto.keep_metadata_keys(self._config.keep_metadata_keys)
            log_entry = log_algo_proto.to_dict()
            log_entry.update(
                {
                    "sample_num": current_sample_num,
                    "operator": operator,
                    "phase": phase,
                    "sample_time": 0.0 if is_template else sample_time_val,
                    "pop_size": len(self._database),
                    "best_score": self._database.get_best_score(),
                }
            )
            if log_population_acceptance:
                log_entry["accepted_by_population"] = accepted_by_population
            self._logger.log_dict(log_entry, "algo")
