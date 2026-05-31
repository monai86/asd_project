"""FastAPI backend boundary for the therapist clinical pilot app."""


def create_app(*args, **kwargs):
    """Lazily import FastAPI app factory so package import stays lightweight."""
    from .app import create_app as _create_app

    return _create_app(*args, **kwargs)

__all__ = ["create_app"]
