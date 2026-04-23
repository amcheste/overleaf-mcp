class PathEscapeError(ValueError):
    """Raised when a target path resolves outside the allowed root."""


class TokenNotFoundError(Exception):
    """Raised when no Overleaf token can be resolved for a given alias."""
