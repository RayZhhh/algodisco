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
from algodisco.base.evaluator import Evaluator
from algodisco.base.algo import AlgoProto
from algodisco.base.search_method import IterativeSearchBase
from algodisco.base.logger import AlgoSearchLoggerBase
from algodisco.common.timer import Timer
from algodisco.common.logging_utils import format_time_info, format_error_box

from algodisco.methods.openevolve.config import OpenEvolveConfig
from algodisco.methods.openevolve.database import ProgramDatabase
from algodisco.methods.openevolve.prompt import PromptConstructor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class OpenEvolve(IterativeSearchBase):
    """Core class for the OpenEvolve process, using threading."""

    def __init__(
        self,
        config: OpenEvolveConfig,
        evaluator,
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
        self._evaluator = evaluator
        self._database = ProgramDatabase(config)
        self._logger = logger

        self._prompt_constructor = prompt_constructor or PromptConstructor(
            config=self._config
        )

        self._lock = threading.Lock()
        self._samples_count = 0
        self._evaluator_semaphore = threading.Semaphore(self._config.num_evaluators)
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=self._config.num_samplers)

        # Debug mode: print all errors during search (can be set after instantiation)
        # When True, errors are logged at ERROR level instead of WARNING
        self.debug_mode = False
        # When True and debug_mode is True, exit immediately on error
        self.debug_mode_crash = False

    def _save_database(self, sample_num: int):
        """Saves the current state of the database using the logger."""
        if not self._logger:
            return

        database_dict = self._database.to_dict()
        database_dict["sample_num"] = sample_num
        self._logger.log_dict_sync(database_dict, "database")
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

        with Timer(template_proto, "eval_time"):
            results = self._evaluator.evaluate_program(template_proto.program)

        if results is None:
            raise RuntimeError("The template program failed evaluation.")

        # handle results dict or object
        if isinstance(results, dict):
            template_proto.score = results.get("score")
            template_proto["metrics"] = results
        else:
            template_proto.score = results
            template_proto["metrics"] = {"score": results}

        self._database.register_program(template_proto)

        with self._lock:
            self._samples_count += 1
            template_proto["island_id"] = -1
            self._log(template_proto, is_template=True)

    def run(self):
        """Starts the search process."""
        try:
            self.initialize()

            logging.info(f"Starting {self._config.num_samplers} sampler threads...")

            # Start migration thread
            migration_thread = threading.Thread(target=self._migration_loop)
            migration_thread.daemon = True
            migration_thread.start()

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
                self._logger.finish_sync()
            logging.info("Search finished.")

    def _migration_loop(self):
        """Periodically triggers migration in the database based on sample count."""
        last_migration_at = 0
        while not self.is_stopped():
            current_samples = self._samples_count
            if current_samples - last_migration_at >= self._config.migration_interval:
                if current_samples > 0:
                    logging.info(
                        f"Triggering migration at {current_samples} samples..."
                    )
                    self._database.migrate()
                    last_migration_at = current_samples

            time.sleep(5)  # Check every 5 seconds

    @override
    def is_stopped(self) -> bool:
        """Checks if the search should be stopped based on the max samples or stop event."""
        return self._stop_event.is_set() or (
            self._config.max_samples is not None
            and self._samples_count >= self._config.max_samples
        )

    def _sample_evaluate_register_loop(self):
        """The main loop for a single sampler thread."""
        while not self.is_stopped():
            with self._lock:
                if self.is_stopped():
                    self._stop_event.set()
                    break

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
                    # Register
                    self.register(_candidate)

            except (KeyboardInterrupt, SystemExit):
                self._stop_event.set()
                break
            except Exception as e:
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

    @override
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Selects parents from the database and returns a NEW AlgoProto.

        The returned AlgoProto acts as a 'candidate' container for the entire lifecycle.
        It starts with 'parents', 'island_id', and 'prompt' populated in its attributes.
        """
        # 1. Select parent program from an island
        parent_programs, island_id = self._database.select_programs(1)

        if not parent_programs:
            return None

        parent = parent_programs[0]

        # 2. Select context programs (Top Performing and Inspirations/Diverse)
        top_programs = self._database.get_top_programs(self._config.num_top_programs)

        # Select inspirations (simply by selecting more from random islands)
        # In full OpenEvolve, this is more complex, but this maintains the principle.
        inspirations, _ = self._database.select_programs(
            self._config.num_diverse_programs
        )

        # 3. Create a NEW AlgoProto for this candidate
        candidate = AlgoProto(language=self._config.language)
        candidate["parents"] = [parent]
        candidate["island_id"] = island_id

        # 4. Construct Modular Prompt (Restored logic)
        prompt_dict = self._prompt_constructor.construct_prompt(
            parent=parent, top_programs=top_programs, inspirations=inspirations
        )

        # Store as string for the LLM chat_completion interface
        candidate["prompt"] = f"{prompt_dict['system']}\n\n{prompt_dict['user']}"
        return candidate

    @override
    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """Parses 'response_text' and updates 'candidate.program' in-place.

        Uses the parent in 'candidate.parents' as the original code for parser.
        """
        response_text = candidate.get("response_text", "")
        parents = candidate.get("parents")
        parent_code = parents[0].program if parents else ""

        # Use the improved parser from PromptConstructor
        new_code_str = self._prompt_constructor.extract_code(
            response_text, original_code=parent_code
        )

        if new_code_str:
            candidate.program = new_code_str
        return candidate

    @override
    def generate(self, candidate: AlgoProto) -> AlgoProto:
        """Calls the LLM using candidate['prompt'] and stores 'response_text' in the candidate.

        Also records 'sample_time' into the candidate's attributes via the Timer.
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
        """
        if not candidate or not candidate.program:
            return candidate

        with Timer(candidate, "eval_time"):
            with self._evaluator_semaphore:
                results = self._evaluator.evaluate_program(candidate.program)

        if results is not None:
            # Always record execution_time and error_msg if available
            if isinstance(results, dict):
                if "execution_time" in results:
                    candidate["execution_time"] = results["execution_time"]
                if "error_msg" in results:
                    candidate["error_msg"] = results["error_msg"]
                candidate["metrics"] = results
                candidate.score = results.get("score")
            else:
                candidate.score = results
                candidate["metrics"] = {"score": results}

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

        score_val = algo_proto.score
        score_str = f"{score_val:10.4f}" if score_val is not None else f"{'None':>10}"

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
            f"Sample: {sample_time_str} | "
            f"{time_info}"
        )

        # Register to the logger no matter if it is feasible.
        if self._logger:
            # Keep only specified metadata keys for logging
            algo_proto.keep_metadata_keys(self._config.keep_metadata_keys)
            log_entry = algo_proto.to_dict()
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

            self._logger.log_dict_sync(log_entry, "algo")

    @override
    def register(self, algo_proto: AlgoProto):
        """Registers a new AlgoProto in the database and logger."""
        if not algo_proto or not algo_proto.program:
            return

        island_id = algo_proto.get("island_id", -1)

        with self._lock:
            if (
                self._config.max_samples is not None
                and self._samples_count >= self._config.max_samples
            ):
                return

            self._samples_count += 1

            if algo_proto.score is not None:
                self._database.register_program(algo_proto, island_id=island_id)

            # Print, save to algo using logger, save database using logger.
            self._log(algo_proto)
