"""LLM-specific exceptions."""


class LLMError(Exception):
    """Base exception for all LLM errors."""

    def __init__(self, message: str, model: str = "", retryable: bool = True):
        self.model = model
        self.retryable = retryable
        super().__init__(message)


class LLMTimeoutError(LLMError):
    """LLM call exceeded timeout."""

    def __init__(self, model: str = "", timeout: int = 0):
        super().__init__(
            f"LLM call to {model} timed out after {timeout}s",
            model=model,
            retryable=True,
        )


class LLMUnavailableError(LLMError):
    """All models in the fallback chain are unavailable."""

    def __init__(self, models_tried: list[str] | None = None):
        models = models_tried or []
        super().__init__(
            f"All LLM models unavailable: {', '.join(models)}",
            retryable=True,
        )


class LLMResponseError(LLMError):
    """LLM returned an invalid or unparseable response."""

    def __init__(self, model: str = "", detail: str = ""):
        super().__init__(
            f"Invalid LLM response from {model}: {detail}",
            model=model,
            retryable=True,
        )
