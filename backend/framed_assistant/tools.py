from __future__ import annotations

import ast
import asyncio
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from jsonschema import ValidationError, validate

from .errors import ToolError
from .models import HostContext
from .store import Store

ToolHandler = Callable[[HostContext, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    side_effect: str
    risk: str
    permission: str
    confirmation: str
    idempotency: str
    handler: ToolHandler
    timeout_ms: int = 5_000
    max_attempts: int = 1

    def manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": "0.1.0",
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "side_effect": self.side_effect,
            "risk": self.risk,
            "permissions": [] if self.permission == "none" else [self.permission],
            "timeout_ms": self.timeout_ms,
            "retry": {"max_attempts": self.max_attempts},
            "confirmation": self.confirmation,
            "idempotency": self.idempotency,
            "redaction": {},
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def definitions(self) -> list[dict[str, Any]]:
        return [tool.manifest() for tool in self._tools.values()]

    async def execute(self, name: str, host: HostContext, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools[name]
        try:
            validate(arguments, tool.input_schema)
            result = await asyncio.wait_for(
                asyncio.to_thread(tool.handler, host, arguments),
                timeout=tool.timeout_ms / 1_000,
            )
            validate(result, tool.output_schema)
        except TimeoutError as error:
            raise ToolError(f"Tool timed out after {tool.timeout_ms} ms") from error
        except ValidationError as error:
            raise ToolError(f"Tool schema validation failed: {error.message}") from error
        except ValueError as error:
            raise ToolError(str(error)) from error
        return result


def create_essentials_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        deterministic_tool(
            "essentials.current_time",
            object_schema(),
            object_schema(required=["iso"], properties={"iso": {"type": "string"}}),
            lambda _host, _arguments: {"iso": datetime.now(UTC).isoformat()},
        )
    )
    registry.register(
        deterministic_tool(
            "essentials.calculate",
            object_schema(required=["expression"], properties={"expression": {"type": "string"}}),
            object_schema(required=["result"], properties={"result": {"type": "string"}}),
            lambda _host, arguments: {"result": str(evaluate_expression(arguments["expression"]))},
        )
    )
    registry.register(
        deterministic_tool(
            "essentials.convert_unit",
            object_schema(
                required=["value", "from", "to"],
                properties={
                    "value": {"type": "number"},
                    "from": {"enum": sorted(CONVERSIONS)},
                    "to": {"enum": sorted(CONVERSIONS)},
                },
            ),
            object_schema(
                required=["value", "unit"],
                properties={"value": {"type": "number"}, "unit": {"type": "string"}},
            ),
            lambda _host, arguments: convert_unit(arguments["value"], arguments["from"], arguments["to"]),
        )
    )
    registry.register(
        deterministic_tool(
            "essentials.format_currency",
            object_schema(
                required=["amount", "currency"],
                properties={
                    "amount": {"type": "number"},
                    "currency": {"type": "string", "minLength": 3, "maxLength": 3},
                },
            ),
            object_schema(required=["formatted"], properties={"formatted": {"type": "string"}}),
            lambda _host, arguments: {
                "formatted": f"{arguments['currency'].upper()} {Decimal(str(arguments['amount'])):,.2f}"
            },
        )
    )
    registry.register(
        deterministic_tool(
            "essentials.text_cleanup",
            object_schema(required=["text"], properties={"text": {"type": "string"}}),
            object_schema(required=["text"], properties={"text": {"type": "string"}}),
            lambda _host, arguments: {"text": re.sub(r"\s+", " ", arguments["text"]).strip()},
        )
    )
    return registry


def register_reference_tools(registry: ToolRegistry, store: Store) -> None:
    registry.register(
        ToolDefinition(
            name="host.records.list",
            input_schema=object_schema(),
            output_schema=object_schema(required=["records"], properties={"records": {"type": "array"}}),
            side_effect="read",
            risk="low",
            permission="records.read",
            confirmation="none",
            idempotency="not-applicable",
            handler=lambda host, _arguments: {"records": store.list_host_records(host)},
        )
    )
    registry.register(
        ToolDefinition(
            name="knowledge.search",
            input_schema=object_schema(required=["query"], properties={"query": {"type": "string", "minLength": 1}}),
            output_schema=object_schema(required=["documents"], properties={"documents": {"type": "array"}}),
            side_effect="external-read",
            risk="medium",
            permission="knowledge.read",
            confirmation="policy",
            idempotency="not-applicable",
            handler=lambda host, arguments: {
                "documents": [
                    document.model_dump(mode="json") for document in store.search_knowledge(host, arguments["query"])
                ]
            },
        )
    )


def create_tool_registry(store: Store) -> ToolRegistry:
    registry = create_essentials_registry()
    register_reference_tools(registry, store)
    return registry


def deterministic_tool(
    name: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    handler: ToolHandler,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        input_schema=input_schema,
        output_schema=output_schema,
        side_effect="none",
        risk="low",
        permission="none",
        confirmation="none",
        idempotency="not-applicable",
        handler=handler,
    )


def object_schema(
    *,
    required: list[str] | None = None,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required or [],
        "properties": properties or {},
        "additionalProperties": False,
    }


CONVERSIONS = {
    "kg": ("mass", Decimal("1")),
    "lb": ("mass", Decimal("0.45359237")),
    "km": ("distance", Decimal("1")),
    "mi": ("distance", Decimal("1.609344")),
    "m": ("distance", Decimal("0.001")),
}


def convert_unit(value: float, source: str, target: str) -> dict[str, float | str]:
    source_family, source_factor = CONVERSIONS[source]
    target_family, target_factor = CONVERSIONS[target]
    if source_family != target_family:
        raise ValueError(f"Cannot convert {source} to {target}")
    converted = Decimal(str(value)) * source_factor / target_factor
    return {"value": float(converted), "unit": target}


BIN_OPS: dict[type[ast.operator], Callable[[Decimal, Decimal], Decimal]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
UNARY_OPS: dict[type[ast.unaryop], Callable[[Decimal], Decimal]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def evaluate_expression(expression: str) -> Decimal:
    return evaluate_node(ast.parse(expression, mode="eval").body)


def evaluate_node(node: ast.expr) -> Decimal:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
        return BIN_OPS[type(node.op)](evaluate_node(node.left), evaluate_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](evaluate_node(node.operand))
    raise ValueError("Expression contains an unsupported operation")
