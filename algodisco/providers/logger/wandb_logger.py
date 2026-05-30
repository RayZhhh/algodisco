# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import logging
import os
from os import PathLike
from typing import Optional, Dict
from .pickle_logger import BasePickleLogger


class BaseWandbLogger(BasePickleLogger):
    """A base Pickle logger that also logs common metrics to Weights & Biases."""

    def __init__(
        self,
        logdir: PathLike | str,
        project: str,
        experiment_name: Optional[str] = None,
        group: Optional[str] = None,
        config: Optional[dict] = None,
        entity: Optional[str] = None,
        wandb_logdir: Optional[PathLike | str] = None,
        api_key: Optional[str] = None,
        *,
        lazy_init: bool = False,
    ):
        super().__init__(
            logdir=str(logdir),
        )

        try:
            import wandb
        except ImportError:
            raise ImportError(
                "wandb is not installed. Please install it with 'pip install wandb'"
            )

        if api_key is None and os.environ.get("WANDB_API_KEY") is None:
            logging.warning(
                "Weights & Biases API key is not set. Provide api_key or set "
                "WANDB_API_KEY if your W&B setup requires authentication."
            )

        if api_key:
            os.environ["WANDB_API_KEY"] = api_key

        self._project_name = project
        self._experiment_name = experiment_name
        self._group = group
        self._config = config
        self._entity = entity
        self._wandb_logdir = wandb_logdir if wandb_logdir is not None else logdir
        self._wandb_run = None
        self._owns_wandb_run = False
        self._initialized = False
        self._lazy_init = lazy_init

        if not self._lazy_init:
            self._init_wandb()

        self._best_score = -float("inf")
        self._all_scores = []
        self._cumulative_sample_time = 0.0
        self._cumulative_eval_time = 0.0
        self._cumulative_execution_time = 0.0
        self._valid_functions_num = 0
        self._invalid_functions_num = 0

    def _init_wandb(self):
        import wandb

        if self._initialized:
            return

        existing_run = getattr(wandb, "run", None)
        if existing_run is not None:
            logging.warning(
                "Weights & Biases has already been initialized; BaseWandbLogger will reuse the existing run."
            )
            self._wandb_run = existing_run
            self._owns_wandb_run = False
            self._initialized = True
            return

        wandb_init_kwargs = {
            "project": self._project_name,
            "name": self._experiment_name,
            "group": self._group,
            "config": self._config,
            "entity": self._entity,
        }

        if self._wandb_logdir is not None:
            wandb_init_kwargs["dir"] = str(self._wandb_logdir)

        wandb_init_kwargs = {
            k: v for k, v in wandb_init_kwargs.items() if v is not None
        }

        self._wandb_run = wandb.init(**wandb_init_kwargs)
        if not self._wandb_run:

            class DummyLogger:
                def log(self, *args, **kwargs):
                    pass

                def finish(self, *args, **kwargs):
                    pass

            self._wandb_run = DummyLogger()
            self._owns_wandb_run = False
        else:
            self._owns_wandb_run = True

        self._initialized = True

    def _prepare_wandb_log_items(self, log_dict: dict) -> dict:
        """Prepares a dictionary of common items to log to Weights & Biases."""
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

        # 2. Prepare items for W&B logging
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

    def _pre_log_hook(self, log_item: Dict, item_name: str, *, count: int, step: int):
        """Logs metrics to wandb before caching."""
        if not self._initialized:
            self._init_wandb()

        log_items = self._prepare_wandb_log_items(log_item)
        self._wandb_run.log(log_items, step=step)

    def finish(self):
        super().finish()
        if self._owns_wandb_run and hasattr(self._wandb_run, "finish"):
            self._wandb_run.finish()
