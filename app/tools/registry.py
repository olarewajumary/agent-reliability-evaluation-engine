
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Define the common interface for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Explain what the tool does."""
        pass

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool using the supplied arguments."""
        pass


class ToolRegistry:
    """Register, retrieve, and manage available agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool using its unique name."""

        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name."""

        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' is not registered."
            )

        return self._tools[name]

    def list_tools(self) -> list[str]:
        """Return the names of all registered tools."""

        return list(self._tools.keys())
