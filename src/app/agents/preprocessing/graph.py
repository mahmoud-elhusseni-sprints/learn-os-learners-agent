from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .lms_memory_card_agent import LMSMemoryCardAgent
from .mentor_metric_agent import MentorMetricAgent


class PreprocessingState(TypedDict, total=False):
    configs_filepath: str
    logs_filepath: str
    catalog_filepath: str
    cards_per_learner: int
    cards_map: Dict[str, List[Dict[str, Any]]]
    metrics_map: Dict[str, Dict[str, Any]]


def lms_card_node(state: PreprocessingState) -> Dict[str, Any]:
    agent = LMSMemoryCardAgent(state["catalog_filepath"])
    cards_map = agent.generate_memory_cards_map(
        configs_filepath=state["configs_filepath"],
        logs_filepath=state["logs_filepath"],
        cards_per_learner=state.get("cards_per_learner", 15),
    )
    return {"cards_map": cards_map}


def mentor_metric_node(state: PreprocessingState) -> Dict[str, Any]:
    agent = MentorMetricAgent()
    metrics_map = agent.evaluate_mentor_metrics_map(
        configs_filepath=state["configs_filepath"],
        logs_filepath=state["logs_filepath"],
    )
    return {"metrics_map": metrics_map}


_builder: StateGraph = StateGraph(PreprocessingState)

_builder.add_node("lms_card_node", lms_card_node)
_builder.add_node("mentor_metric_node", mentor_metric_node)

_builder.add_edge(START, "lms_card_node")
_builder.add_edge(START, "mentor_metric_node")

_builder.add_edge("lms_card_node", END)
_builder.add_edge("mentor_metric_node", END)

preprocessing_graph = _builder.compile()
