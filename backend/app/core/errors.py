"""Domain errors raised by services and translated to HTTP responses in main.py."""


class AppError(Exception):
    """Base class for domain errors carrying an HTTP status code.

    Attributes:
        status (int): HTTP status code this error maps to.
    """

    status = 400


class InvalidInputError(AppError):
    """A value failed domain validation (e.g. field value vs. field type, FR-14)."""

    status = 400


class AuthenticationError(AppError):
    """Credentials are missing or wrong."""

    status = 401


class NotFoundError(AppError):
    """The requested entity does not exist."""

    status = 404


class ConflictError(AppError):
    """The request conflicts with existing state (e.g. setup already done)."""

    status = 409


class PayloadTooLargeError(AppError):
    """An upload exceeded the configured size limit (FR-20)."""

    status = 413


class RateLimitedError(AppError):
    """Too many failed attempts; retry after a cooldown (SEC hardening, G-07)."""

    status = 429
