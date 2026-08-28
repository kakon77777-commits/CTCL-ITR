"""Interoperability projections for canonical CTCL-ITR ATL events."""

__all__ = [
    "CloudEventError",
    "from_cloudevent",
    "to_cloudevent",
    "OpenTelemetryProjectionError",
    "project_event",
    "project_events",
]


def __getattr__(name):
    if name in {"CloudEventError", "from_cloudevent", "to_cloudevent"}:
        from . import cloudevents
        return getattr(cloudevents, name)
    if name in {"OpenTelemetryProjectionError", "project_event", "project_events"}:
        from . import opentelemetry
        return getattr(opentelemetry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
