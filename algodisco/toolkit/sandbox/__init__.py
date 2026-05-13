# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from algodisco.toolkit.sandbox.sandbox_executor import (
    SandboxExecutor,
    ExecutionResults,
)
from algodisco.toolkit.sandbox.sandbox_executor_simple import SandboxExecutorSimple
from algodisco.toolkit.sandbox.sandbox_executor_ray import SandboxExecutorRay


def sandbox_run(*args, **kwargs):
    """Compatibility wrapper for the public sandbox decorator.

    Historically some local scripts imported ``sandbox_run`` from
    ``algodisco.toolkit.sandbox`` even though the canonical public location is
    ``algodisco.toolkit.decorators``. Import lazily here so that compatibility
    works without creating an import cycle during module initialization.
    """
    from algodisco.toolkit.decorators import sandbox_run as _sandbox_run

    return _sandbox_run(*args, **kwargs)
