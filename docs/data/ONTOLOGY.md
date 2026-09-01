# Professional Learner Graph - Ontology Reference

- ontology version: `0.1.0`
- schema version: `learner-graph/0.1.0`
- node labels: **25**
- relationship types: **42** across **52** legal endpoint pairs

> **Generated file.** Produced by `generate_docs.py` from
> `learner_graph_models.py`. Edit the models and regenerate.

Node kinds:

| kind | meaning | carries |
|---|---|---|
| `source` | mirrors a record that exists in a source system | `provenance` (required) |
| `derived` | a computed opinion the platform produced | `computed_at`, `computed_by` |
| `registry` | a taxonomy entry owned by the platform | neither |

---

## 1. Node types

### Organisational scope

The containers employer authorisation is scoped against (FR-05).

#### `Cohort`  (source)

A programme intake, e.g. 'sprints-2026-spring'.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `cohort_key` | `str` | yes |  |
| `name` | `str` | yes |  |
| `start_date` | `datetime (UTC) \| None` | no |  |
| `end_date` | `datetime (UTC) \| None` | no |  |
| `duration_weeks` | `int \| None` | no |  |
| `organization_id` | `str \| None` | no |  |

#### `Round`  (source)

An internship round, e.g. 'round2'.  Employer authorisation is scoped
at this level (FR-05), which is why it must be a first-class node.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `round_key` | `str` | yes |  |
| `name` | `str` | yes |  |

#### `Group`  (source)

A track/group inside a round, e.g. 'G2 - AI Engineer Internship'.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `group_key` | `str` | yes |  |
| `name` | `str` | yes |  |
| `track` | `str \| None` | no | e.g. 'AI Engineer' |

---

### Identity

One canonical person, plus every source identity that resolves to them.

#### `Learner`  (source)

The canonical person.  One Learner node per real human, however many
source identities point at them.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `canonical_email` | `str` | yes |  |
| `display_name` | `str` | yes |  |
| `timezone` | `str \| None` | no |  |
| `learner_status` | `str \| None` | no |  |
| `sensitive_attributes` | `dict[str, str]` | no | Optional profile context (location, education level, field of study). PRD 8.2: these ar... |

#### `LearnerIdentity`  (source)

One source-system identity that maps onto a canonical Learner.

Task 4 (identity resolution) owns this node.  Modelling it explicitly is
what lets US-01 ("all source IDs resolved to one canonical profile") be
satisfied *without losing the source mappings*, and gives the unresolved
queue somewhere to live.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `source_learner_id` | `str` | yes |  |
| `source_email` | `str \| None` | no |  |
| `source_display_name` | `str \| None` | no |  |
| `resolution_status` | `IdentityResolutionStatus` | no |  |
| `resolution_method` | `str \| None` | no | e.g. 'exact_email', 'manual_merge' |
| `resolved_at` | `datetime (UTC) \| None` | no |  |
| `merge_note` | `str \| None` | no |  |

---

### Skills

The canonical skill registry; aliases collapse surface forms onto one node.

#### `Skill`  (registry)

A canonical skill.  Not a SourceNode: skills are registry entries owned
by the taxonomy, not records copied from one system.  Aliases collapse the
many surface forms ('Python 3.11', 'python', 'Python') onto one node.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `canonical_name` | `str` | yes |  |
| `slug` | `str` | yes |  |
| `category` | `SkillCategory` | yes |  |
| `aliases` | `list[str]` | no |  |
| `description` | `str \| None` | no |  |
| `taxonomy_version` | `str` | no |  |

---

### Work and learning

What was assigned, what was handed in, and the files inside it.

#### `Project`  (source)

A body of work several tasks contribute to.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `project_key` | `str` | yes |  |
| `name` | `str` | yes |  |
| `description` | `str \| None` | no |  |
| `repository_url` | `str \| None` | no |  |

#### `TaskDefinition`  (source)

The reusable specification of a task.

