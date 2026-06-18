from dataclasses import dataclass

from app.schemas.errors import ErrorCode


@dataclass(slots=True)
class APIException(Exception):
    code: ErrorCode
    message: str
    retryable: bool
