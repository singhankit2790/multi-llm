class ProviderError(Exception):
    """Base class for application-level LLM provider errors."""

    category = "unknown"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MissingAPIKeyError(ProviderError):
    category = "missing_api_key"


class AuthenticationFailureError(ProviderError):
    category = "authentication"


class RateLimitError(ProviderError):
    category = "rate_limit"


class ProviderTimeoutError(ProviderError):
    category = "timeout"


class ProviderUnavailableError(ProviderError):
    category = "unavailable"


class InvalidRequestError(ProviderError):
    category = "invalid_request"


class UnknownProviderError(ProviderError):
    category = "unknown_provider"


class UnknownProviderFailureError(ProviderError):
    category = "unknown"


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session '{session_id}' was not found")
        self.session_id = session_id