Distinct from LearningExperience: in the real export one
``task_definition_id`` is handed to several learners.  Collapsing the two
would destroy the difference between 'the task' and 'her attempt at it'.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `task_definition_key` | `str` | yes |  |
| `headline` | `str` | yes |  |
| `description` | `str \| None` | no |  |
| `task_archetype` | `str \| None` | no | e.g. 'single_submission' |
| `technologies` | `list[str]` | no |  |
| `deliverable_format` | `str \| None` | no |  |
| `functional_requirements` | `list[str]` | no |  |
| `non_functional_requirements` | `list[str]` | no |  |
| `sprint_label` | `str \| None` | no |  |

#### `LearningExperience`  (source)

One task instance assigned to one learner (an 'LX' in the source data).

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `lx_key` | `str` | yes |  |
| `flow_id` | `str \| None` | no |  |
| `task_archetype_id` | `str \| None` | no |  |
| `status` | `LXStatus` | yes |  |
| `outcome` | `LXOutcome \| None` | no |  |
| `trial_count` | `int` | no |  |
| `extension_used` | `bool` | no |  |
| `activated_at` | `datetime (UTC) \| None` | no |  |
| `deadline_at` | `datetime (UTC) \| None` | no |  |
| `terminated_at` | `datetime (UTC) \| None` | no |  |
| `terminated_reason` | `str \| None` | no |  |
| `scenario_key` | `str \| None` | no |  |
| `revision` | `int \| None` | no |  |

#### `Attempt`  (source)

One graded attempt at an LX.  ``trial_count`` in the source data and the
``attempt_failed_retry`` / ``attempt_passed`` tags make this a real entity:
Learner A4's LX 144bd399 has three attempts with different verdicts.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `attempt_number` | `int` | yes |  |
| `verdict` | `AttemptVerdict` | yes |  |
| `submitted_at` | `datetime (UTC) \| None` | no |  |
| `evaluated_at` | `datetime (UTC) \| None` | no |  |

#### `Submission`  (source)

What the learner handed in.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `kind` | `str` | yes | e.g. 'attachments', 'text', 'link' |
| `text` | `str \| None` | no |  |
| `attachment_count` | `int` | no |  |
| `submission_url` | `str \| None` | no |  |

#### `Artifact`  (source)

A concrete file/chunk inside a submission.

The grader cites these by id (``'backend/app/services/script_agent.py_0'``),
so they are the finest-grained provenance anchor available and make
'show me the evidence' land on an actual line of work.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `artifact_key` | `str` | yes |  |
| `path` | `str \| None` | no |  |
| `artifact_type` | `str \| None` | no | e.g. 'code', 'readme', 'diff' |
| `content_excerpt` | `str \| None` | no |  |

---

### Assessment

How work was graded, down to the individual rubric point.

#### `Rubric`  (source)

A node that mirrors something that actually happened in a source system.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `rubric_key` | `str` | yes |  |
| `version` | `str` | no |  |
| `criterion_count` | `int` | no |  |

#### `RubricCriterion`  (source)

One scope/point pair from the task rubric.  This is where a skill gets
attached to an assessable requirement, so it is the hinge between
'work delivered' and 'skill demonstrated'.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `criterion_key` | `str` | yes |  |
| `scope_id` | `int \| None` | no |  |
| `point_id` | `int \| None` | no |  |
| `category` | `str \| None` | no |  |
| `polarity` | `str \| None` | no | 'positive' or 'negative' |
| `requirement` | `str \| None` | no |  |
| `description` | `str \| None` | no |  |
| `evaluation_criteria` | `str \| None` | no |  |

#### `Assessment`  (source)

One evaluation event - a grader call, quiz submission or coding test.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `assessment_kind` | `str` | yes | e.g. 'grader_call', 'quiz', 'coding_challenge' |
| `verdict` | `str \| None` | no |  |
| `summary` | `str \| None` | no |  |
| `score` | `float \| None` | no |  |
| `max_score` | `float \| None` | no |  |
| `grader_version` | `str \| None` | no |  |
| `evaluated_at` | `datetime (UTC) \| None` | no |  |

