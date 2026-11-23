
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Define the common interface for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def argument_schema(self) -> dict[str, Any]:
        """Return the JSON schema describing accepted arguments."""

        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": True,
        }

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        """Validate arguments against the declared tool schema."""

        schema = self.argument_schema
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object.")

        for key in required:
            if key not in arguments:
                raise ValueError(
                    f"Missing required argument: '{key}'."
                )

        if not schema.get("additionalProperties", True):
            unknown = set(arguments) - set(properties)

            if unknown:
                raise ValueError(
                    f"Unexpected arguments: {sorted(unknown)}."
                )

        expected_types = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        for key, value in arguments.items():
            definition = properties.get(key)

            if definition is None:
                continue

            expected_type = expected_types.get(
                definition.get("type")
            )

            if expected_type is None:
                continue

            if not isinstance(value, expected_type):
                raise ValueError(
                    f"Argument '{key}' must be "
                    f"{definition.get('type')}."
                )

            if isinstance(value, str) and not value.strip():
                raise ValueError(
                    f"Argument '{key}' must not be blank."
                )

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        pass


class ToolRegistry:
    """Register, retrieve, and manage available agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' is not registered."
            )

        return self._tools[name]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def describe_tools(self) -> list[dict[str, Any]]:
        """Return tool descriptions for the planner."""

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "arguments": tool.argument_schema,
            }
            for tool in self._tools.values()
        ]