"""Decorator helpers for running evaluator code inside a sandbox.

This module exposes :func:`sandbox_run`, the high-level decorator used by task
evaluators and examples throughout the repository. The decorator hides the
details of the underlying sandbox executor implementation and provides a stable
result contract by optionally injecting common evaluator metadata such as
execution time and error messages.
"""

# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import copy
import functools
from typing import Literal, Optional, Any, Callable, Dict

from algodisco.toolkit.sandbox.sandbox_executor import (
    SandboxExecutor,
    ExecutionResults,
)
from algodisco.toolkit.sandbox.sandbox_executor_simple import SandboxExecutorSimple
from algodisco.toolkit.sandbox.sandbox_executor_ray import SandboxExecutorRay

__all__ = ["sandbox_run"]


def _is_class_method(func) -> bool:
    """Return ``True`` when ``func`` looks like a class instance method."""
    return "." in func.__qualname__ and "<locals>" not in func.__qualname__


def _is_top_level_function(func) -> bool:
    """Return ``True`` when ``func`` appears to be a module-level function."""
    return func.__qualname__ == func.__name__


class _FunctionWorker:
    """Wrap a standalone function so sandbox executors can call a ``run`` method.

    The sandbox executors are written around an object-plus-method interface.
    For plain functions, this tiny adapter keeps the executor API uniform.
    """

    def __init__(self, func):
        self.func = func

    def run(self, *args, **kwargs):
        """Invoke the wrapped standalone function."""
        return self.func(*args, **kwargs)


def sandbox_run(
    sandbox_type: Literal["ray", "process", "simple"] = "simple",
    timeout: Optional[float] = None,
    redirect_to_devnull: bool = False,
    ray_actor_options: Optional[Dict[str, Any]] = None,
    add_execution_time_in_res_dict: bool = True,
    add_error_msg_in_res_dict: bool = True,
    **executor_init_kwargs,
):
    """
    Execute a method or function inside an isolated sandbox executor.

    The decorated callable is not run inline in the caller process. Instead,
    ``sandbox_run`` creates one of the supported executor types and forwards the
    invocation to that executor. This is primarily used by evaluator methods
    that execute candidate programs and need protection against crashes,
    timeouts, or noisy stdout/stderr.

    The decorator supports both instance methods and standalone functions:

    - For instance methods, the evaluator object is shallow-copied and the copy
      is executed in the sandbox. A private bypass flag prevents infinite
      recursion when the copied worker calls the original method body.
    - For standalone functions, the function is wrapped in a lightweight object
      exposing a ``run`` method so it can be passed to the same executor API.

    By default, the decorator normalizes the returned payload into a dictionary
    and injects ``execution_time`` and ``error_msg`` fields. This keeps the
    evaluator result shape predictable even when the wrapped callable returns a
    plain scalar or omits these common metadata fields.

    Args:
        sandbox_type: Which executor backend to use. ``"ray"`` uses
            :class:`SandboxExecutorRay`, ``"process"`` uses the shared-memory
            process executor, and ``"simple"`` uses the queue-based simple
            process executor. The default is ``"simple"``.
        timeout: Maximum allowed runtime in seconds for the sandboxed call. If
            the timeout is exceeded, the executor returns ``None`` or an error
            payload depending on its backend behavior.
        redirect_to_devnull: When ``True``, redirect stdout and stderr from the
            sandboxed execution to ``/dev/null``. This is useful for keeping
            evaluation logs clean when candidate programs print aggressively.
        ray_actor_options: Extra options passed to the Ray actor constructor
            when ``sandbox_type="ray"``.
        add_execution_time_in_res_dict: When ``True``, append an
            ``execution_time`` field to the returned result dictionary. Missing
            values are normalized to ``0.0``.
        add_error_msg_in_res_dict: When ``True``, append an ``error_msg`` field
            to the returned result dictionary. Missing values are normalized to
            the empty string.
        **executor_init_kwargs: Additional keyword arguments forwarded to the
            chosen executor constructor, such as ``debug_mode`` or ``init_ray``.

    Returns:
        A decorator that wraps the target callable and executes it in the
        selected sandbox environment.
    """
    # Followings are to cheat IDE
    executor_init_kwargs.get("debug_mode", False)
    executor_init_kwargs.get("init_ray", None)
    executor_init_kwargs.get("recur_kill_eval_proc", False)

    def decorator(func: Callable) -> Callable:
        """Wrap ``func`` so its body executes through a sandbox executor."""
        is_class_method = _is_class_method(func)  # noqa

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Dispatch the wrapped callable to the configured sandbox backend."""
            if is_class_method:
                # Treated as a method call: args[0] is 'self'
                if not args:
                    raise RuntimeError("Method call expected 'self' as first argument.")
                self_instance = args[0]
                method_args = args[1:]

                # Check bypass flag to prevent recursion
                if getattr(self_instance, "_bypass_sandbox", False):
                    return func(self_instance, *method_args, **kwargs)

                # Create worker copy
                evaluate_worker = copy.copy(self_instance)
                evaluate_worker._bypass_sandbox = True
                method_name = func.__name__
            else:
                # Treated as a standalone function
                worker = _FunctionWorker(func)
                evaluate_worker = worker
                method_name = "run"
                method_args = args

            # Prepare Executor
            if sandbox_type == "ray":
                import ray

                init_ray = executor_init_kwargs.get("init_ray", None)
                if init_ray is None:
                    init_ray = not ray.is_initialized()

                executor = SandboxExecutorRay(
                    evaluate_worker,
                    init_ray=init_ray,
                    **executor_init_kwargs,
                )
                ray_options = ray_actor_options
            elif sandbox_type == "simple":
                executor = SandboxExecutorSimple(
                    evaluate_worker, **executor_init_kwargs
                )
                ray_options = None
            else:
                executor = SandboxExecutor(evaluate_worker, **executor_init_kwargs)
                ray_options = None  # Not used for process

            # Execute
            if sandbox_type == "ray":
                result = executor.secure_execute(
                    worker_execute_method_name=method_name,
                    method_args=method_args,
                    method_kwargs=kwargs,
                    timeout_seconds=timeout,
                    redirect_to_devnull=redirect_to_devnull,
                    ray_actor_options=ray_options,
                )
            else:
                result = executor.secure_execute(
                    worker_execute_method_name=method_name,
                    method_args=method_args,
                    method_kwargs=kwargs,
                    timeout_seconds=timeout,
                    redirect_to_devnull=redirect_to_devnull,
                )

            # Handle case when result is None (e.g., timeout or execution failure)
            if result is None:
                return None

            # Create a new dict to hold the results, starting with the actual result if exists
            if result["result"] is not None:
                actual_result = result["result"]
                # If the result is not a dict, wrap it in a dict
                if isinstance(actual_result, dict):
                    final_results = actual_result
                else:
                    final_results = {"result": actual_result}
            else:
                final_results = {}

            # Always provide stable defaults for the shared evaluator fields so
            # downstream code does not need to defensively check for missing
            # keys on every evaluation result.
            if add_execution_time_in_res_dict:
                execution_time = result.get("execution_time", 0.0)
                if execution_time is None:
                    execution_time = 0.0
                final_results.update({"execution_time": float(execution_time)})

            if add_error_msg_in_res_dict:
                error_msg = result.get("error_msg", "")
                if error_msg is None:
                    error_msg = ""
                final_results.update({"error_msg": str(error_msg)})

            return final_results

        return wrapper

    return decorator
