# Task 22: Career Guidance Agent

Analyses one learner against one target career role, finds the competency gaps
between what the role expects and what the learner's evidence demonstrates, and
returns personalised, actionable recommendations. Every recommendation is a
`course`, a `task`, or a `project` — nothing else passes validation.

The agent performs no database reads or writes. It receives a profile, returns a
validated result, and makes no hiring judgement.

## Architecture

```
CareerGuidanceProfile
  -> RoleRegistry.resolve(target_role)           roles.py
  -> assess_competencies / identify_gaps         gap_analysis.py   (deterministic)
  -> build_deterministic_recommendations         recommendations.py (deterministic)
  -> optional RecommendationWriter (LLM)         agent.py + prompts.py
       -> parse_recommendation_payload           recommendations.py (JSON + schema)
       -> validate_grounding                     recommendations.py (gaps + evidence IDs)
  -> CareerGuidanceResult                        validated again on construction
```

| File | Responsibility |
|---|---|
| `src/app/schemas/career_guidance.py` | Pydantic v2 contracts, including `RecommendationCategory` |
| `src/app/agents/career_guidance/roles.py` | Competency library, role definitions, `RoleRegistry` |
| `src/app/agents/career_guidance/gap_analysis.py` | Evidence evaluation and gap detection |
| `src/app/agents/career_guidance/recommendations.py` | Category policy, consolidation, LLM output validation |
| `src/app/agents/career_guidance/prompts.py` | System prompt and prompt payload builder |
| `src/app/agents/career_guidance/agent.py` | `CareerGuidanceAgent` orchestration and `LLMRecommendationWriter` |
| `src/app/agents/career_guidance/__main__.py` | Command-line entry point |

**Separation of concerns.** Gap detection never uses an LLM. The LLM, when one
is injected, only words recommendations for gaps Python has already identified.
Its output must pass the same schema plus grounding checks, otherwise the
deterministic recommendations are returned.

**Reused infrastructure.**
- LLM calls go through the shared `generate_chat_completion` in
  `src/app/core/llm_client.py`.
- Configuration comes from `src/app/core/config.py` (`AI_API_KEY`,
  `AI_AGENT_URL`, `PRIMARY_MODEL`/`AI_MODEL`).
- Non-technical competencies are tagged with the team taxonomy from
  `src/app/core/tags.py`, and the registry rejects any tag that is not in it.

## Input contract — `CareerGuidanceProfile`

All models forbid unknown fields.

| Field | Type | Notes |
|---|---|---|
| `learner_id` | string, optional | |
| `target_role` | non-empty string | Resolved by id, title or alias, e.g. `AI Engineer`, `ML Engineer`, `Product Manager` |
| `skills` | list of `DemonstratedSkill` | `name`, optional `kind`, optional `level` (`beginner`→`expert`), `evidence_ids` |
| `behavioral_signals` | list of `BehavioralSignal` | `signal`, optional `competency`, `polarity` (`positive`/`concern`), `description`, `evidence_ids` |
| `evidence` | list of `EvidenceItem` | `evidence_id` (unique), `source_type` (`project`, `task`, `course`, `assessment`, `review`, `presentation`, `meeting`, `feedback`, `other`), `title`, `summary`, `competencies`, `tags`, `outcome`, `occurred_at` |

`EvidenceItem.competencies` names what an item specifically demonstrates.
`EvidenceItem.tags` holds the broad taxonomy tags from `core/tags.py`.

## Output contract — `CareerGuidanceResult`

| Field | Meaning |
|---|---|
| `role_id`, `role_title` | The resolved role |
| `profile_completeness` | `empty`, `limited` (fewer than 3 evidence items) or `substantial` |
| `assessments` | One `CompetencyAssessment` per role competency: `status`, `observed_level`, `supporting_evidence_ids`, `concern_evidence_ids`, `rationale` |
| `gaps` | `SkillGap` for every competency that is not demonstrated: `status`, `priority`, `gap_statement`, `evidence_basis`, `related_evidence_ids` |
| `recommendations` | `Recommendation`: `category`, `title`, `action`, `competencies`, `gap_summary`, `rationale`, `evidence_ids` |
| `generation_mode` | `deterministic`, `llm`, or `deterministic_fallback` |
| `warnings` | Explanations such as limited evidence or a rejected model response |

