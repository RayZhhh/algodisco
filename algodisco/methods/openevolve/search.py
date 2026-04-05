# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import copy
import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

try:
    from typing import override
except ImportError:
    from typing_extensions import override

from algodisco.base.llm import LanguageModel
from algodisco.base.evaluator import EvalResult, Evaluator
from algodisco.base.algo import AlgoProto
from algodisco.base.search_method import IterativeSearchBase
from algodisco.base.logger import AlgoSearchLoggerBase
from algodisco.common.timer import Timer
from algodisco.common.logging_utils import format_time_info, format_error_box

from algodisco.methods.openevolve.config import OpenEvolveConfig
from algodisco.methods.openevolve.database import ProgramDatabase, get_fitness_score
from algodisco.methods.openevolve.prompt import PromptConstructor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class OpenEvolve(IterativeSearchBase):
    """Drive threaded sampling, evaluation, registration, and logging."""

    def __init__(
        self,
        config: OpenEvolveConfig,
        evaluator: Evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptConstructor = None,
        *,
        tool_mode=False,
    ):
        # --- Tool mode assertion ---
        assert llm or tool_mode
        # ---------------------------

        self._config = config
        self._template_program_str = str(self._config.template_program)
        if not self._template_program_str:
            raise ValueError("The provided template program is empty.")

        self._llm = llm
        self._evaluator: Evaluator = evaluator
        self._database = ProgramDatabase(config)
        self._logger = logger

        # Prompt construction is kept modular so prompt behavior can evolve
        # without changing the outer search interface.
        self._prompt_constructor = prompt_constructor or PromptConstructor(
            config=self._config
        )

        self._lock = threading.Lock()
        # `_samples_count` counts registered candidates plus the initial template.
        self._samples_count = 0
        # Limit concurrent evaluator calls independently from sampler count.
        self._evaluator_semaphore = threading.Semaphore(self._config.num_evaluators)
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=self._config.num_samplers)
        # Track in-flight work per island so scheduling stays balanced even
        # though this implementation uses threads instead of worker processes.
        self._island_pending = [0 for _ in range(self._config.db_num_islands)]
        self._batch_per_island = max(
            1,
            min(
                self._config.num_samplers * 2,
                self._config.max_samples or self._config.num_samplers * 2,
            )
            // max(1, self._config.db_num_islands),
        )

        # Debug mode: print all errors during search (can be set after instantiation)
        # When True, errors are logged at ERROR level instead of WARNING
        self.debug_mode = False
        # When True and debug_mode is True, exit immediately on error
        self.debug_mode_crash = False

    def _save_database(self, sample_num: int):
        """Saves the current state of the database using the logger."""
        if not self._logger:
            return

        # Database snapshots are logged separately from per-algorithm entries so
        # island state can be reconstructed after the run.
        database_dict = self._database.to_dict()
        database_dict["sample_num"] = sample_num
        self._logger.log_dict(database_dict, "database")
        logging.info(f"Saved database snapshot for sample #{sample_num} to logger.")

    @override
    def initialize(self):
        """Initializes the search process by evaluating the template program."""
        # Set log flush frequencies
        db_frequency = getattr(self._config, "db_save_frequency", 1)
        algo_frequency = getattr(self._config, "algo", 2000)
        if self._logger:
            self._logger.set_log_item_flush_frequency(
                {
                    "database": db_frequency,
                    "algo": algo_frequency,
                }
            )

        logging.info("Evaluating template program...")

        template_proto = AlgoProto(
            program=self._template_program_str,
            language=self._config.language,
        )

        # The template program is evaluated once up front so the search always
        # starts from one valid baseline in the database.
        with Timer(template_proto, "eval_time"):
            results = self._evaluator.evaluate_program(template_proto.program)

        if results is None:
            raise RuntimeError("The template program failed evaluation.")

        # handle results dict or object
        if isinstance(results, dict):
            if "execution_time" in results:
                template_proto["execution_time"] = results["execution_time"]
            if "error_msg" in results:
                template_proto["error_msg"] = results["error_msg"]
            template_proto["metrics"] = results
            template_proto["evaluator_score"] = results.get("score")
            template_proto["fitness_score"] = get_fitness_score(
                results, self._config.feature_dimensions
            )
            template_proto.score = results.get("score")
        else:
            template_proto.score = results
            template_proto["metrics"] = {"score": results}
            template_proto["fitness_score"] = results

        if not self._database.is_searchable_program(template_proto):
            raise RuntimeError(
                "The template program did not produce a valid score."
            )

        # Register the template before logging so the logger can include island
        # state derived from the database snapshot.
        self._database.register_program(template_proto)

        with self._lock:
            self._samples_count += 1
            # Keep the template out of island accounting in terminal/log output.
            template_proto["island_id"] = -1
            self._log(template_proto, is_template=True)

    def run(self):
        """Starts the search process."""
        try:
            self.initialize()

            logging.info(f"Starting {self._config.num_samplers} sampler threads...")

            # Start sampler threads
            threads = []
            for _ in range(self._config.num_samplers):
                t = threading.Thread(target=self._sample_evaluate_register_loop)
                t.start()
                threads.append(t)

            # Wait for all sampler threads to complete
            for t in threads:
                t.join()

        except (KeyboardInterrupt, SystemExit):
            logging.info("Search interrupted by user.")
            self._stop_event.set()
        except Exception as e:
            error_msg = traceback.format_exc()
            logging.error("An unexpected error occurred during the search process.")
            if self.debug_mode:
                logging.error(format_error_box(error_msg))
                if self.debug_mode_crash:
                    logging.error("Debug mode crash: exiting immediately.")
                    import sys

                    sys.exit(1)
            self._stop_event.set()
        finally:
            self._executor.shutdown(wait=True)
            with self._lock:
                self._save_database(self._samples_count)
            if self._logger:
                logging.info("Finalizing logger...")
                self._logger.finish()
            logging.info("Search finished.")

    @override
    def is_stopped(self) -> bool:
        """Checks if the search should be stopped based on the max samples or stop event."""
        return self._stop_event.is_set() or (
            self._config.max_samples is not None
            and self._samples_count >= self._config.max_samples
        )

    @override
    def current_num_samples(self) -> int:
        with self._lock:
            return self._samples_count

    @override
    def get_config(self) -> OpenEvolveConfig:
        return self._config

    def _sample_evaluate_register_loop(self):
        """
        Run the full candidate lifecycle inside one sampler thread.

        Each loop reserves a target island, builds prompt context, samples one or
        more completions, evaluates the resulting code, and registers successful
        candidates back into the database.
        """
        while not self.is_stopped():
            with self._lock:
                if self.is_stopped():
                    self._stop_event.set()
                    break

            candidate = None
            try:
                # Select parents, create prompt and return a NEW AlgoProto
                candidate = self.select_and_create_prompt()
                if not candidate:
                    time.sleep(1)
                    continue

                for _ in range(self._config.samples_per_prompt):
                    if self.is_stopped():
                        break
                    _candidate = copy.deepcopy(candidate)
                    # Each completion attempt starts from the same prompt context
                    # so one parent selection can yield multiple sibling trials.
                    # Generate raw response (updates candidate in-place)
                    _candidate = self.generate(_candidate)
                    # Extract algo from response (updates candidate in-place)
                    _candidate = self.extract_algo_from_response(_candidate)

                    parent_code = (
                        _candidate.get("parents")[0].program
                        if _candidate.get("parents")
                        else ""
                    )
                    # Skip evaluation if the code couldn't be parsed or didn't change
                    if not _candidate.program or _candidate.program == parent_code:
                        logging.debug(
                            f"Sampler skipped evaluation: Code identical to parent or invalid diff."
                        )
                        continue

                    # Evaluate (updates candidate in-place)
                    _candidate = self.evaluate(_candidate)
                    # Registration handles bookkeeping, migration checks, and logging.
                    self.register(_candidate)
                self._release_sampling_island(candidate.get("target_island"))

            except (KeyboardInterrupt, SystemExit):
                if candidate:
                    self._release_sampling_island(candidate.get("target_island"))
                self._stop_event.set()
                break
            except Exception as e:
                if candidate:
                    self._release_sampling_island(candidate.get("target_island"))
                logging.warning(
                    f"Exception in sampler thread: {traceback.format_exc()}"
                )
                if self.debug_mode:
                    logging.error(f"Debug mode: error in sampler thread: {e}")
                    logging.error(format_error_box(traceback.format_exc()))
                    if self.debug_mode_crash:
                        logging.error("Debug mode crash: exiting immediately.")
                        self._stop_event.set()
                        import sys

                        sys.exit(1)
                time.sleep(5)

    def _reserve_sampling_island(self) -> int:
        """Reserve the least-loaded island for the next sampling task."""
        with self._lock:
            # Keep outstanding work spread across islands so one hot island does
            # not consume all sampler capacity.
            eligible_islands = [
                island_id
                for island_id, pending in enumerate(self._island_pending)
                if pending < self._batch_per_island
            ]
            candidate_islands = eligible_islands or list(
                range(len(self._island_pending))
            )
            island_id = min(
                candidate_islands, key=lambda idx: (self._island_pending[idx], idx)
            )
            self._island_pending[island_id] += 1
            return island_id

    def _release_sampling_island(self, island_id: Optional[int]) -> None:
        """Release a previously reserved island after sampling work finishes."""
        if island_id is None or island_id < 0:
            return
        with self._lock:
            if (
                island_id < len(self._island_pending)
                and self._island_pending[island_id] > 0
            ):
                self._island_pending[island_id] -= 1

    def _collapse_candidate_parents(self, candidate: AlgoProto) -> None:
        """Replace transient parent objects with compact scalar metadata."""
        parents = candidate.get("parents") or []
        if not parents:
            return

        parent = parents[0]
        parent_id = parent.get("algo_id") if isinstance(parent, AlgoProto) else None
        parent_island_id = (
            parent.get("island_id") if isinstance(parent, AlgoProto) else None
        )
        parent_metrics = (
            copy.deepcopy(parent.get("metrics", {}) or {})
            if isinstance(parent, AlgoProto)
            else {}
        )

        if parent_id is not None:
            candidate["parent_id"] = parent_id
        if parent_island_id is not None:
            candidate["parent_island_id"] = parent_island_id
        if parent_metrics and not candidate.get("parent_metrics"):
            candidate["parent_metrics"] = parent_metrics

        candidate.pop("parents", None)

    @override
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Selects parents from the database and returns a NEW AlgoProto.

        The returned AlgoProto acts as a 'candidate' container for the entire lifecycle.
        It starts with 'parents', 'island_id', and 'prompt' populated in its attributes.

        AlgoProto keys set:
            - parents: list of selected parent AlgoProto objects
            - island_id: int, the target island for this candidate
            - target_island: int, the island reserved for sampling
            - context_island: int, the island used for prompt context
            - parent_metrics: dict, metrics from the parent program
            - prompt: str, the constructed prompt for generation
        """
        target_island = self._reserve_sampling_island()
        parent, inspirations, target_island = self._database.sample_from_island(
            target_island,
            self._config.num_diverse_programs,
        )

        if not parent:
            self._release_sampling_island(target_island)
            return None

        # Keep the destination island for registration, but build prompt context
        # from the sampled parent's island if parent selection had to fall back
        # to the global population.
        context_island = parent.get("island_id", target_island)
        previous_programs = self._database.get_top_programs(
            3,
            island_id=context_island,
        )
        top_programs = self._database.get_top_programs(
            self._config.num_top_programs + self._config.num_diverse_programs,
            island_id=context_island,
        )

        # 3. Create a NEW AlgoProto for this candidate
        candidate = AlgoProto(language=self._config.language)
        candidate["parents"] = [parent]
        candidate["island_id"] = target_island
        candidate["target_island"] = target_island
        candidate["context_island"] = context_island
        candidate["parent_metrics"] = parent.get("metrics", {})

        # Reuse island-local top programs as the "previous attempts" context so
        # prompts emphasize nearby search history rather than distant lineage.
        prompt_dict = self._prompt_constructor.construct_prompt(
            parent=parent,
            top_programs=top_programs,
            inspirations=inspirations,
            previous_programs=previous_programs,
        )

        # Store as string for the LLM chat_completion interface
        candidate["prompt"] = f"{prompt_dict['system']}\n\n{prompt_dict['user']}"
        return candidate

    @override
    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """Parses 'response_text' and updates 'candidate.program' in-place.

        Uses the parent in 'candidate.parents' as the baseline code for diff application.

        AlgoProto keys set:
            - program: str, the extracted algorithm code
            - changes_summary: str, summary of changes made (if available)
        """
        response_text = candidate.get("response_text", "")
        parents = candidate.get("parents")
        parent_code = parents[0].program if parents else ""

        # Use the improved parser from PromptConstructor
        idea_text = self._prompt_constructor.extract_idea(response_text)
        if idea_text:
            candidate["idea"] = idea_text

        new_code_str = self._prompt_constructor.extract_code(
            response_text, original_code=parent_code
        )

        if new_code_str:
            candidate.program = new_code_str
            candidate["changes_summary"] = self._prompt_constructor.summarize_changes(
                response_text
            )
        return candidate

    @override
    def generate(self, candidate: AlgoProto) -> AlgoProto:
        """Calls the LLM using candidate['prompt'] and stores 'response_text' in the candidate.

        Also records 'sample_time' into the candidate's attributes via the Timer.

        AlgoProto keys set:
            - response_text: str, the raw LLM response
            - sample_time: float, time taken for LLM call (via Timer)
        """
        assert (
            self._llm is not None
        ), "LLM is required for generate(). Use tool_mode=False or provide an LLM."
        with Timer(candidate, "sample_time"):
            response_text = self._llm.chat_completion(
                candidate["prompt"],
                self._config.llm_max_tokens,
                self._config.llm_timeout_seconds,
            )
        candidate["response_text"] = response_text
        return candidate

    @override
    def evaluate(self, candidate: AlgoProto) -> AlgoProto:
        """Evaluates 'candidate.program' and updates 'candidate.score' in-place.

        Also records 'eval_time' and 'metrics' in the candidate's attributes.

        AlgoProto keys set:
            - execution_time: float, time taken to execute the program
            - error_msg: str, error message if evaluation failed
            - metrics: dict, full evaluation results
            - evaluator_score: float, raw score from evaluator
            - fitness_score: float, fitness mirrored from evaluator ``score``
            - score: float, the evaluated score
            - eval_time: float, total evaluation time (via Timer)
            - parent_metrics: dict, metrics from the parent (reassigned after collapse)
        """
        if not candidate or not candidate.program:
            return candidate

        with Timer(candidate, "eval_time"):
            with self._evaluator_semaphore:
                # The evaluator is the only step that may need explicit
                # concurrency throttling because it can be far more expensive
                # than prompt generation or database insertion.
                results = self._evaluator.evaluate_program(candidate.program)

        if results is not None:
            # Always record execution_time and error_msg if available
            if isinstance(results, dict):
                if "execution_time" in results:
                    candidate["execution_time"] = results["execution_time"]
                if "error_msg" in results:
                    candidate["error_msg"] = results["error_msg"]
                candidate["metrics"] = results
                candidate["parent_metrics"] = (
                    candidate.get("parents")[0].get("metrics", {})
                    if candidate.get("parents")
                    else {}
                )
                candidate["evaluator_score"] = results.get("score")
                candidate["fitness_score"] = get_fitness_score(
                    results, self._config.feature_dimensions
                )
                # Preserve both names even though OpenEvolve currently treats
                # fitness as the evaluator score.
                candidate.score = results.get("score")
            else:
                candidate.score = results
                candidate["metrics"] = {"score": results}
                candidate["fitness_score"] = results

        # Parent code is only needed until extraction/evaluation is complete.
        # After that, keep compact provenance fields instead of recursive objects.
        self._collapse_candidate_parents(candidate)
        return candidate

    def _log(self, algo_proto: AlgoProto, is_template: bool = False):
        """Internal logging helper. Assumes self._lock is held by the caller."""
        current_sample_num = self._samples_count
        island_id = algo_proto.get("island_id", -1)

        # Save database
        if (
            self._config.db_save_frequency is not None
            and current_sample_num % self._config.db_save_frequency == 0
        ):
            self._save_database(current_sample_num)

        # Log to terminal
        tag = " (Template)" if is_template else ""
        algo_id_str = f"#{current_sample_num}{tag}"

        score_val = algo_proto.get("evaluator_score", algo_proto.score)
        score_str = f"{score_val:10.4f}" if score_val is not None else f"{'None':>10}"
        fitness_val = algo_proto.get("fitness_score", None)
        fitness_str = (
            f"{fitness_val:10.4f}"
            if isinstance(fitness_val, (int, float))
            else f"{'None':>10}"
        )

        sample_time_val = algo_proto.get("sample_time", 0.0)
        sample_time_str = (
            f"{sample_time_val:6.2f}s" if not is_template else f"{'N/A':>7}"
        )

        eval_time_val = algo_proto.get("eval_time", 0.0)
        execution_time_val = algo_proto.get("execution_time", None)
        time_info = format_time_info(eval_time_val, execution_time_val)

        logging.info(
            f"Algo {algo_id_str:<16} | "
            f"Score: {score_str} | "
            f"Fitness: {fitness_str} | "
            f"Sample: {sample_time_str} | "
            f"{time_info}"
        )

        # Register to the logger no matter if it is feasible.
        if self._logger:
            # Log a trimmed copy so the database entry keeps its full metadata.
            algo_proto_for_log = copy.deepcopy(algo_proto)
            algo_proto_for_log.keep_metadata_keys(self._config.keep_metadata_keys)
            log_entry = algo_proto_for_log.to_dict()
            log_entry.update(
                {
                    "sample_num": current_sample_num,
                    "island_id": island_id,
                    "sample_time": 0.0 if is_template else sample_time_val,
                }
            )

            # Add island stats if available
            if hasattr(self._database, "get_island_stats"):
                island_stats = self._database.get_island_stats()
                if island_stats:
                    for i_id, size in island_stats.items():
                        log_entry[f"island_size_{i_id}"] = size

            self._logger.log_dict(log_entry, "algo")

    @override
    def register(self, algo_proto: AlgoProto):
        """
        Register a finished candidate and trigger island maintenance immediately.

        This is where sample counting, database insertion, generation tracking,
        migration checks, terminal logging, and logger persistence are tied
        together.
        """
        if not algo_proto or not algo_proto.program:
            return

        island_id = algo_proto.get("target_island", algo_proto.get("island_id", -1))

        with self._lock:
            if (
                self._config.max_samples is not None
                and self._samples_count >= self._config.max_samples
            ):
                return

            self._samples_count += 1

            if self._database.is_searchable_program(algo_proto):
                self._database.register_program(algo_proto, island_id=island_id)
                if island_id >= 0:
                    self._database.increment_island_generation(island_id)
                    # Check migration immediately after registration so island
                    # state changes are applied synchronously with sample intake.
                    if self._database.should_migrate():
                        logging.info(
                            "Triggering migration at sample %s from island %s registration...",
                            self._samples_count,
                            island_id,
                        )
                        self._database.migrate()

            # Print, save to algo using logger, save database using logger.
            self._log(algo_proto)
