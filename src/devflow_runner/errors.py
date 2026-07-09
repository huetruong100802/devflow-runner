"""Domain exceptions for DevFlow Runner."""

from __future__ import annotations


class DevFlowError(Exception):
    """Base runner error with a stable machine code."""

    code = "DEVFLOW_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


class ConfigError(DevFlowError):
    code = "CONFIG_ERROR"


class ValidationError(DevFlowError):
    code = "VALIDATION_ERROR"


class ResolverError(DevFlowError):
    code = "RESOLVER_ERROR"


class ToolExecutionError(DevFlowError):
    code = "TOOL_EXECUTION_ERROR"


class ToolReturnedError(ToolExecutionError):
    code = "TOOL_RETURNED_ERROR"


class ToolProtocolError(DevFlowError):
    code = "TOOL_PROTOCOL_ERROR"