---

### Meetings and interactions

Where behavioural signal comes from.

#### `Meeting`  (source)

A node that mirrors something that actually happened in a source system.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `meeting_key` | `str` | yes |  |
| `kind` | `MeetingKind` | yes |  |
| `topic` | `str \| None` | no |  |
| `starts_at_utc` | `datetime (UTC) \| None` | no |  |
| `duration_min` | `int \| None` | no |  |
| `zoom_meeting_id` | `str \| None` | no |  |
| `extraction_status` | `str \| None` | no |  |

#### `Interaction`  (source)

One entry from the interaction log - a chat exchange, kickoff brief,
daily check-in, redirect, etc.  Covers the brief's 'Interaction/Chat'.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `interaction_kind` | `InteractionKind` | yes |  |
| `tags` | `list[str]` | no |  |
| `summary` | `str \| None` | no |  |
| `trigger_node_id` | `str \| None` | no |  |
| `occurred_at` | `datetime (UTC)` | yes |  |
| `message_count` | `int` | no |  |
| `participant_roles` | `list[str]` | no | e.g. ['learner', 'mentor'] |
| `struggle_area` | `str \| None` | no |  |
| `struggle_resolved` | `bool \| None` | no |  |

---

### Evidence

The centre of the ontology: atomic, citable, provenance-carrying proof.

#### `Evidence`  (source)

An atomic, citable piece of proof about a learner.

Every Evidence node must point back at the record it came from
(``DERIVED_FROM``) and at the learner it concerns
(``EVIDENCE_FOR_LEARNER``).  Both are enforced structurally by
``LearnerGraph`` rather than left to convention.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `evidence_type` | `EvidenceType` | yes |  |
| `strength` | `EvidenceStrength` | yes |  |
| `confidence` | `float` | no |  |
| `title` | `str` | yes |  |
| `content` | `str` | yes | The quotable substance - grader reason, feedback line, meeting excerpt. |
| `observed_at` | `datetime (UTC)` | yes | When the evidenced behaviour occurred (drives recency weighting). |
| `access_scope` | `AccessScope` | no |  |
| `criterion_status` | `CriterionStatus \| None` | no | Set when the evidence came from a graded rubric point. |

---

### Derived state

Computed opinions. Versioned, recomputable, never overwriting source truth.

#### `SkillAssertion`  (derived)

The derived, evidence-backed state of one learner-skill-tier triple.

This node is the reason the product can answer "we don't know" honestly:
``status = NO_EVIDENCE`` is storable, queryable and actionable, and it is
what Epic 3 turns into a validation scenario.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `computed_at` | `datetime (UTC)` | yes |  |
| `computed_by` | `str` | yes | Versioned producer, e.g. 'skill-aggregator@0.1.0' |
| `derivation_note` | `str \| None` | no |  |
| `tier` | `SkillEvidenceTier` | yes |  |
| `status` | `AssertionStatus` | yes |  |
| `confidence` | `float` | no |  |
| `evidence_count` | `int` | no |  |
| `evidence_source_count` | `int` | no | Distinct source_systems behind this assertion - the diversity signal that stops one cha... |
| `first_evidence_at` | `datetime (UTC) \| None` | no |  |
| `latest_evidence_at` | `datetime (UTC) \| None` | no |  |
| `rationale` | `str \| None` | no |  |

#### `Observation`  (derived)

A contextual behavioural observation.

