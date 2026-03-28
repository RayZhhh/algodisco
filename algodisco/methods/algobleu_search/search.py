# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import copy
import logging
import random
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
from algodisco.base.algo import AlgoProto
from algodisco.base.evaluator import Evaluator
from algodisco.base.search_method import IterativeSearchBase
from algodisco.base.logger import AlgoSearchLoggerBase
from algodisco.common.timer import Timer
from algodisco.common.logging_utils import format_time_info, format_error_box

from algodisco.methods.algobleu_search.algo_database import AlgoDatabase
from algodisco.methods.algobleu_search.config import AlgoBLEUSearchConfig
from algodisco.methods.algobleu_search.prompt import PromptAdapter

# Configure basic logging.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class AlgoBLEUSearch(IterativeSearchBase):
    """Core class for the AlgoBLEU search process, using threading."""

    def __init__(
        self,
        config: AlgoBLEUSearchConfig,
        evaluator,
        llm: LanguageModel = None,
        emb_llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptAdapter = PromptAdapter(),
        *,
        tool_mode=False,
    ):
        """
        Initializes the AlgoBLEU Search.

        Args:
            config: Configuration object for the search.
            llm: Language model for code generation.
            emb_llm: Language model for embeddings.
            evaluator: The evaluator to score programs.
            logger: Logger for experiment tracking.
            prompt_constructor: The component for building prompts.
        """
        # --- Tool mode assertion ---
        assert (llm and emb_llm) or tool_mode
        # ---------------------------

        self._config = config
        self._template_program_str = str(self._config.template_program)
        if not self._template_program_str:
            raise ValueError("The provided template program is empty.")

        self._llm = llm
        self._emb_llm = emb_llm
        self._evaluator = evaluator
        self._database = AlgoDatabase(config.database_config)
        self._logger = logger
        self._prompt_constructor = prompt_constructor

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

        # Basic evaluation
        with Timer(template_proto, "eval_time"):
            results = self._evaluator.evaluate_program(template_proto.program)

        if (
            results is None
            or results.get("score") is None
            or results.get("behavior") is None
        ):
            raise RuntimeError("The template program failed evaluation.")

        template_proto.score = results["score"]
        template_proto["behavior"] = results["behavior"]

        logging.info(
            f"Template program evaluated successfully. "
            f"Score: {template_proto.score:.4f}, Time: {template_proto['eval_time']:.2f}s"
        )

        # Extract idea from initial algorithm
        with Timer(template_proto, "idea_time"):
            summary_prompt = self._prompt_constructor.construct_idea_summary_prompt(
                template_proto
            )
            idea = self._llm.chat_completion(
                summary_prompt,
                self._config.llm_max_tokens,
                self._config.llm_timeout_seconds,
            )
            template_proto["idea"] = idea

        # Extract embedding
        with Timer(template_proto, "emb_time"):
            full_idea = f"Idea:\n{template_proto['idea']}"
            embedding = self._emb_llm.embedding(full_idea)
            template_proto["embedding"] = embedding

        # Register
        self._database.register_algo(template_proto)

        with self._lock:
            self._samples_count += 1
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
                t = threading.Thread(target=self._generate_evaluate_register_loop)
                t.start()
                threads.append(t)

            # Wait for all threads to complete
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
                    self._stop_event.set()
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
        """Checks if the search termination criteria are met."""
        return self._stop_event.is_set() or (
            self._config.max_samples is not None
            and self._samples_count >= self._config.max_samples
        )

    @override
    def current_num_samples(self) -> int:
        with self._lock:
            return self._samples_count

    @override
    def get_config(self) -> AlgoBLEUSearchConfig:
        return self._config

    def _generate_evaluate_register_loop(self):
        """The main loop for a single sampler thread."""
        while not self.is_stopped():
            with self._lock:
                if self.is_stopped():
                    self._stop_event.set()
                    break

            try:
                candidate = self.select_and_create_prompt()
                if not candidate:
                    time.sleep(1)
                    continue

                for _ in range(self._config.samples_per_prompt):
                    if self.is_stopped():
                        break
                    _candidate = copy.deepcopy(candidate)
                    _candidate = self.generate(_candidate)
                    _candidate = self.extract_algo_from_response(_candidate)
                    _candidate = self.evaluate(_candidate)
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
                time.sleep(1)

    @override
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Selects parents and creates a prompt container.

        AlgoProto keys set:
            - parents: list of selected parent AlgoProto objects
            - island_id: int, the island from which parents were selected
            - prompt: str, the constructed prompt for generation
        """
        if random.random() < self._config.inter_island_selection_p:
            selection = self._database.select_algos(
                num_islands=self._config.examples_per_prompt, samples_per_island=1
            )
        else:
            selection = self._database.select_algos(
                num_islands=1, samples_per_island=self._config.samples_per_prompt
            )

        if not selection:
            return None

        examples = [item[0] for item in selection]
        island_ids = [item[1] for item in selection]

        sorted_examples = sorted(examples, key=lambda p: p.score, reverse=True)

        candidate = AlgoProto(language=self._config.language)
        candidate["parents"] = sorted_examples
        candidate["island_id"] = island_ids[0] if island_ids else -1

        prompt = self._prompt_constructor.construct_prompt(
            self._config.task_description, sorted_examples
        )
        candidate["prompt"] = prompt
        return candidate

    @override
    def generate(self, candidate: AlgoProto) -> AlgoProto:
        """Generates raw response from LLM.

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
    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """Extracts code from LLM response."""
        response_text = candidate.get("response_text", "")
        new_code_str = self._prompt_constructor.extract_code(
            response_text, language=candidate.language
        )
        if new_code_str:
            candidate.program = new_code_str
        return candidate

    @override
    def evaluate(self, candidate: AlgoProto) -> AlgoProto:
        """Evaluates candidate program, including idea and embedding.

        AlgoProto keys set:
            - execution_time: float, time taken to execute the program
            - error_msg: str, error message if evaluation failed
            - score: float, the evaluated score
            - behavior: object, behavior extracted from evaluation
            - idea: str, idea summary generated by LLM
            - embedding: list, embedding vector of the idea
            - eval_time: float, total evaluation time (via Timer)
            - idea_time: float, time taken for idea generation (via Timer)
            - emb_time: float, time taken for embedding generation (via Timer)
        """
        if not candidate or not candidate.program:
            return candidate

        # 1. Basic evaluation
        with Timer(candidate, "eval_time"):
            with self._evaluator_semaphore:
                results = self._evaluator.evaluate_program(candidate.program)

        if results:
            # Always record execution_time and error_msg if available
            if "execution_time" in results:
                candidate["execution_time"] = results["execution_time"]
            if "error_msg" in results:
                candidate["error_msg"] = results["error_msg"]
            # Record score and behavior if available
            if results.get("score") is not None:
                candidate.score = results["score"]
                candidate["behavior"] = results.get("behavior")
            else:
                candidate.score = None
                candidate["behavior"] = None

            if candidate.get("behavior") is None:
                return candidate

            # 2. Generate idea summary
            with Timer(candidate, "idea_time"):
                summary_prompt = self._prompt_constructor.construct_idea_summary_prompt(
                    candidate
                )
                idea = self._llm.chat_completion(
                    summary_prompt,
                    self._config.llm_max_tokens,
                    self._config.llm_timeout_seconds,
                )
                candidate["idea"] = idea

            # 3. Generate embedding
            with Timer(candidate, "emb_time"):
                full_idea = f"Idea:\n{candidate['idea']}"
                embedding = self._emb_llm.embedding(full_idea)
                candidate["embedding"] = embedding

        return candidate

    @override
    def register(self, algo_proto: AlgoProto):
        """Registers evaluated program in database and logs progress."""
        if not algo_proto or not algo_proto.program:
            return

        with self._lock:
            if self.is_stopped():
                return

            self._samples_count += 1

            if algo_proto.score is not None:
                self._database.register_algo(algo_proto)

            self._log(algo_proto)

    def _log(self, algo_proto: AlgoProto, is_template: bool = False):
        """Internal logging helper."""
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

        if self._logger:
            # Keep only specified metadata keys for logging (use copy to avoid modifying original)
            algo_copy = copy.deepcopy(algo_proto)
            algo_copy.keep_metadata_keys(self._config.keep_metadata_keys)
            log_entry = algo_copy.to_dict()
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
