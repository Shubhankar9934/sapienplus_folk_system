"""Layer 3.5 - Reference Verification Engine."""

from folk.reference.engine import (
    CitationNormalizer,
    ReferenceLibraryBuilder,
    ReferenceValidator,
    check_minimums,
)

__all__ = [
    "CitationNormalizer",
    "ReferenceLibraryBuilder",
    "ReferenceValidator",
    "check_minimums",
]