PRD 4.3 / 8.2: store *event + behaviour + outcome + source + confidence*,
never a personality label.  The validator below is a guardrail that makes
the policy enforceable in code instead of a line in a doc.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `computed_at` | `datetime (UTC)` | yes |  |
| `computed_by` | `str` | yes | Versioned producer, e.g. 'skill-aggregator@0.1.0' |
| `derivation_note` | `str \| None` | no |  |
| `category` | `ObservationCategory` | yes |  |
| `context` | `str` | yes | The situation, e.g. 'company API went down mid-task' |
| `behavior` | `str` | yes | What the learner did, observably |
| `outcome` | `str \| None` | no | What resulted |
| `observed_at` | `datetime (UTC)` | yes |  |
| `confidence` | `float` | no |  |

---

### Career goal and closed loop

Sprint 4 surface. CareerGoal is P0 now; Scenario/Recommendation are stubs.

#### `CareerGoal`  (source)

FR-11 (P0): every pilot learner has a goal or an explicit unknown state.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `status` | `CareerGoalStatus` | yes |  |
| `target_role` | `str \| None` | no |  |
| `stated_at` | `datetime (UTC) \| None` | no |  |
| `notes` | `str \| None` | no |  |

#### `Scenario`  (source)

Approved practice/validation scenario (Sprint 4 catalog).

Included now as a stub so Sprint 4 extends the ontology instead of
migrating it.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `scenario_key` | `str` | yes |  |
| `title` | `str` | yes |  |
| `description` | `str \| None` | no |  |
| `difficulty` | `str \| None` | no |  |
| `estimated_minutes` | `int \| None` | no |  |
| `task_type` | `str \| None` | no |  |
| `version` | `str` | no |  |
| `approved` | `bool` | no |  |

#### `Recommendation`  (derived)

A gap-driven recommendation (Sprint 4 stub).

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `computed_at` | `datetime (UTC)` | yes |  |
| `computed_by` | `str` | yes | Versioned producer, e.g. 'skill-aggregator@0.1.0' |
| `derivation_note` | `str \| None` | no |  |
| `gap_type` | `GapType` | yes |  |
| `reason` | `str` | yes | The profile signal that triggered this |
| `priority` | `int` | yes |  |
| `status` | `RecommendationStatus` | no |  |
| `expected_evidence` | `str \| None` | no |  |

---

### Employer access

Deny-by-default authorisation. Enforced in Sprint 2; fields exist now.

#### `Employer`  (source)

A node that mirrors something that actually happened in a source system.

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `employer_key` | `str` | yes |  |
| `name` | `str` | yes |  |

#### `AccessGrant`  (source)

Deny-by-default authorisation record (FR-05).

| property | type | required | notes |
|---|---|---|---|
| `id` | `UUID` | yes |  |
| `created_at` | `datetime (UTC)` | yes |  |
| `updated_at` | `datetime (UTC) \| None` | no |  |
| `provenance` | `Provenance` | yes |  |
| `grant_key` | `str` | yes |  |
| `granted_at` | `datetime (UTC)` | yes |  |
| `expires_at` | `datetime (UTC) \| None` | no |  |
| `allowed_evidence_types` | `list[EvidenceType]` | no |  |
| `allowed_access_scopes` | `list[AccessScope]` | no |  |

---

## 2. Relationships

Every relationship below is registered in `EDGE_SPECS`. An edge whose
`(type, source, target)` triple is not in this table is **rejected at
validation time** - this is what stops the ingestion, identity and API
workstreams from inventing divergent edges.

Cardinality is read left-to-right:

| notation | meaning |
|---|---|
| `1:1` | each source has at most one target, and vice versa |
| `1:N` | one source, many targets; each target has one source |
| `N:1` | many sources, one target; each source has one target |
| `N:M` | unconstrained both ways |