The result validates two invariants when it is built: every recommendation
targets identified gaps only, and no two recommendations share a category and
title.

## Recommendation categories

```python
class RecommendationCategory(str, Enum):
    COURSE = "course"
    TASK = "task"
    PROJECT = "project"
```

Any other value (`certification`, `workshop`, `internship`, `book`, `video`,
`mentorship`, `Course`, empty) raises a `ValidationError`, whether the value comes
from code, a role template, or an LLM response.

Deterministic category policy:

| Situation | Category |
|---|---|
| Non-technical gap | `task` — a focused, observable exercise |
| Technical gap two or more levels below the requirement | `course` |
| Other partially demonstrated technical gap | `task` |
| Technical gap with no evidence, learner already demonstrates other technical skills | `task` |
| Technical gap with no evidence and no demonstrated technical skills | `course` |
| Two or more technical `task` gaps | consolidated into one `project` (up to 3 competencies) |

Tasks reuse the learner's strongest successful work (the *anchor*) where the
template allows, e.g. "present *Document Q&A RAG prototype* to a non-technical
audience". Output is de-duplicated, ordered by gap priority, and capped at 6.

## Gap-analysis behaviour

Each role competency is matched against structured data only: evidence items
that name it (key, label or alias), skill entries, and behavioral signals. Free
text in summaries is never scanned, so "gave a great presentation" in a summary
is not treated as evidence of presenting.

| Status | Rule |
|---|---|
| `demonstrated` | At least two successful direct evidence items, **or** a skill at or above the required level that cites evidence; no concern signals; level not below requirement |
| `partially_demonstrated` | Something related exists, but it is a single item, below the required level, an unsuccessful outcome (`failed`, `retry`…), only a broad taxonomy tag, only a behavioral signal, or contradicted by a concern signal |
| `insufficient_evidence` | Nothing in the profile relates to the competency |

Priority: critical + insufficient → `high`; critical + partial or important +
insufficient → `medium`; important + partial → `low`.

## Evidence-first behaviour

- Missing evidence is never reported as inability. Insufficient gaps say
  *"Insufficient demonstrated evidence"* and their rationale states that this
  reflects missing evidence, not a proven lack of ability.
- Every rationale names the evidence IDs, skills or signals that produced it.
- **Empty profile:** every gap is `insufficient_evidence`, and the only
  recommendations are two baseline tasks for establishing evidence. No evidence
  IDs are cited, the LLM is not called, and a warning explains why.
- **Strong profile:** no gaps, no recommendations, and a warning saying no major
  gaps were found.
- **Limited profile:** normal analysis plus a warning that gaps may reflect
  missing records.

## LLM orchestration

`CareerGuidanceAgent(writer=...)` accepts any object with
`write(system_prompt, user_prompt) -> str`. `LLMRecommendationWriter.from_env()`
builds one on the shared LiteLLM client and raises `CareerGuidanceError` if
`AI_API_KEY`, `AI_AGENT_URL` or a model name is missing.

The prompt (`prompts.py`) provides the target role, competency assessments,
identified gaps, skills, behavioral signals, evidence, the deterministic draft,
the allowed categories, and the output contract. The system prompt enforces
evidence-first reasoning, technical and non-technical coverage, and the
three-category restriction.

Each attempt is validated in order:

