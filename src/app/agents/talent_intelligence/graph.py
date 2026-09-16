from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from src.app.core.llm_client import get_chat_model

from .registry import build_tool_schemas

TOOL_LOOP_FAILURE = (
    "Unable to complete the investigation within the tool-call limit. "
    "Please retry or narrow the question. This does not mean evidence is missing."
)

TOOL_SCHEMAS: list[dict[str, Any]] = build_tool_schemas()


class ToolLoopState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    steps: int


ToolHandler = Callable[[dict[str, Any]], Any]


def run_tool_loop(
    question: str,
    system_prompt: str,
    tool_schemas: list[dict[str, Any]],
    handlers: dict[str, ToolHandler],
    max_steps: int = 3,
) -> str:
    """Run the Talent Intelligence tool graph with Python-owned handlers."""
    model = get_chat_model().bind_tools(tool_schemas)

    def call_model(state: ToolLoopState) -> dict[str, Any]:
        response = model.invoke(state["messages"])
        return {"messages": [response], "steps": state["steps"] + 1}

    def execute_tools(state: ToolLoopState) -> dict[str, Any]:
        message = state["messages"][-1]
        if not isinstance(message, AIMessage):
            return {"messages": [], "steps": state["steps"]}

        outputs: list[ToolMessage] = []
        for call in message.tool_calls:
            try:
                arguments = call.get("args", {})
                handler = handlers.get(call["name"])
                output = (
                    handler(arguments)
                    if handler
                    else {"status": "error", "message": "Unknown tool."}
                )
            except Exception:
                output = {
                    "status": "error",
                    "message": "Tool execution failed. Please retry.",
                }
            outputs.append(
                ToolMessage(
                    content=json.dumps(output, default=str),
                    tool_call_id=call["id"],
                )
            )
        return {"messages": outputs, "steps": state["steps"]}

    def route_after_model(state: ToolLoopState) -> str:
        message = state["messages"][-1]
        if isinstance(message, AIMessage) and message.tool_calls:
            return "tools" if state["steps"] < max_steps else END
        return END

    graph = StateGraph(ToolLoopState)
    graph.add_node("model", call_model)
    graph.add_node("tools", execute_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model)
    graph.add_edge("tools", "model")
    result = graph.compile().invoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=question),
            ],
            "steps": 0,
        }
    )
    final = result["messages"][-1]
    if isinstance(final, AIMessage) and final.content:
        return str(final.content)
    return TOOL_LOOP_FAILURE


__all__ = ["TOOL_LOOP_FAILURE", "TOOL_SCHEMAS", "ToolLoopState", "run_tool_loop"]
