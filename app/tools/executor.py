from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolRequest, ToolResult, ToolStatus


class ToolExecutor:
    """Execute registered tools and return structured results."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, request: ToolRequest) -> ToolResult:
        """Execute a tool request and capture its outcome."""

        # Step 1: Find the requested tool.
        try:
            tool = self.registry.get(request.tool_name)

        except KeyError:
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILURE,
                error=f"Tool '{request.tool_name}' is not registered.",
            )

        # Step 2: Execute the tool.
        try:
            output = tool.execute(request.arguments)

            # Tools must return dictionaries.
            if not isinstance(output, dict):
                raise TypeError(
                    "Tool output must be a dictionary."
                )

            # Step 3: Return a successful result.
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.SUCCESS,
                output=output,
            )

        except Exception as exc:
            # Capture execution errors instead of crashing the application.
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILURE,
                error=f"Tool execution failed: {exc}",
            )