| Check | Rejection reason |
|---|---|
| Blank or `None` response | `empty_response` |
| Not JSON (a surrounding ` ```json ` fence is allowed) | `invalid_json` |
| No `recommendations` object | `unexpected_structure` |
| Category outside course/task/project | `invalid_category` |
| Missing or invalid fields | `schema_validation` |
| Empty list | `empty_recommendations` |
| Targets a competency that is not a gap | `ungrounded_competency` |
| Cites an evidence ID not in the profile | `unknown_evidence` |
| Writer raised an exception | `model_request_failed` |

The agent retries up to `max_attempts` (default 2). If every attempt fails it
returns the deterministic recommendations with
`generation_mode="deterministic_fallback"` and a warning naming the reason code.
Provider error messages are never copied into the result. High-priority gaps the
model skipped are backfilled with deterministic recommendations, with a warning.

## Adding a career role

Add a `RoleDefinition` in `roles.py` built from `COMPETENCY_LIBRARY` entries
(with a role-specific importance and level), plus a `project` template, and
register it in `DEFAULT_ROLE_REGISTRY`. New competencies need a key, label, kind,
aliases, optional taxonomy tags from `core/tags.py`, and `course`/`task`
templates. The agent code does not change.

## Running locally

Deterministic (no API key needed):

```bash
docker compose run --rm --no-deps api python -m src.app.agents.career_guidance docs/examples/career_guidance_request.json
```

With the configured LLM (`AI_API_KEY`, `AI_AGENT_URL`, `PRIMARY_MODEL` in `.env`):

```bash
docker compose run --rm --no-deps api python -m src.app.agents.career_guidance docs/examples/career_guidance_request.json --llm
```

From Python:

```python
from src.app.agents.career_guidance import CareerGuidanceAgent, LLMRecommendationWriter

result = CareerGuidanceAgent().analyze({"target_role": "AI Engineer", "evidence": [...]})
llm_result = CareerGuidanceAgent(writer=LLMRecommendationWriter.from_env()).analyze(profile)
```

## Tests

```bash
docker compose run --rm --no-deps api pytest tests/test_career_guidance_agent.py
```

The suite is fully offline; every LLM call is a mock. It covers the schema (all
three categories accepted, others rejected, malformed data), each gap status,
the technically strong learner with missing presentation, collaboration and
feedback evidence, empty, limited and strong profiles, the category policy and
consolidation, prompt contents, every malformed-response reason code, retries,
exception containment, backfilling, and the CLI.

## Example

Input: [`docs/examples/career_guidance_request.json`](examples/career_guidance_request.json).
The learner has strong RAG, API and ML evidence, no presentation evidence, a
partly evidenced collaboration signal, and a concern about applying review
feedback.

Excerpt of the real deterministic output (15 assessments, 12 gaps, 6
recommendations):

```json
{
  "role_id": "ai_engineer",
  "profile_completeness": "substantial",
  "generation_mode": "deterministic",
  "gaps": [
    {
      "competency_key": "technical_presentation",
      "kind": "non_technical",
      "status": "insufficient_evidence",
      "priority": "high",
      "gap_statement": "Insufficient demonstrated evidence for presenting technical work, which an AI Engineer is expected to show at intermediate level.",
      "evidence_basis": "Insufficient evidence: nothing in the profile relates to Presenting technical work. This reflects missing evidence, not a proven lack of ability."
    }
  ],
  "recommendations": [
    {
      "category": "task",
      "title": "Present one of your projects to a non-technical audience",
      "action": "Prepare and deliver a 10-minute presentation explaining 'Document Q&A RAG prototype' to a non-technical audience, then collect written feedback on clarity from at least two listeners.",
      "competencies": ["technical_presentation"],
      "rationale": "The profile shows completed work such as 'Document Q&A RAG prototype' (ev-rag-project) but no evidence of presenting technical work. Missing evidence is not proof of inability; this task creates that evidence by building on work already done.",
      "evidence_ids": ["ev-rag-project"]
    },
    {
      "category": "project",
      "title": "Build an end-to-end portfolio project",
      "competencies": ["software_engineering", "sql", "data_analysis"],
      "rationale": "3 technical competencies (software engineering practices, SQL and relational data, data analysis) are not yet demonstrated by the profile's evidence. One integrated project produces reviewable evidence for all of them instead of several disconnected exercises.",
      "evidence_ids": ["ev-api-review"]
    }
  ]
}
```

The remaining recommendations are tasks for system design, collaboration,
applying feedback, and documentation.

## Limitations

- Two role frameworks ship today (AI Engineer, Product Manager); other roles
  raise `UnknownRoleError` until a `RoleDefinition` is added.
- Matching uses competency keys, labels and aliases, so evidence must name
  competencies in `EvidenceItem.competencies` or carry a taxonomy tag. Summaries
  are deliberately not interpreted.
- Required levels and importance are expert judgement encoded in `roles.py`, not
  derived from labour-market data.
- Adapting graph memory cards or profile metrics into `CareerGuidanceProfile` is
  left to the caller. The agent is not wired into an API route yet.
- Live LLM behaviour has not been exercised in tests; all LLM paths are mocked.
