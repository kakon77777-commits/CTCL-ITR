"""CTCL-ITR reference utilities."""

__version__ = "0.2.13"
__all__ = ["TopologyError", "analyze_events", "load_events"]


def __getattr__(name):
    if name in __all__:
        from . import topology
        return getattr(topology, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
