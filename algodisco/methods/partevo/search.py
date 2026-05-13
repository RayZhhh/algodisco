# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from __future__ import annotations

import copy
import logging
import math
import threading
import time
import traceback
from typing import Optional

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

from algodisco.methods.partevo.config import PartEvoConfig
from algodisco.methods.partevo.database import PartEvoDatabase
from algodisco.methods.partevo.prompt import PartEvoPromptAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PartEvoSearch(IterativeSearchBase):
    """Niching-enhanced evolutionary search adapted to AlgoDisco.

    This implementation keeps the high-level behavior of the original PartEvo
    paper and upstream code:

    1. initialize a diverse population;
    2. partition the population into niches;
    3. alternate among reflection, summary-guided, cross-niche, and
       local-global operators;
    4. maintain a global archive summary to steer semantic exploration.

    The overall lifecycle matches EoH in this repository: ``initialize()``
    performs template baseline evaluation and logger setup, while the actual
    population initialization happens inside the iterative sampling loop.
    """

    _EXCLUDED_LOG_KEYS = frozenset(
        {
            "accepted_by_population",
            "accepted_by_tree",
            "assigned_cluster_id",
        }
    )

    def __init__(
        self,
        config: PartEvoConfig,
        evaluator: Evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PartEvoPromptAdapter = PartEvoPromptAdapter(),
        *,
        tool_mode: bool = False,
    ):
        """Initialize the PartEvo search object."""
        assert llm or tool_mode

        self._config = config
        self._template_program_str = str(self._config.template_program)
        if not self._template_program_str:
            raise ValueError("The provided template program is empty.")

        self._llm = llm
        self._evaluator = evaluator
        self._logger = logger
        self._prompt_constructor = prompt_constructor
        self._database = PartEvoDatabase(
            pop_size=self._config.pop_size,
            num_clusters=self._config.num_clusters,
            operator_weights={
                "re": self._config.re_operator_weight,
                "se": self._config.se_operator_weight,
                "cn": self._config.cn_operator_weight,
                "lge": self._config.lge_operator_weight,
            },
            use_resource_tilt=self._config.use_resource_tilt,
            resource_tilt_alpha=self._config.resource_tilt_alpha,
            cluster_refresh_interval=self._config.cluster_refresh_interval,
            archive_elite_size=self._config.archive_elite_size,
            archive_hard_negative_size=self._config.archive_hard_negative_size,
            summary_update_interval=self._config.summary_update_interval,
        )

        # `_lock` protects high-level search state transitions such as phase
        # changes, sample counting, and registration. Expensive LLM/evaluator
        # calls are intentionally performed outside this lock.
        self._lock = threading.RLock()
        # Archive summary refresh is a separate side-channel LLM call; this lock
        # prevents many sampler threads from regenerating the same summary.
        self._summary_refresh_lock = threading.Lock()
        # Reflection is also an auxiliary LLM call. Cache critiques per parent
        # program so repeated `re` steps on the same elite do not pay for the
        # same extra round-trip over and over.
        self._reflection_cache_lock = threading.Lock()
        self._reflection_cache: dict[str, str] = {}
        # Evaluator concurrency is capped independently from sampler threads so
        # we can keep prompt construction parallel without overloading runtime.
        self._evaluator_semaphore = threading.Semaphore(self._config.num_evaluators)
        self._stop_event = threading.Event()
        self._samples_count = 0
        self._last_db_saved_at: int = -1
        self._init_trials = 0
        self._max_init_trials = (
            self._config.init_trial_multiplier * self._config.init_pop_size
        )
        self._phase = "init"

        # Debug flags follow the conventions of the other search methods.
        self.debug_mode = False
        self.debug_mode_crash = False

    def _has_valid_score(self, score) -> bool:
        """Return whether a score is finite and therefore searchable."""
        if score is None:
            return False
        try:
            return math.isfinite(score)
        except (TypeError, ValueError):
            return False

    def _sanitize_log_value(self, value):
        """Drop method-local runtime fields that should not enter logger outputs."""
        if isinstance(value, dict):
            return {
                key: self._sanitize_log_value(item)
                for key, item in value.items()
                if key not in self._EXCLUDED_LOG_KEYS
            }
        if isinstance(value, list):
            return [self._sanitize_log_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._sanitize_log_value(item) for item in value)
        return value

    def _serialize_algo_for_logging(self, algo_proto: AlgoProto) -> dict:
        """Serialize one candidate using the method's metadata allowlist."""
        log_algo_proto = copy.deepcopy(algo_proto)
        log_algo_proto.keep_metadata_keys(self._config.keep_metadata_keys)
        return self._sanitize_log_value(log_algo_proto.to_dict())

    def _save_database(self, sample_num: int) -> None:
        """Persist the current database snapshot using the configured logger."""
        if not self._logger:
            return

        database_dict = self._sanitize_log_value(self._database.to_dict())
        database_dict["sample_num"] = sample_num
        database_dict["phase"] = self._phase
        self._logger.log_dict(database_dict, "database")
        self._last_db_saved_at = sample_num
        logging.info("Saved database snapshot for sample #%s to logger.", sample_num)

    @override
    def initialize(self) -> None:
        """Evaluate and log the template program as a baseline.

        Like EoH, initialization here only prepares the baseline/template
        record. The searchable population is still created later by ``init``
        prompts in the iterative loop.
        """
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

        with Timer(template_proto, "eval_time"):
            results = self._evaluator.evaluate_program(template_proto.program)

        if results is not None:
            if "execution_time" in results:
                template_proto["execution_time"] = results["execution_time"]
            if "error_msg" in results:
                template_proto["error_msg"] = results["error_msg"]
            if results.get("score") is not None:
                template_proto.score = results["score"]

        with self._lock:
            self._samples_count += 1
            self._log(template_proto, is_template=True)

    def run(self) -> None:
        """Run the full PartEvo search loop until termination."""
        try:
            self.initialize()
            logging.info(
                "Starting %s PartEvo sampler threads...",
                self._config.num_samplers,
            )

            threads = []
            for _ in range(self._config.num_samplers):
                thread = threading.Thread(target=self._generate_evaluate_register_loop)
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
        """Return whether the search has reached a stop condition."""
        return self._stop_event.is_set() or (
            self._config.max_samples is not None
            and self._samples_count >= self._config.max_samples
        )

    @override
    def current_num_samples(self) -> int:
        """Return the number of evaluated samples seen so far."""
        with self._lock:
            return self._samples_count

    @override
    def get_config(self) -> PartEvoConfig:
        """Return the active method configuration."""
        return self._config

    def _build_candidate(
        self,
        *,
        operator: str,
        prompt: str,
        phase: str,
        cluster_id: Optional[int] = None,
    ) -> AlgoProto:
        """Create the mutable candidate container for one lifecycle."""
        candidate = AlgoProto(language=self._config.language)
        candidate["operator"] = operator
        candidate["prompt"] = prompt
        candidate["phase"] = phase
        if cluster_id is not None:
            candidate["cluster_id"] = cluster_id
        return candidate

    def _try_enter_clustered_phase(self) -> None:
        """Enter the clustered phase once initialization has enough accepted samples."""
        if self._database.is_clustered:
            self._phase = "search"
            return

        # The normal path is: collect enough accepted algorithms, then cluster
        # them once and switch the whole search into niche-aware mode.
        if self._database.can_cluster(min_population=self._config.init_pop_size):
            if self._database.recluster():
                self._phase = "search"
                logging.info(
                    "PartEvo initialization completed with %s accepted candidates. "
                    "Entered clustered search with %s clusters.",
                    len(self._database),
                    self._config.num_clusters,
                )
                return

        # If initialization keeps failing to yield enough feasible candidates, we do
        # not want to loop forever. We either cluster the smaller current pool
        # or stop cleanly if even that is impossible.
        if self._init_trials >= self._max_init_trials:
            if self._database.can_cluster(min_population=self._config.num_clusters):
                if self._database.recluster():
                    self._phase = "search"
                    logging.info(
                        "Initialization hit its attempt cap; clustered search starts "
                        "with the currently accepted population (%s candidates).",
                        len(self._database),
                    )
                    return

            logging.warning(
                "Initialization ended after %s attempts without enough feasible "
                "candidates to cluster. Search will stop.",
                self._init_trials,
            )
            self._phase = "finished"
            self._stop_event.set()

    def _call_aux_llm(self, prompt: str) -> tuple[str, float]:
        """Execute one auxiliary LLM call used for reflection or summary."""
        assert self._llm is not None
        start_time = time.time()
        response = self._llm.chat_completion(
            prompt,
            self._config.llm_max_tokens,
            self._config.llm_timeout_seconds,
        )
        return response, time.time() - start_time

    def _build_init_candidate(self) -> AlgoProto:
        """Create an initialization prompt that seeks diversity against current elites."""
        # Initialization does not use niche operators yet. It simply asks for a
        # strong candidate that differs from the currently accepted population.
        prompt = self._prompt_constructor.construct_prompt_init(
            self._config.task_description,
            self._database.population,
            self._template_program_str,
            self._config.language,
        )
        return self._build_candidate(
            operator="init",
            prompt=prompt,
            phase="init",
        )

    def _refresh_archive_summary_if_needed(self) -> tuple[str, float]:
        """Refresh the cached archive summary at most once concurrently."""
        cached_summary, needs_refresh, context_samples = (
            self._database.archive.fetch_summary_context()
        )
        if not needs_refresh or not context_samples:
            return cached_summary, 0.0

        with self._summary_refresh_lock:
            # Another thread may have refreshed the summary while we were
            # waiting, so re-check after acquiring the lock.
            cached_summary, needs_refresh, context_samples = (
                self._database.archive.fetch_summary_context()
            )
            if not needs_refresh or not context_samples:
                return cached_summary, 0.0

            summary_prompt = self._prompt_constructor.construct_prompt_summary(
                self._config.task_description,
                context_samples,
                current_summary=cached_summary,
            )
            summary_response, aux_llm_time = self._call_aux_llm(summary_prompt)
            parsed_summary = self._prompt_constructor.extract_summary(summary_response)
            if parsed_summary:
                self._database.archive.update_summary(parsed_summary)
                return parsed_summary, aux_llm_time
            return cached_summary, aux_llm_time

    def _build_search_candidate_from_context(self, context) -> Optional[AlgoProto]:
        """Create the next clustered-search candidate prompt."""

        operator = context.operator
        parents = context.parents
        cluster_id = context.cluster_id

        if operator == "re":
            # `re` is a two-step operator:
            # 1. ask for a targeted critique of the current algorithm;
            # 2. feed that critique into the actual generation prompt.
            parent_program = str(parents[0].program)
            aux_llm_time = 0.0

            with self._reflection_cache_lock:
                reflection_text = self._reflection_cache.get(parent_program, "")

            if not reflection_text:
                reflection_prompt = self._prompt_constructor.construct_prompt_reflection(
                    self._config.task_description,
                    parents[0],
                    self._template_program_str,
                    self._config.language,
                )
                reflection_response, aux_llm_time = self._call_aux_llm(
                    reflection_prompt
                )
                reflection_text = (
                    self._prompt_constructor.extract_reflection(reflection_response)
                    or ""
                )
                if reflection_text:
                    with self._reflection_cache_lock:
                        self._reflection_cache[parent_program] = reflection_text

            candidate = self._build_candidate(
                operator=operator,
                prompt=self._prompt_constructor.construct_prompt_re(
                    self._config.task_description,
                    parents[0],
                    reflection_text,
                    self._template_program_str,
                    self._config.language,
                ),
                phase="search",
                cluster_id=cluster_id,
            )
            candidate["reflection_guidance"] = reflection_text
            candidate["aux_llm_time"] = aux_llm_time
            candidate["parents"] = parents
            return candidate

        if operator == "se":
            summary_text, aux_llm_time = self._refresh_archive_summary_if_needed()
            candidate = self._build_candidate(
                operator=operator,
                prompt=self._prompt_constructor.construct_prompt_se(
                    self._config.task_description,
                    parents[0],
                    summary_text,
                    self._template_program_str,
                    self._config.language,
                ),
                phase="search",
                cluster_id=cluster_id,
            )
            candidate["archive_summary"] = summary_text
            candidate["aux_llm_time"] = aux_llm_time
            candidate["parents"] = parents
            return candidate

        if operator == "cn":
            candidate = self._build_candidate(
                operator=operator,
                prompt=self._prompt_constructor.construct_prompt_cn(
                    self._config.task_description,
                    parents,
                    self._template_program_str,
                    self._config.language,
                ),
                phase="search",
                cluster_id=cluster_id,
            )
            candidate["parents"] = parents
            return candidate

        if operator == "lge":
            candidate = self._build_candidate(
                operator=operator,
                prompt=self._prompt_constructor.construct_prompt_lge(
                    self._config.task_description,
                    parents,
                    self._template_program_str,
                    self._config.language,
                ),
                phase="search",
                cluster_id=cluster_id,
            )
            candidate["parents"] = parents
            return candidate

        return None

    @override
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Select the next operator context and construct a candidate prompt."""
        with self._lock:
            if self.is_stopped():
                return None

            self._try_enter_clustered_phase()
            phase = self._phase

        if phase == "finished":
            return None

        if phase == "init":
            return self._build_init_candidate()

        if phase == "search":
            # Parent/operator selection is synchronized inside the database so
            # each thread sees a coherent clustered population snapshot.
            context = self._database.select_search_context()
            if context is None:
                return None
            return self._build_search_candidate_from_context(context)

        return None

    def _generate_evaluate_register_loop(self) -> None:
        """Main lifecycle loop for a single PartEvo sampler thread."""
        while not self.is_stopped():
            with self._lock:
                if self.is_stopped():
                    self._stop_event.set()
                    break

            try:
                # Each thread performs a full candidate lifecycle. The shared
                # state interaction happens during selection and registration;
                # generation and evaluation run concurrently across threads.
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
                    "Exception in PartEvo sampler thread: %s",
                    traceback.format_exc(),
                )
                if self.debug_mode:
                    logging.error(
                        "Debug mode: error in PartEvo sampler thread: %s",
                        exc,
                    )
                    logging.error(format_error_box(traceback.format_exc()))
                    if self.debug_mode_crash:
                        self._stop_event.set()
                        raise
                time.sleep(0.2)

    @override
    def generate(self, candidate: AlgoProto) -> AlgoProto:
        """Call the LLM and attach the raw response to the candidate."""
        assert (
            self._llm is not None
        ), "LLM is required for generate(). Use tool_mode=False or provide an LLM."
        aux_llm_time = float(candidate.get("aux_llm_time", 0.0) or 0.0)
        with Timer(candidate, "sample_time"):
            response_text = self._llm.chat_completion(
                candidate["prompt"],
                self._config.llm_max_tokens,
                self._config.llm_timeout_seconds,
            )
        candidate["response_text"] = response_text
        if aux_llm_time > 0.0:
            candidate["sample_time"] = candidate.get("sample_time", 0.0) + aux_llm_time
        return candidate

    @override
    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """Parse the model response into idea text and program code."""
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
        """Evaluate the candidate program and attach useful evaluator metrics."""
        if not candidate or not candidate.program:
            return candidate

        with Timer(candidate, "eval_time"):
            with self._evaluator_semaphore:
                results = self._evaluator.evaluate_program(candidate.program)

        if results is not None:
            if "execution_time" in results:
                candidate["execution_time"] = results["execution_time"]
            if "error_msg" in results:
                candidate["error_msg"] = results["error_msg"]
            if results.get("score") is not None:
                candidate.score = results["score"]
        return candidate

    @override
    def register(self, algo_proto: AlgoProto) -> None:
        """Register one evaluated candidate into logs, population, and clusters."""
        if algo_proto is None:
            return

        with self._lock:
            if self.is_stopped():
                return

            self._samples_count += 1

            if algo_proto.get("phase") == "init":
                self._init_trials += 1

            if algo_proto.program and self._has_valid_score(algo_proto.score):
                # All acceptance logic flows through the database so global
                # population control, archive maintenance, and cluster routing
                # stay in one place.
                registered_algo_proto = copy.deepcopy(algo_proto)
                registered_algo_proto.keep_metadata_keys(
                    self._config.keep_metadata_keys
                )
                self._database.register_algo(
                    registered_algo_proto,
                    source_cluster_id=algo_proto.get("cluster_id"),
                )

            self._try_enter_clustered_phase()
            self._log(algo_proto)

    def _log(
        self,
        algo_proto: AlgoProto,
        *,
        is_template: bool = False,
    ) -> None:
        """Write terminal output and structured logger entries for one sample."""
        current_sample_num = self._samples_count
        operator = algo_proto.get("operator", "template")
        phase = algo_proto.get("phase", self._phase)

        if (
            self._config.db_save_frequency is not None
            and current_sample_num % self._config.db_save_frequency == 0
        ):
            # Database snapshots are aligned to the global sample counter so
            # logs remain consistent even when many sampler threads are active.
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

        cluster_str = "-"
        if algo_proto.get("cluster_id") is not None:
            cluster_str = str(algo_proto.get("cluster_id"))

        status_parts = [
            f"Algo {algo_id_str:<24}",
            f"Score: {score_str}",
            f"Sample: {sample_time_str}",
            time_info,
        ]
        status_parts.extend(
            [
                f"Cluster: {cluster_str}",
                f"Phase: {self._phase}",
            ]
        )
        logging.info(
            " | ".join(status_parts)
        )

        if self._logger:
            log_entry = self._serialize_algo_for_logging(algo_proto)
            log_entry.update(
                {
                    "sample_num": current_sample_num,
                    "operator": operator,
                    "phase": phase,
                    "sample_time": 0.0 if is_template else sample_time_val,
                    "pop_size": len(self._database),
                    "best_score": self._database.get_best_score(),
                    "is_clustered": self._database.is_clustered,
                }
            )
            self._logger.log_dict(log_entry, "algo")

