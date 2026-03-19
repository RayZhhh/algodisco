# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import os
from os import PathLike
from typing import Optional, Dict, Any
from .pickle_logger import BasePickleLogger


class BaseSwanLabLogger(BasePickleLogger):
    """A base Pickle logger that also logs common metrics to SwanLab."""

    def __init__(
        self,
        logdir: PathLike | str,
        project: str,
        experiment_name: Optional[str] = None,
        group: Optional[str] = None,
        config: Optional[dict] = None,
        swanlab_logdir: Optional[PathLike | str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(
            logdir=str(logdir),
        )

        try:
            import swanlab
        except ImportError:
            raise ImportError(
                "SwanLab is not installed. Please install it with 'pip install swanlab'"
            )

        if api_key:
            swanlab.login(api_key)

        swanlab_init_kwargs = {
            "project": project,
            "experiment_name": experiment_name,
            "group": group,
            "config": config,
        }

        # Use logdir as swanlab_logdir if not explicitly specified
        if swanlab_logdir is None:
            swanlab_logdir = logdir

        if swanlab_logdir is not None:
            swanlab_init_kwargs["logdir"] = str(swanlab_logdir)

        swanlab_init_kwargs = {
            k: v for k, v in swanlab_init_kwargs.items() if v is not None
        }

        self._swanlab_run = swanlab.init(**swanlab_init_kwargs)
        if not self._swanlab_run:

            class DummyLogger:
                def log(self, *args, **kwargs):
                    pass

                def finish(self, *args, **kwargs):
                    pass

            self._swanlab_run = DummyLogger()

        self._best_score = -float("inf")
        self._all_scores = []
        self._cumulative_sample_time = 0.0
        self._cumulative_eval_time = 0.0
        self._cumulative_execution_time = 0.0
        self._valid_functions_num = 0
        self._invalid_functions_num = 0

    def _prepare_swanlab_log_items(self, log_dict: dict) -> dict:
        """Prepares a dictionary of common items to log to SwanLab."""
        log_items = {}

        # 1. Update state with the current sample's data
        score = log_dict.get("score")
        if score is not None:
            self._valid_functions_num += 1
            self._all_scores.append(score)
            if score > self._best_score:
                self._best_score = score
        else:
            self._invalid_functions_num += 1

        if "sample_time" in log_dict:
            self._cumulative_sample_time += log_dict["sample_time"]
        if "eval_time" in log_dict:
            self._cumulative_eval_time += log_dict["eval_time"]
        if "execution_time" in log_dict:
            self._cumulative_execution_time += log_dict["execution_time"]

        # 2. Prepare items for SwanLab logging
        if self._best_score > -float("inf"):
            log_items["best_score"] = self._best_score

        self._all_scores.sort(reverse=True)
        for k in [5, 10, 20, 30]:
            if len(self._all_scores) >= k:
                top_k_avg = sum(self._all_scores[:k]) / k
                log_items[f"top_{k}_avg_score"] = top_k_avg

        log_items["cumulative_sample_time"] = self._cumulative_sample_time
        log_items["cumulative_eval_time"] = self._cumulative_eval_time
        log_items["cumulative_execution_time"] = self._cumulative_execution_time

        # Log other numeric values from the original log_dict
        for k, v in log_dict.items():
            if isinstance(v, (int, float)):
                log_items[k] = v

        log_items["num_valid_functions"] = self._valid_functions_num
        log_items["num_invalid_functions"] = self._invalid_functions_num

        return log_items

    def _pre_log_hook(self, log_item: Dict, item_name: str):
        """Logs metrics to swanlab before caching."""
        log_items = self._prepare_swanlab_log_items(log_item)
        counter = self._counters.get(item_name, 1)
        self._swanlab_run.log(log_items, step=counter)

    async def finish(self):
        await super().finish()
        if hasattr(self._swanlab_run, "finish"):
            self._swanlab_run.finish()
