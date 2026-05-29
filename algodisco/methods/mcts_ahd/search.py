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
from typing import Dict, List, Optional

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

from algodisco.methods.mcts_ahd.config import MCTSAHDConfig
from algodisco.methods.mcts_ahd.database import MCTSAHDDatabase
from algodisco.methods.mcts_ahd.mcts import MCTSNode, MCTSTree
from algodisco.methods.mcts_ahd.prompt import MCTSAHDPromptAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MCTSAHDSearch(IterativeSearchBase):
    """Tree-guided heuristic search adapted to AlgoDisco's method interface.

    Compared with simpler evolutionary methods in this repository, MCTS-AHD
    keeps two pieces of state in parallel:

    - an elite population database used for parent sampling;
    - an explicit MCTS tree used for path-aware traversal and operator routing.

    This adaptation keeps tree mutation, UCT traversal, and logging synchronized
    with locks, while allowing multiple sampler threads to generate and evaluate
    candidates concurrently in the same style as EoH.
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
        config: MCTSAHDConfig,
        evaluator: Evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: MCTSAHDPromptAdapter = MCTSAHDPromptAdapter(),
        *,
        tool_mode: bool = False,
    ):
        """Initialize the MCTS-AHD search object.

        Args:
            config: Search hyper-parameters and prompt/evaluation settings.
            evaluator: Program evaluator used to score candidate algorithms.
            llm: Language model backend used for candidate generation.
            logger: Optional experiment logger.
            prompt_constructor: Prompt adapter used to build and parse prompts.
            tool_mode: Internal escape hatch allowing construction without an
                LLM when only static tooling is needed.
        """
        assert llm or tool_mode

        self._config = config
        self._template_program_str = str(self._config.template_program)
        if not self._template_program_str:
            raise ValueError("The provided template program is empty.")

        self._llm = llm
        self._evaluator = evaluator
        self._database = MCTSAHDDatabase(config.pop_size)
        self._logger = logger
        self._prompt_constructor = prompt_constructor

        # `_lock` protects tree traversal, pending-expansion scheduling, and
        # final registration into the shared tree/database structures.
        self._lock = threading.RLock()
        # Prompt sampling can be more parallel than evaluation, so evaluator
        # concurrency is capped separately.
        self._evaluator_semaphore = threading.Semaphore(self._config.num_evaluators)
        self._stop_event = threading.Event()
        self._samples_count = 0
        self._last_db_saved_at: int = -1

        # Search phases:
        #   - bootstrap: template baseline already logged, need first valid i1.
        #   - init_root: expand the initial population with e1-like prompts.
        #   - search: tree-guided MCTS-AHD search is active.
        #   - finished: search should terminate cleanly.
        self._phase = "bootstrap"

        self._tree: Optional[MCTSTree] = None
        # Pending expansions act as a small work queue produced by serialized
        # tree traversal and consumed by multiple sampler threads.
        self._pending_expansions: List[Dict] = []
        self._initialization_trials = 0
        self._max_initialization_trials = (
            self._config.init_trial_multiplier * self._config.init_pop_size
        )
        self._searched_algos: List[AlgoProto] = []

        # Debug mode: print all errors during search (can be set after instantiation)
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
        """Persist the current population and tree summary through the logger."""
        if not self._logger:
            return

        database_dict = self._sanitize_log_value(self._database.to_dict())
        database_dict["sample_num"] = sample_num
        database_dict["phase"] = self._phase
        if self._tree is not None:
            database_dict["tree"] = self._sanitize_log_value(self._tree.to_dict())

        self._logger.log_dict(database_dict, "database")
        self._last_db_saved_at = sample_num
        logging.info(f"Saved database snapshot for sample #{sample_num} to logger.")

    @override
    def initialize(self) -> None:
        """Evaluate and log the template program once as a baseline.

        The template is *not* inserted into the searchable population by
        default. The original MCTS-AHD bootstraps itself from sampled candidates
        rather than anchoring the tree on the template program.
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
            if self._has_valid_score(template_proto.score):
                self._searched_algos.append(
                    self._copy_algo_for_storage(template_proto)
                )
            self._log(template_proto, is_template=True)

    def run(self) -> None:
        """Run the full MCTS-AHD search loop until termination."""
        try:
            self.initialize()
            logging.info(
                "Starting %s MCTS-AHD sampler threads...",
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
    def get_config(self) -> MCTSAHDConfig:
        """Return the active method configuration."""
        return self._config

    @override
    def get_top_k_algos(self, k: int) -> List[AlgoProto]:
        with self._lock:
            return self._get_top_k_algos_from_list(self._searched_algos, k)

    def _build_candidate(
        self,
        *,
        operator: str,
        prompt: str,
        phase: str,
        parents: Optional[List[AlgoProto]] = None,
        tree_parent_node: Optional[MCTSNode] = None,
        local_programs_seen: Optional[set[str]] = None,
    ) -> AlgoProto:
        """Create the mutable candidate container used across one lifecycle."""
        candidate = AlgoProto(language=self._config.language)
        candidate["operator"] = operator
        candidate["prompt"] = prompt
        candidate["phase"] = phase
        if parents is not None:
            candidate["parents"] = parents
            candidate["parent_scores"] = [parent.score for parent in parents]
        if tree_parent_node is not None:
            candidate["_tree_parent_node"] = tree_parent_node
        if local_programs_seen is not None:
            candidate["_local_programs_seen"] = local_programs_seen
        return candidate

    def _finalize_initialization_if_ready(self) -> None:
        """Build the MCTS tree once initialization has reached its stopping rule."""
        if self._tree is not None:
            return
        if self._phase not in {"bootstrap", "init_root"}:
            return

        # If even the first valid seed solution cannot be found within the
        # initialization budget, the method cannot proceed into tree search.
        if (
            self._phase == "bootstrap"
            and len(self._database) == 0
            and self._initialization_trials >= self._max_initialization_trials
        ):
            logging.warning(
                "MCTS-AHD failed to obtain a feasible bootstrap candidate after %d trials.",
                self._initialization_trials,
            )
            self._phase = "finished"
            self._stop_event.set()
            return

        if self._phase == "bootstrap" and len(self._database) > 0:
            self._phase = "init_root"

        if self._phase != "init_root":
            return

        should_finalize = False
        if len(self._database) >= self._config.init_pop_size:
            should_finalize = True
        elif self._initialization_trials >= self._max_initialization_trials:
            should_finalize = True
            logging.info(
                "Initialization trial budget exhausted with %d/%d feasible algorithms.",
                len(self._database),
                self._config.init_pop_size,
            )

        if not should_finalize:
            return

        if len(self._database) < self._config.selection_num:
            logging.warning(
                "MCTS-AHD initialization produced only %d feasible algorithms; "
                "at least %d are required to enter tree search.",
                len(self._database),
                self._config.selection_num,
            )
            self._phase = "finished"
            self._stop_event.set()
            return

        self._tree = MCTSTree(
            alpha=self._config.alpha,
            lambda_0=self._config.lambda_0,
            max_depth=self._config.max_tree_depth,
        )
        for algo in self._database.population:
            self._tree.add_root_child(algo)

        self._phase = "search"
        logging.info(
            "Initialization finished with %d elite algorithms. Entering tree search.",
            len(self._database),
        )

    def _schedule_search_iteration(self) -> None:
        """Schedule the next batch of tree-guided expansions.

        One scheduled iteration mirrors the original method's shape:

        1. Traverse the tree with UCT.
        2. Optionally trigger one pre-descent expansion when a node's branching
           budget suggests that more children should be added.
        3. At the selected leaf, schedule a weighted operator batch.
        """
        if self._tree is None or self._phase != "search":
            return

        current_node = self._tree.root
        while current_node.children and current_node.depth < self._tree.max_depth:
            eval_remain_ratio = 0.0
            if self._config.max_samples:
                eval_remain_ratio = max(
                    1.0 - self._samples_count / self._config.max_samples,
                    0.0,
                )

            selected_child = max(
                current_node.children,
                key=lambda child: self._tree.uct(child, eval_remain_ratio),
            )

            if self._tree.should_expand_before_descending(current_node):
                operator = "e1" if current_node.is_root else "e2"
                self._pending_expansions.append(
                    {
                        "operator": operator,
                        "current_node": current_node,
                        "phase": "search",
                    }
                )

            current_node = selected_child

        # Leaf-stage operators share one local duplicate set so we do not keep
        # evaluating the same code multiple times inside a single scheduled batch.
        local_programs_seen: set[str] = set()

        weighted_ops = [
            ("e1", self._config.e1_weight),
            ("e2", self._config.e2_weight if self._config.use_e2_operator else 0),
            ("m1", self._config.m1_weight if self._config.use_m1_operator else 0),
            ("m2", self._config.m2_weight if self._config.use_m2_operator else 0),
            ("s1", self._config.s1_weight if self._config.use_s1_operator else 0),
        ]
        for operator, weight in weighted_ops:
            for _ in range(weight):
                self._pending_expansions.append(
                    {
                        "operator": operator,
                        "current_node": current_node,
                        "phase": "search",
                        "local_programs_seen": local_programs_seen,
                    }
                )

    def _build_e1_parents(self) -> List[AlgoProto]:
        """Sample one representative from each root branch for the ``e1`` operator."""
        assert self._tree is not None
        parents: List[AlgoProto] = []
        for branch_root in self._tree.root.children:
            branch_pool = branch_root.subtree or [branch_root]
            selected_node = random.choice(branch_pool)
            parents.append(copy.deepcopy(selected_node.algo))
        return parents

    def _build_path_algos(self, node: MCTSNode) -> List[AlgoProto]:
        """Collect and deduplicate path algorithms for the ``s1`` operator."""
        path_algos: List[AlgoProto] = []
        seen_programs: set[str] = set()

        current: Optional[MCTSNode] = node
        while current is not None and not current.is_root:
            if current.algo is not None and current.program not in seen_programs:
                seen_programs.add(current.program)
                path_algos.append(copy.deepcopy(current.algo))
            current = current.parent

        path_algos.sort(key=lambda algo: algo.score, reverse=True)
        return path_algos

    def _create_candidate_from_context(self, context: Dict) -> Optional[AlgoProto]:
        """Translate one scheduled expansion context into a concrete prompt."""
        operator = context["operator"]
        current_node: Optional[MCTSNode] = context.get("current_node")
        local_programs_seen = context.get("local_programs_seen")
        phase = context.get("phase", self._phase)

        # Retry prompt construction a few times for operators whose parent choice
        # can fail, such as e2 when the alternative partner equals the current node.
        for _ in range(self._config.expansion_retry_limit):
            if operator == "i1":
                prompt = self._prompt_constructor.construct_prompt_i1(
                    self._config.task_description,
                    self._template_program_str,
                    self._config.language,
                )
                return self._build_candidate(
                    operator=operator,
                    prompt=prompt,
                    phase=phase,
                )

            if operator == "e1":
                if self._tree is not None:
                    # After the tree exists, `e1` uses one representative from
                    # each root branch, matching the method's branch-aware
                    # exploration bias.
                    parents = self._build_e1_parents()
                    tree_parent_node = current_node
                else:
                    # During initialization there is no tree yet, so `e1`
                    # falls back to the current elite population snapshot.
                    parents = [copy.deepcopy(algo) for algo in self._database.population]
                    tree_parent_node = None

                if not parents:
                    return None

                prompt = self._prompt_constructor.construct_prompt_e1(
                    self._config.task_description,
                    parents,
                    self._template_program_str,
                    self._config.language,
                )
                return self._build_candidate(
                    operator=operator,
                    prompt=prompt,
                    phase=phase,
                    parents=parents,
                    tree_parent_node=tree_parent_node,
                    local_programs_seen=local_programs_seen,
                )

            if operator == "e2":
                if current_node is None or current_node.algo is None:
                    return None
                # `e2` needs a distinct elite partner so the prompt compares
                # the current node against another strong but different sample.
                others = self._database.select_algos(
                    1,
                    exclude_programs=[current_node.program],
                )
                if not others:
                    return None
                parents = [copy.deepcopy(others[0]), copy.deepcopy(current_node.algo)]
                prompt = self._prompt_constructor.construct_prompt_e2(
                    self._config.task_description,
                    parents,
                    self._template_program_str,
                    self._config.language,
                )
                return self._build_candidate(
                    operator=operator,
                    prompt=prompt,
                    phase=phase,
                    parents=parents,
                    tree_parent_node=current_node,
                    local_programs_seen=local_programs_seen,
                )

            if operator == "m1":
                if current_node is None or current_node.algo is None:
                    return None
                parent = copy.deepcopy(current_node.algo)
                prompt = self._prompt_constructor.construct_prompt_m1(
                    self._config.task_description,
                    parent,
                    self._template_program_str,
                    self._config.language,
                )
                return self._build_candidate(
                    operator=operator,
                    prompt=prompt,
                    phase=phase,
                    parents=[parent],
                    tree_parent_node=current_node,
                    local_programs_seen=local_programs_seen,
                )

            if operator == "m2":
                if current_node is None or current_node.algo is None:
                    return None
                parent = copy.deepcopy(current_node.algo)
                prompt = self._prompt_constructor.construct_prompt_m2(
                    self._config.task_description,
                    parent,
                    self._template_program_str,
                    self._config.language,
                )
                return self._build_candidate(
                    operator=operator,
                    prompt=prompt,
                    phase=phase,
                    parents=[parent],
                    tree_parent_node=current_node,
                    local_programs_seen=local_programs_seen,
                )

            if operator == "s1":
                if current_node is None:
                    return None
                parents = self._build_path_algos(current_node)
                # Path synthesis only makes sense when the path carries at
                # least two distinct historical designs.
                if len(parents) < 2:
                    return None
                prompt = self._prompt_constructor.construct_prompt_s1(
                    self._config.task_description,
                    parents,
                    self._template_program_str,
                    self._config.language,
                )
                return self._build_candidate(
                    operator=operator,
                    prompt=prompt,
                    phase=phase,
                    parents=parents,
                    tree_parent_node=current_node,
                    local_programs_seen=local_programs_seen,
                )

            return None

        return None

    def _generate_evaluate_register_loop(self) -> None:
        """Main lifecycle loop for a single MCTS-AHD sampler thread."""
        while not self.is_stopped():
            with self._lock:
                if self.is_stopped():
                    self._stop_event.set()
                    break

            try:
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
                    "Exception in MCTS-AHD sampler thread: %s",
                    traceback.format_exc(),
                )
                if self.debug_mode:
                    logging.error(
                        "Debug mode: error in MCTS-AHD sampler thread: %s",
                        exc,
                    )
                    logging.error(format_error_box(traceback.format_exc()))
                    if self.debug_mode_crash:
                        self._stop_event.set()
                        raise
                time.sleep(0.2)

    @override
    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """Select the next operator context and construct a candidate prompt."""
        with self._lock:
            if self.is_stopped():
                return None

            self._finalize_initialization_if_ready()
            if self._phase == "finished":
                return None

            if self._phase == "bootstrap":
                return self._create_candidate_from_context(
                    {"operator": "i1", "phase": "bootstrap"}
                )

            if self._phase == "init_root":
                if len(self._database) < self._config.init_pop_size:
                    return self._create_candidate_from_context(
                        {"operator": "e1", "phase": "init_root"}
                    )
                self._finalize_initialization_if_ready()

            if self._phase != "search":
                return None

            if not self._pending_expansions:
                # Only one thread schedules new tree work at a time. After that,
                # the queued contexts can be consumed in parallel by samplers.
                self._schedule_search_iteration()

            while self._pending_expansions:
                context = self._pending_expansions.pop(0)
                candidate = self._create_candidate_from_context(context)
                if candidate is not None:
                    return candidate

        return None

    @override
    def generate(self, candidate: AlgoProto) -> AlgoProto:
        """Call the LLM and attach the raw response to the candidate."""
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
        """Evaluate the candidate program and copy useful metrics onto it."""
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
        """Register one evaluated candidate into logs, population, and tree.

        Registration is intentionally conservative:

        - all evaluated candidates count toward the sample budget and are logged;
        - only finite-scored candidates can enter the elite population;
        - local per-iteration duplicate guards prevent repeated tree insertions;
        - only accepted elite candidates are attached to the MCTS tree.
        """
        if algo_proto is None:
            return

        with self._lock:
            if self.is_stopped():
                return

            self._samples_count += 1

            accepted_by_population = False
            accepted_by_tree = False
            tree_depth: Optional[int] = None

            local_programs_seen = algo_proto.get("_local_programs_seen")
            local_duplicate = False
            if local_programs_seen is not None and algo_proto.program:
                # Duplicate protection is per scheduled batch, not global tree
                # state. This is enough to prevent wasteful repeated evaluation
                # within one leaf expansion wave.
                local_duplicate = algo_proto.program in local_programs_seen

            is_valid_algo = algo_proto.program and self._has_valid_score(
                algo_proto.score
            )
            if is_valid_algo:
                stored_algo_proto = self._copy_algo_for_storage(
                    algo_proto,
                    drop_metadata_keys=["_tree_parent_node", "_local_programs_seen"],
                )
                self._searched_algos.append(copy.deepcopy(stored_algo_proto))

            if is_valid_algo and not local_duplicate:
                accepted_by_population = self._database.register_algo(stored_algo_proto)
                if accepted_by_population and local_programs_seen is not None:
                    local_programs_seen.add(algo_proto.program)

                tree_parent_node = algo_proto.get("_tree_parent_node")
                if (
                    accepted_by_population
                    and tree_parent_node is not None
                    and self._tree is not None
                ):
                    # Tree insertion only happens after elite acceptance so the
                    # tree remains aligned with the searchable population.
                    node = self._tree.attach_child(tree_parent_node, stored_algo_proto)
                    accepted_by_tree = True
                    tree_depth = node.depth

            if self._phase in {"bootstrap", "init_root"}:
                self._initialization_trials += 1
                if accepted_by_population and self._phase == "bootstrap":
                    self._phase = "init_root"

            if tree_depth is not None:
                algo_proto["tree_depth"] = tree_depth

            self._finalize_initialization_if_ready()
            self._log(algo_proto)

            if self._phase == "finished":
                self._stop_event.set()

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
            # Snapshotting is keyed to the global evaluated-sample counter so
            # logs stay coherent even when threads finish out of order.
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

        tree_depth_str = "-"
        if algo_proto.get("tree_depth") is not None:
            tree_depth_str = str(algo_proto.get("tree_depth"))

        status_parts = [
            f"Algo {algo_id_str:<24}",
            f"Score: {score_str}",
            f"Sample: {sample_time_str}",
            time_info,
        ]
        status_parts.append(f"Depth: {tree_depth_str}")
        logging.info(
            " | ".join(status_parts)
        )

        if self._logger:
            # Keep only whitelisted metadata before serializing the candidate.
            log_entry = self._serialize_algo_for_logging(algo_proto)
            log_entry.update(
                {
                    "sample_num": current_sample_num,
                    "operator": operator,
                    "phase": phase,
                    "sample_time": 0.0 if is_template else sample_time_val,
                    "pop_size": len(self._database),
                    "best_score": self._database.get_best_score(),
                    "tree_num_nodes": self._tree.num_nodes() if self._tree else 0,
                }
            )
            self._logger.log_dict(log_entry, "algo")
