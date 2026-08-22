class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class ValidationError(ValueError):
    pass


class ToolError(RuntimeError):
    pass
