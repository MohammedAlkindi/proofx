"""Public API for Collatz analytics."""

from .runtime import EnhancedConfig, EnhancedFormatter, config, configure_logging, logger
from .sequence import CollatzSequence, CollatzVariant

__all__ = [
    "AlgebraicFeatureExtractor",
    "CollatzAnalyzer",
    "CollatzSequence",
    "CollatzVariant",
    "EnhancedConfig",
    "EnhancedFormatter",
    "FeatureExtractor",
    "FeatureUnion",
    "FitResult",
    "ModelType",
    "StatisticalFeatureExtractor",
    "config",
    "configure_logging",
    "logger",
]

_ANALYTICS_EXPORTS = {
    "AlgebraicFeatureExtractor",
    "CollatzAnalyzer",
    "FeatureExtractor",
    "FeatureUnion",
    "FitResult",
    "ModelType",
    "StatisticalFeatureExtractor",
}


def __getattr__(name: str):
    """Load model-heavy analytics exports only when they are requested."""
    if name in _ANALYTICS_EXPORTS:
        from . import analytics

        return getattr(analytics, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
