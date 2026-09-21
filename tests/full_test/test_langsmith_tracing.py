import sys
from pathlib import Path
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.agents.talent_intelligence.graph import run_tool_loop  # noqa: E402


def test_tool_loop_attaches_langsmith_run_context():
    model = Mock()
    model.bind_tools.return_value = model
    compiled_graph = Mock()
    compiled_graph.invoke.return_value = {
        "messages": [AIMessage(content="answer")]
    }

    with (
        patch(
            "src.app.agents.talent_intelligence.graph.get_chat_model",
            return_value=model,
        ),
        patch(
            "src.app.agents.talent_intelligence.graph.StateGraph.compile",
            return_value=compiled_graph,
        ),
    ):
        assert run_tool_loop("question", "system", [], {}) == "answer"

    invoke_config = compiled_graph.invoke.call_args.kwargs["config"]
    assert invoke_config["run_name"] == "talent_intelligence_tool_loop"
    assert invoke_config["metadata"] == {
        "agent": "talent_intelligence",
        "max_steps": 3,
    }
    assert invoke_config["tags"] == ["talent-intelligence", "tool-loop"]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))