| relationship | cardinality | properties | meaning |
|---|---|---|---|
| `(:SkillAssertion)-[:ABOUT_SKILL]->(:Skill)` | `N:1` | - | Which skill the assertion concerns. |
| `(:Recommendation)-[:ADDRESSES_GAP_IN]->(:Skill)` | `N:M` | - | Skill the gap concerns. |
| `(:Learner)-[:ASSESSED_ON_SKILL]->(:Skill)` | `N:M` | `SkillTierProps` | Tier 3: scored against a rubric. |
| `(:Learner)-[:COMPLETED_TASK]->(:TaskDefinition)` | `N:M` | `CompletedTaskProps` | Denormalised completion edge for fast history queries. |
| `(:Submission)-[:CONTAINS_ARTIFACT]->(:Artifact)` | `1:N` | - | Files/chunks inside a submission. |
| `(:Learner)-[:DECLARED_SKILL]->(:Skill)` | `N:M` | `SkillTierProps` | Tier 1: self-declared. |
| `(:Learner)-[:DEMONSTRATED_SKILL]->(:Skill)` | `N:M` | `SkillTierProps` | Tier 4: shipped working artifacts. |
| `(:Evidence)-[:DERIVED_FROM]->(:Assessment)` | `N:1` | - | Evidence traced to an assessment. |
| `(:Evidence)-[:DERIVED_FROM]->(:Submission)` | `N:1` | - | Evidence traced to a submission. |
| `(:Evidence)-[:DERIVED_FROM]->(:Artifact)` | `N:M` | - | Evidence traced to a file/chunk. |
| `(:Evidence)-[:DERIVED_FROM]->(:Interaction)` | `N:1` | - | Evidence traced to a chat exchange. |
| `(:Evidence)-[:DERIVED_FROM]->(:Meeting)` | `N:1` | - | Evidence traced to a meeting. |
| `(:Evidence)-[:DERIVED_FROM]->(:RubricCriterion)` | `N:1` | - | Evidence traced to a rubric point. |
| `(:Evidence)-[:DERIVED_FROM]->(:LearningExperience)` | `N:1` | - | Evidence traced to a task instance. |
| `(:Attempt)-[:EVALUATED_BY]->(:Assessment)` | `1:N` | - | Assessment run over an attempt. |
| `(:Evidence)-[:EVIDENCE_ABOUT_SKILL]->(:Skill)` | `N:M` | - | Which skill this evidence speaks to. |
| `(:Evidence)-[:EVIDENCE_FOR_LEARNER]->(:Learner)` | `N:1` | - | Every evidence item is about exactly one learner. |
| `(:Learner)-[:EXPOSED_TO_SKILL]->(:Skill)` | `N:M` | `SkillTierProps` | Tier 2: learning exposure. |
| `(:CareerGoal)-[:GOAL_TARGETS_SKILL]->(:Skill)` | `N:M` | - | Target competency for the goal. |
| `(:AccessGrant)-[:GRANTS_ACCESS_TO]->(:Round)` | `N:M` | - | Rounds the grant unlocks. |
| `(:Employer)-[:HAS_ACCESS_GRANT]->(:AccessGrant)` | `1:N` | - | Grants held by an employer. |
| `(:LearningExperience)-[:HAS_ATTEMPT]->(:Attempt)` | `1:N` | - | Graded attempts, in order. |
| `(:Learner)-[:HAS_CAREER_GOAL]->(:CareerGoal)` | `1:1` | - | Current career goal or unknown state. |
| `(:Rubric)-[:HAS_CRITERION]->(:RubricCriterion)` | `1:N` | - | Rubric's scope/point criteria. |
| `(:Learner)-[:HAS_LEARNING_EXPERIENCE]->(:LearningExperience)` | `1:N` | - | A task instance assigned to this learner. |
| `(:Learner)-[:HAS_OBSERVATION]->(:Observation)` | `1:N` | - | Behavioural observations. |
| `(:TaskDefinition)-[:HAS_RUBRIC]->(:Rubric)` | `N:1` | - | Task is graded by this rubric. |
| `(:Learner)-[:HAS_SKILL_ASSERTION]->(:SkillAssertion)` | `1:N` | - | Learner's derived skill states. |
| `(:Meeting)-[:HELD_FOR_GROUP]->(:Group)` | `N:1` | - | Meeting belongs to a group. |
| `(:LearnerIdentity)-[:IDENTIFIES]->(:Learner)` | `N:1` | - | A source-system identity resolves to one canonical learner. |
| `(:LearningExperience)-[:INSTANCE_OF]->(:TaskDefinition)` | `N:1` | - | Which task specification this instance realises. |
| `(:Learner)-[:MEMBER_OF]->(:Group)` | `N:M` | `MembershipProps` | Learner belongs to a track/group. |
| `(:Observation)-[:OBSERVED_IN]->(:Meeting)` | `N:1` | - | Context: a meeting. |
| `(:Observation)-[:OBSERVED_IN]->(:Interaction)` | `N:1` | - | Context: an interaction. |
| `(:Observation)-[:OBSERVED_IN]->(:LearningExperience)` | `N:1` | - | Context: a task instance. |
| `(:Interaction)-[:OCCURRED_IN]->(:LearningExperience)` | `N:1` | - | Interaction happened inside a task instance. |
| `(:Learner)-[:PARTICIPATED_IN]->(:Meeting)` | `N:M` | `ParticipationProps` | Learner attended a meeting. |
| `(:Learner)-[:PARTICIPATED_IN]->(:Interaction)` | `N:M` | `ParticipationProps` | Learner took part in an exchange. |
| `(:Round)-[:PART_OF_COHORT]->(:Cohort)` | `N:1` | - | Round belongs to a cohort. |
| `(:TaskDefinition)-[:PART_OF_PROJECT]->(:Project)` | `N:1` | - | Task contributes to a project. |
| `(:Group)-[:PART_OF_ROUND]->(:Round)` | `N:1` | - | Group sits inside a round. |
| `(:Recommendation)-[:RECOMMENDED_FOR]->(:Learner)` | `N:1` | - | Who the recommendation is for. |
| `(:Recommendation)-[:RECOMMENDS_SCENARIO]->(:Scenario)` | `N:1` | - | Catalog scenario proposed. |
| `(:TaskDefinition)-[:REQUIRES_SKILL]->(:Skill)` | `N:M` | - | Skill the task exercises. |
| `(:Assessment)-[:SCORED_CRITERION]->(:RubricCriterion)` | `N:M` | `ScoredCriterionProps` | Per-point grader result with confidence and artifact citations. |
| `(:Learner)-[:SUBMITTED]->(:Submission)` | `1:N` | - | Learner handed this in. |
| `(:Submission)-[:SUBMITTED_IN]->(:Attempt)` | `N:1` | - | Submission belongs to an attempt. |
| `(:Observation)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)` | `N:M` | - | The evidence backing a behavioural observation. |
| `(:SkillAssertion)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)` | `N:M` | - | The evidence backing a derived skill claim. |
| `(:RubricCriterion)-[:TARGETS_SKILL]->(:Skill)` | `N:M` | - | The criterion measures this skill - the hinge from work to skill. |
| `(:Assessment)-[:USED_RUBRIC]->(:Rubric)` | `N:1` | - | Rubric the assessment applied. |
| `(:Scenario)-[:VALIDATES_SKILL]->(:Skill)` | `N:M` | - | What the scenario can prove. |

