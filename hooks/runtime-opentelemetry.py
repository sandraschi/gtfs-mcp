"""PyInstaller runtime hook - pre-load the opentelemetry default runtime context.

Frozen binaries lose entry-point metadata discovery (stripped .dist-info), so
opentelemetry.context._load_runtime_context() raises StopIteration at import
time. Pin the contextvars implementation directly.
"""

from opentelemetry import context as _otel_context
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext

_otel_context._RUNTIME_CONTEXT = ContextVarsRuntimeContext()
_otel_context._RUNTIME_CONTEXT_DEFAULT = _otel_context._RUNTIME_CONTEXT
