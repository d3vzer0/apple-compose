class AppleComposeError(Exception):
    """Base exception for user-facing apple-compose errors."""


class ComposeValidationError(AppleComposeError):
    """Raised when a Compose file cannot be validated."""


class InterpolationError(AppleComposeError):
    """Raised when environment loading fails."""


class PlanningError(AppleComposeError):
    """Raised when a Compose application cannot be planned."""


class ContainerRuntimeError(AppleComposeError):
    """Raised when the Apple container CLI fails."""