### Relationship property payloads

#### `CompletedTaskProps`

Denormalised summary of how a learner finished a task definition.

| property | type | required |
|---|---|---|
| `lx_key` | `str` | yes |
| `outcome` | `LXOutcome \| None` | no |
| `completed_at` | `datetime (UTC) \| None` | no |
| `attempts` | `int` | no |

#### `MembershipProps`

Shared config.  ``extra='forbid'`` is deliberate: a typo in an ingestion
script should fail loudly at write time rather than silently create an
orphan property in Neo4j.

| property | type | required |
|---|---|---|
| `role` | `str` | no |
| `added_at` | `datetime (UTC) \| None` | no |

#### `ParticipationProps`

Shared config.  ``extra='forbid'`` is deliberate: a typo in an ingestion
script should fail loudly at write time rather than silently create an
orphan property in Neo4j.

| property | type | required |
|---|---|---|
| `attendance` | `str` | no |
| `role` | `str` | no |

#### `ScoredCriterionProps`

The grader's per-rubric-point result, kept at full fidelity.

| property | type | required |
|---|---|---|
| `status` | `CriterionStatus` | yes |
| `confidence` | `float` | yes |
| `reason` | `str \| None` | no |
| `artifact_keys` | `list[str]` | no |

#### `SkillTierProps`

