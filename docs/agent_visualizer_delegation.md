# Task 19: Employer-to-Visualizer delegation

Use `TalentIntelligenceAgent.respond_structured(query, learner_name_or_id,
visual_options)` for the agent-level contract. Existing `respond()` and
`respond_with_gemini()` still return strings; Task 20's owner can adopt the new
method without a breaking change. No FastAPI, persistence, or frontend changes
are included.

The existing LangGraph investigation runs first. Successful current-turn graph
retrieval results are copied into a private evidence buffer. Failed tools,
model-written numbers, and previous-turn evidence are not chart inputs. Visual
intent is conservatively detected in Python; the employer prompt tells the model
to retrieve relevant evidence and finish its factual answer independently.

Supported visuals are Task 15's SVG, HTML and PNG bar charts of **distinct
retrieved evidence counts by source**. They are not skill ratings, candidate
rankings, comprehensive histories, or measurements of progress. Duplicate IDs
count once; conflicting duplicate IDs cause fallback. Missing citation fields
are excluded. Timeline/trajectory/pie requests return an unsupported notice.
Intent matching currently supports English chart/visual/comparison keywords;
simple factual queries and explicit text-only requests do not invoke rendering.

The request uses existing `VisualizationRequest` and `Theme` schemas from
`src.app.schemas.models`, serialized and validated through JSON before calling
`VisualizerAgent.visualize()`. No conceptual-image generation API is called.

## Response contract for Task 20

`EmployerResponse` in `src.app.schemas.agent_response` contains:

- `markdown`: the original factual answer, unchanged.
- `artifacts`: zero or more objects with `format`, `data`, `encoding`,
  `commentary`, and supporting `evidence` (IDs, sources, dates, observations).
- `fallback`: null, or `{code, notice}` for unsupported, insufficient evidence,
  timeout, rendering error, or exhausted rendering capacity.

Serialize with `response.model_dump(mode="json")` or `model_dump_json()`.
SVG/HTML data is text. PNG data is standard base64, explicitly labeled.
There are no hosted URLs or local filesystem paths. The API/frontend owners
handle persistence and presentation: show markdown even with a fallback, display
the notice, and sandbox/sanitize HTML/SVG rather than injecting arbitrary markup
into the chat page. Serve PNG as image/png after base64 decoding.

## Timeout and resource isolation

`VISUALIZER_TIMEOUT_SECONDS` defaults to 2 seconds and must be positive/finite.
This guards only visualization, not upstream investigation/LLM execution.
The caller stops waiting at the deadline; no delayed artifact channel exists.
Python cannot forcibly stop a running thread safely, so a timed-out daemon thread
may finish in the background and its result is discarded. A global two-slot
semaphore bounds outstanding rendering work. Once both slots are occupied, new
requests immediately return a busy fallback. Slots release when rendering ends.
Permanent renderer hangs require process restart; a future process-based renderer
could provide hard cancellation. Do not share a stateful agent instance between
concurrent conversations.

## Validation

```sh
pytest tests/test_visual_delegation.py tests/test_visualizer_agent.py -q
```

Tests use the real deterministic renderer, synthetic evidence, mocked model/tool
execution, and a blocking renderer to verify timeout latency. No API keys, live
learner data or image generation charges are needed.

Validation on this branch: 60 delegation/visualizer tests passed; Ruff, Black,
and MyPy passed. A broader run reached 176 passes and three failures in existing
`tests/unit/test_graph_helpers.py` routing assertions before it was interrupted
while waiting on a live model call. Those tests mock tool functions but not the
current model loop; the full suite is not claimed green.
# Conversation history integration

The chat adapter passes persisted `user`/`assistant` messages as a structured
list to `respond_structured(history=...)`. The LangGraph input preserves those
roles and appends the current question once. History supplies conversational
context, not verified evidence. Other history roles are rejected. Legacy string
history remains accepted as a single user-context message.

An explicit history list (including an empty list) resets local learner/turn
state so a reused adapter cannot carry another conversation's context forward.
Direct `respond()` calls without persisted history use their local prior turns.
Visual intent is evaluated only on the current question. Charts still require
successful retrieval records from the current turn.

Offline integration checks: `pytest tests/test_talent_history.py
tests/test_agent_orchestration.py tests/test_visual_delegation.py
tests/test_visualizer_agent.py`. These use a fake LLM/retrieval boundary with the
real LangGraph and chart renderer; they do not certify live LLM behavior or the
frontend. The frontend must map `ChatResponse.message` and
`ChatResponse.response.artifacts`; frontend changes are outside this patch.
