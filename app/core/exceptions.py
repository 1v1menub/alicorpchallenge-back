class ConflictError(Exception):
    """Raised when an operation conflicts with the resource's current state.

    Routes translate this to HTTP 409 Conflict.
    """