Carried on the four denormalised learner->skill convenience edges.

These edges exist for fast Cypher in Epic 2/3; the SkillAssertion node
remains the authoritative, versioned record.

| property | type | required |
|---|---|---|
| `assertion_id` | `UUID` | yes |
| `status` | `AssertionStatus` | yes |
| `confidence` | `float` | no |
| `evidence_count` | `int` | no |
| `latest_evidence_at` | `datetime (UTC) \| None` | no |

---

## 3. Controlled vocabularies

Values follow the source export wherever one already exists, so ingestion
never has to translate between two vocabularies.

**`AccessScope`** - Coarse visibility band stamped on every Evidence item (FR-03).

  `internal_only`, `employer_shareable`, `learner_visible`, `restricted`

**`AssertionStatus`** - Evidence-strength state of a derived skill claim.

  `no_evidence`, `weak`, `moderate`, `strong`

**`AttemptVerdict`** - str(object='') -> str

  `passed`, `failed_retry`, `failed_final`, `pending`

**`Cardinality`** - str(object='') -> str

  `1:1`, `1:N`, `N:1`, `N:M`

**`CareerGoalStatus`** - str(object='') -> str

  `stated`, `unknown`

**`CriterionStatus`** - Per-rubric-point grader outcome as emitted in the real feedback payload.

  `Yes`, `Partial`, `No`

**`EdgeType`** - str(object='') -> str

  `IDENTIFIES`, `MEMBER_OF`, `PART_OF_ROUND`, `PART_OF_COHORT`, `HAS_LEARNING_EXPERIENCE`, `INSTANCE_OF`, `COMPLETED_TASK`, `PART_OF_PROJECT`, `HAS_ATTEMPT`, `SUBMITTED`, `SUBMITTED_IN`, `CONTAINS_ARTIFACT`, `HAS_RUBRIC`, `HAS_CRITERION`, `EVALUATED_BY`, `USED_RUBRIC`, `SCORED_CRITERION`, `TARGETS_SKILL`, `REQUIRES_SKILL`, `PARTICIPATED_IN`, `HELD_FOR_GROUP`, `OCCURRED_IN`, `EVIDENCE_FOR_LEARNER`, `DERIVED_FROM`, `SUPPORTED_BY_EVIDENCE`, `EVIDENCE_ABOUT_SKILL`, `HAS_SKILL_ASSERTION`, `ABOUT_SKILL`, `DECLARED_SKILL`, `EXPOSED_TO_SKILL`, `ASSESSED_ON_SKILL`, `DEMONSTRATED_SKILL`, `HAS_OBSERVATION`, `OBSERVED_IN`, `HAS_CAREER_GOAL`, `GOAL_TARGETS_SKILL`, `RECOMMENDED_FOR`, `RECOMMENDS_SCENARIO`, `ADDRESSES_GAP_IN`, `VALIDATES_SKILL`, `HAS_ACCESS_GRANT`, `GRANTS_ACCESS_TO`

**`EvidenceStrength`** - Typical strength band from PRD 4.4.  Set per evidence item, not per type,

  `high`, `medium_high`, `medium`, `low`

**`EvidenceType`** - PRD 4.4 evidence classes.

  `direct_assessment`, `delivered_work`, `observed_behavior`, `mentor_feedback`, `learning_exposure`, `self_declared`

**`ExtractionMethod`** - How a record got into the graph - drives how much we trust it.

  `direct_mapping`, `rule_based`, `llm_extraction`, `human_curated`

**`GapType`** - str(object='') -> str

  `skill_gap`, `evidence_gap`, `behavioral_evidence_gap`, `recency_gap`, `career_goal_gap`

**`IdentityResolutionStatus`** - str(object='') -> str

  `resolved`, `unresolved`, `conflict`

**`InteractionKind`** - str(object='') -> str

  `learner_message`, `actor_response`, `human_mentor_message`, `task_kickoff`, `daily_check`, `learner_submission`, `feedback_delivered`, `deadline_reminder`, `misrouted_redirect`, `scenario_event`, `other`

**`LXOutcome`** - str(object='') -> str

  `completed_success`, `completed_failed`, `expired`, `abandoned`

**`LXStatus`** - str(object='') -> str

  `active`, `terminated`

**`MeetingKind`** - str(object='') -> str

  `sprint_planning`, `standup`, `retro`, `ad_hoc`

**`ObservationCategory`** - Behavioural observation buckets, aligned with the memory-card metric keys.

  `collaboration`, `problem_solving`, `deadline_handling`, `communication`, `initiative`, `adaptability`, `help_seeking`

**`RecommendationStatus`** - str(object='') -> str

  `recommended`, `approved`, `assigned`, `in_progress`, `submitted`, `evaluated`, `evidence_ingested`

**`SkillCategory`** - Mirrors the rubric ``scopes[].category`` values in the real export.

  `digital_ai_skills`, `work_skills`, `soft_skills`, `knowledge_state`, `mistake_patterns`, `domain_specific`

**`SkillEvidenceTier`** - PRD 4.3: 'Separate declared, exposed, assessed and demonstrated'.

  `declared`, `exposed`, `assessed`, `demonstrated`

**`SourceSystem`** - Systems that can write into the graph.

  `lms`, `virtual_internship`, `assessment_engine`, `meetings`, `meeting_memory`, `profile`, `scenario_engine`, `agent`

---

## 4. Cardinality rules that carry product meaning

Most cardinalities are bookkeeping. These five are product decisions:

| rule | why |
|---|---|
| `(:Evidence)-[:EVIDENCE_FOR_LEARNER]->(:Learner)` is `N:1` | An evidence item is about exactly one person. Shared evidence would make per-learner access scoping unenforceable. |
| `(:SkillAssertion)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)` is `N:M` | One claim is backed by many evidence items, and one evidence item supports many claims. This is why Evidence is a node, not an edge property. |
| `(:SkillAssertion)-[:ABOUT_SKILL]->(:Skill)` is `N:1` | An assertion concerns exactly one skill at one tier, so recomputation can target it precisely. |
| `(:Learner)-[:HAS_CAREER_GOAL]->(:CareerGoal)` is `1:1` | FR-11: exactly one current goal or one explicit unknown state. Two goals would make the gap engine ambiguous. |
| `(:Evidence)-[:DERIVED_FROM]->(:Artifact)` is `N:M` | One graded rubric point routinely cites several artifact chunks (`chunks_ids_met` in the real grader payload). |

## 5. Invariants enforced in code

`LearnerGraph` refuses to construct a graph that breaks any of these:

1. every node id is unique;
2. every edge endpoint exists and its declared label matches the node;
3. every edge is a registered `(type, source, target)` triple;
4. declared cardinality holds;
5. **Evidence-First** -
   every `SkillAssertion` with a status other than `no_evidence` has at least
   one `SUPPORTED_BY_EVIDENCE` edge; every `Observation` has one; every
   `Evidence` has a `DERIVED_FROM` source record and an `EVIDENCE_FOR_LEARNER` owner.

The same five are expressed as Cypher in section 6 of
`schema_constraints.cql` and asserted against a live database by
`verify_neo4j.sh`.

