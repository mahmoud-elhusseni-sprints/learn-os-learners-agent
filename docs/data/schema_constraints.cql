// ==========================================================================
// Professional Learner Graph - schema constraints and indexes
// ==========================================================================

// ontology version : 0.1.0
// schema version   : learner-graph/0.1.0
// node labels      : 25
// relationship types: 42
//
// GENERATED FILE - produced by generate_schema.py from learner_graph_models.py.
// Edit the models (or DDL_SPEC) and regenerate; do not hand-edit this file.
//
// Every statement uses IF NOT EXISTS, so this script is idempotent and safe
// to re-run on an existing database.
//
// EDITION SUPPORT
//   Sections 1-4 run on Neo4j 5.x Community AND Enterprise.
//   Section 5 (property existence + node keys) is ENTERPRISE ONLY and is
//   commented out. On Community the Pydantic models enforce required
//   properties at write time instead.


// ==========================================================================
// 1. Primary key uniqueness  (Community + Enterprise)
// ==========================================================================

// Every node is keyed by a deterministic UUIDv5. Together with MERGE this
// is what makes re-running the backfill a no-op instead of a duplication.

CREATE CONSTRAINT c_accessgrant_id_unique IF NOT EXISTS
FOR (n:AccessGrant) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_artifact_id_unique IF NOT EXISTS
FOR (n:Artifact) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_assessment_id_unique IF NOT EXISTS
FOR (n:Assessment) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_attempt_id_unique IF NOT EXISTS
FOR (n:Attempt) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_careergoal_id_unique IF NOT EXISTS
FOR (n:CareerGoal) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_cohort_id_unique IF NOT EXISTS
FOR (n:Cohort) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_employer_id_unique IF NOT EXISTS
FOR (n:Employer) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_evidence_id_unique IF NOT EXISTS
FOR (n:Evidence) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_group_id_unique IF NOT EXISTS
FOR (n:Group) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_interaction_id_unique IF NOT EXISTS
FOR (n:Interaction) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_learner_id_unique IF NOT EXISTS
FOR (n:Learner) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_learneridentity_id_unique IF NOT EXISTS
FOR (n:LearnerIdentity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_learningexperience_id_unique IF NOT EXISTS
FOR (n:LearningExperience) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_meeting_id_unique IF NOT EXISTS
FOR (n:Meeting) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_observation_id_unique IF NOT EXISTS
FOR (n:Observation) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_project_id_unique IF NOT EXISTS
FOR (n:Project) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_recommendation_id_unique IF NOT EXISTS
FOR (n:Recommendation) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_round_id_unique IF NOT EXISTS
FOR (n:Round) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_rubric_id_unique IF NOT EXISTS
FOR (n:Rubric) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_rubriccriterion_id_unique IF NOT EXISTS
FOR (n:RubricCriterion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_scenario_id_unique IF NOT EXISTS
FOR (n:Scenario) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_skill_id_unique IF NOT EXISTS
FOR (n:Skill) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_skillassertion_id_unique IF NOT EXISTS
FOR (n:SkillAssertion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_submission_id_unique IF NOT EXISTS
FOR (n:Submission) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_task_id_unique IF NOT EXISTS
FOR (n:Task) REQUIRE n.id IS UNIQUE;

// ==========================================================================
// 2. Business key uniqueness  (Community + Enterprise)
// ==========================================================================

// Guards against the same real-world entity being minted twice under two
// different ids - the failure mode that fragments a learner profile.

CREATE CONSTRAINT c_accessgrant_bkey_unique IF NOT EXISTS
FOR (n:AccessGrant) REQUIRE n.grant_key IS UNIQUE;
CREATE CONSTRAINT c_artifact_bkey_unique IF NOT EXISTS
FOR (n:Artifact) REQUIRE (n.source_system, n.source_id) IS UNIQUE;
CREATE CONSTRAINT c_assessment_bkey_unique IF NOT EXISTS
FOR (n:Assessment) REQUIRE (n.source_system, n.source_id) IS UNIQUE;
CREATE CONSTRAINT c_attempt_bkey_unique IF NOT EXISTS
FOR (n:Attempt) REQUIRE (n.source_system, n.source_id) IS UNIQUE;
CREATE CONSTRAINT c_cohort_bkey_unique IF NOT EXISTS
FOR (n:Cohort) REQUIRE n.cohort_key IS UNIQUE;
CREATE CONSTRAINT c_employer_bkey_unique IF NOT EXISTS
FOR (n:Employer) REQUIRE n.employer_key IS UNIQUE;
CREATE CONSTRAINT c_group_bkey_unique IF NOT EXISTS
FOR (n:Group) REQUIRE n.group_key IS UNIQUE;
CREATE CONSTRAINT c_interaction_bkey_unique IF NOT EXISTS
FOR (n:Interaction) REQUIRE (n.source_system, n.source_id) IS UNIQUE;
CREATE CONSTRAINT c_learner_bkey_unique IF NOT EXISTS
FOR (n:Learner) REQUIRE n.canonical_email IS UNIQUE;
CREATE CONSTRAINT c_learneridentity_bkey_unique IF NOT EXISTS
FOR (n:LearnerIdentity) REQUIRE (n.source_system, n.source_learner_id) IS UNIQUE;
CREATE CONSTRAINT c_learningexperience_bkey_unique IF NOT EXISTS
FOR (n:LearningExperience) REQUIRE n.lx_key IS UNIQUE;
CREATE CONSTRAINT c_meeting_bkey_unique IF NOT EXISTS
FOR (n:Meeting) REQUIRE n.meeting_key IS UNIQUE;
CREATE CONSTRAINT c_project_bkey_unique IF NOT EXISTS
FOR (n:Project) REQUIRE n.project_key IS UNIQUE;
CREATE CONSTRAINT c_round_bkey_unique IF NOT EXISTS
FOR (n:Round) REQUIRE n.round_key IS UNIQUE;
CREATE CONSTRAINT c_rubric_bkey_unique IF NOT EXISTS
FOR (n:Rubric) REQUIRE n.rubric_key IS UNIQUE;
CREATE CONSTRAINT c_rubriccriterion_bkey_unique IF NOT EXISTS
FOR (n:RubricCriterion) REQUIRE n.criterion_key IS UNIQUE;
CREATE CONSTRAINT c_scenario_bkey_unique IF NOT EXISTS
FOR (n:Scenario) REQUIRE n.scenario_key IS UNIQUE;
CREATE CONSTRAINT c_skill_bkey_unique IF NOT EXISTS
FOR (n:Skill) REQUIRE n.slug IS UNIQUE;
CREATE CONSTRAINT c_submission_bkey_unique IF NOT EXISTS
FOR (n:Submission) REQUIRE (n.source_system, n.source_id) IS UNIQUE;
CREATE CONSTRAINT c_task_bkey_unique IF NOT EXISTS
FOR (n:Task) REQUIRE n.task_key IS UNIQUE;

// ==========================================================================
// 3. Range indexes on hot query paths  (Community + Enterprise)
// ==========================================================================

// Chosen for the filters Epic 2 and Epic 3 actually run: scope by round,
// filter by evidence type/strength, sort by recency.

CREATE INDEX i_accessgrant_granted_at IF NOT EXISTS
FOR (n:AccessGrant) ON (n.granted_at);
CREATE INDEX i_accessgrant_expires_at IF NOT EXISTS
FOR (n:AccessGrant) ON (n.expires_at);
CREATE INDEX i_artifact_artifact_key IF NOT EXISTS
FOR (n:Artifact) ON (n.artifact_key);
CREATE INDEX i_artifact_artifact_type IF NOT EXISTS
FOR (n:Artifact) ON (n.artifact_type);
CREATE INDEX i_assessment_assessment_kind IF NOT EXISTS
FOR (n:Assessment) ON (n.assessment_kind);
CREATE INDEX i_assessment_verdict IF NOT EXISTS
FOR (n:Assessment) ON (n.verdict);
CREATE INDEX i_assessment_evaluated_at IF NOT EXISTS
FOR (n:Assessment) ON (n.evaluated_at);
CREATE INDEX i_assessment_criteria_met IF NOT EXISTS
FOR (n:Assessment) ON (n.criteria_met);
CREATE INDEX i_assessment_criteria_total IF NOT EXISTS
FOR (n:Assessment) ON (n.criteria_total);
CREATE INDEX i_attempt_verdict IF NOT EXISTS
FOR (n:Attempt) ON (n.verdict);
CREATE INDEX i_attempt_evaluated_at IF NOT EXISTS
FOR (n:Attempt) ON (n.evaluated_at);
CREATE INDEX i_careergoal_status IF NOT EXISTS
FOR (n:CareerGoal) ON (n.status);
CREATE INDEX i_careergoal_target_role IF NOT EXISTS
FOR (n:CareerGoal) ON (n.target_role);
CREATE INDEX i_employer_name IF NOT EXISTS
FOR (n:Employer) ON (n.name);
CREATE INDEX i_evidence_evidence_type IF NOT EXISTS
FOR (n:Evidence) ON (n.evidence_type);
CREATE INDEX i_evidence_strength IF NOT EXISTS
FOR (n:Evidence) ON (n.strength);
CREATE INDEX i_evidence_observed_at IF NOT EXISTS
FOR (n:Evidence) ON (n.observed_at);
CREATE INDEX i_evidence_access_scope IF NOT EXISTS
FOR (n:Evidence) ON (n.access_scope);
CREATE INDEX i_evidence_source_system IF NOT EXISTS
FOR (n:Evidence) ON (n.source_system);
CREATE INDEX i_evidence_confidence IF NOT EXISTS
FOR (n:Evidence) ON (n.confidence);
CREATE INDEX i_group_track IF NOT EXISTS
FOR (n:Group) ON (n.track);
CREATE INDEX i_interaction_interaction_kind IF NOT EXISTS
FOR (n:Interaction) ON (n.interaction_kind);
CREATE INDEX i_interaction_occurred_at IF NOT EXISTS
FOR (n:Interaction) ON (n.occurred_at);
CREATE INDEX i_interaction_struggle_area IF NOT EXISTS
FOR (n:Interaction) ON (n.struggle_area);
CREATE INDEX i_interaction_initiated_by IF NOT EXISTS
FOR (n:Interaction) ON (n.initiated_by);
CREATE INDEX i_interaction_carries_feedback IF NOT EXISTS
FOR (n:Interaction) ON (n.carries_feedback);
CREATE INDEX i_learner_display_name IF NOT EXISTS
FOR (n:Learner) ON (n.display_name);
CREATE INDEX i_learner_source_system IF NOT EXISTS
FOR (n:Learner) ON (n.source_system);
CREATE INDEX i_learneridentity_resolution_status IF NOT EXISTS
FOR (n:LearnerIdentity) ON (n.resolution_status);
CREATE INDEX i_learneridentity_source_email IF NOT EXISTS
FOR (n:LearnerIdentity) ON (n.source_email);
CREATE INDEX i_learningexperience_status IF NOT EXISTS
FOR (n:LearningExperience) ON (n.status);
CREATE INDEX i_learningexperience_outcome IF NOT EXISTS
FOR (n:LearningExperience) ON (n.outcome);
CREATE INDEX i_learningexperience_activated_at IF NOT EXISTS
FOR (n:LearningExperience) ON (n.activated_at);
CREATE INDEX i_learningexperience_deadline_at IF NOT EXISTS
FOR (n:LearningExperience) ON (n.deadline_at);
CREATE INDEX i_meeting_kind IF NOT EXISTS
FOR (n:Meeting) ON (n.kind);
CREATE INDEX i_meeting_starts_at_utc IF NOT EXISTS
FOR (n:Meeting) ON (n.starts_at_utc);
CREATE INDEX i_meeting_extraction_status IF NOT EXISTS
FOR (n:Meeting) ON (n.extraction_status);
CREATE INDEX i_meeting_transcript_available IF NOT EXISTS
FOR (n:Meeting) ON (n.transcript_available);
CREATE INDEX i_observation_category IF NOT EXISTS
FOR (n:Observation) ON (n.category);
CREATE INDEX i_observation_observed_at IF NOT EXISTS
FOR (n:Observation) ON (n.observed_at);
CREATE INDEX i_observation_confidence IF NOT EXISTS
FOR (n:Observation) ON (n.confidence);
CREATE INDEX i_recommendation_gap_type IF NOT EXISTS
FOR (n:Recommendation) ON (n.gap_type);
CREATE INDEX i_recommendation_status IF NOT EXISTS
FOR (n:Recommendation) ON (n.status);
CREATE INDEX i_recommendation_priority IF NOT EXISTS
FOR (n:Recommendation) ON (n.priority);
CREATE INDEX i_rubriccriterion_category IF NOT EXISTS
FOR (n:RubricCriterion) ON (n.category);
CREATE INDEX i_scenario_difficulty IF NOT EXISTS
FOR (n:Scenario) ON (n.difficulty);
CREATE INDEX i_scenario_approved IF NOT EXISTS
FOR (n:Scenario) ON (n.approved);
CREATE INDEX i_skill_canonical_name IF NOT EXISTS
FOR (n:Skill) ON (n.canonical_name);
CREATE INDEX i_skill_category IF NOT EXISTS
FOR (n:Skill) ON (n.category);
CREATE INDEX i_skillassertion_tier IF NOT EXISTS
FOR (n:SkillAssertion) ON (n.tier);
CREATE INDEX i_skillassertion_status IF NOT EXISTS
FOR (n:SkillAssertion) ON (n.status);
CREATE INDEX i_skillassertion_confidence IF NOT EXISTS
FOR (n:SkillAssertion) ON (n.confidence);
CREATE INDEX i_skillassertion_latest_evidence_at IF NOT EXISTS
FOR (n:SkillAssertion) ON (n.latest_evidence_at);
CREATE INDEX i_skillassertion_evidence_count IF NOT EXISTS
FOR (n:SkillAssertion) ON (n.evidence_count);
CREATE INDEX i_submission_kind IF NOT EXISTS
FOR (n:Submission) ON (n.kind);
CREATE INDEX i_submission_submitted_at IF NOT EXISTS
FOR (n:Submission) ON (n.submitted_at);
CREATE INDEX i_submission_is_resubmission IF NOT EXISTS
FOR (n:Submission) ON (n.is_resubmission);
CREATE INDEX i_task_task_archetype IF NOT EXISTS
FOR (n:Task) ON (n.task_archetype);

// Relationship property indexes (Neo4j 5.x).

CREATE INDEX rel_demonstrated_skill_status IF NOT EXISTS
FOR ()-[r:DEMONSTRATED_SKILL]-() ON (r.status);
CREATE INDEX rel_demonstrated_skill_confidence IF NOT EXISTS
FOR ()-[r:DEMONSTRATED_SKILL]-() ON (r.confidence);
CREATE INDEX rel_assessed_on_skill_status IF NOT EXISTS
FOR ()-[r:ASSESSED_ON_SKILL]-() ON (r.status);
CREATE INDEX rel_scored_criterion_status IF NOT EXISTS
FOR ()-[r:SCORED_CRITERION]-() ON (r.status);
CREATE INDEX rel_completed_task_outcome IF NOT EXISTS
FOR ()-[r:COMPLETED_TASK]-() ON (r.outcome);
CREATE INDEX rel_derived_from_extraction_confidence IF NOT EXISTS
FOR ()-[r:DERIVED_FROM]-() ON (r.extraction_confidence);
CREATE INDEX rel_contains_artifact_cited_by_grader IF NOT EXISTS
FOR ()-[r:CONTAINS_ARTIFACT]-() ON (r.cited_by_grader);
CREATE INDEX rel_evaluated_by_verdict IF NOT EXISTS
FOR ()-[r:EVALUATED_BY]-() ON (r.verdict);
CREATE INDEX rel_submitted_attempt_number IF NOT EXISTS
FOR ()-[r:SUBMITTED]-() ON (r.attempt_number);

// ==========================================================================
// 4. Full-text indexes  (Community + Enterprise)
// ==========================================================================

// Feeds the hybrid retrieval in Sprint 3: graph filtering narrows the
// population, full-text search ranks the evidence inside it.

CREATE FULLTEXT INDEX ft_artifact IF NOT EXISTS
FOR (n:Artifact) ON EACH [n.content_excerpt];
CREATE FULLTEXT INDEX ft_assessment IF NOT EXISTS
FOR (n:Assessment) ON EACH [n.summary, n.mentor_reply];
CREATE FULLTEXT INDEX ft_careergoal IF NOT EXISTS
FOR (n:CareerGoal) ON EACH [n.target_role];
CREATE FULLTEXT INDEX ft_evidence IF NOT EXISTS
FOR (n:Evidence) ON EACH [n.title, n.content];
CREATE FULLTEXT INDEX ft_interaction IF NOT EXISTS
FOR (n:Interaction) ON EACH [n.summary];
CREATE FULLTEXT INDEX ft_meeting IF NOT EXISTS
FOR (n:Meeting) ON EACH [n.topic];
CREATE FULLTEXT INDEX ft_observation IF NOT EXISTS
FOR (n:Observation) ON EACH [n.context, n.behavior, n.outcome];
CREATE FULLTEXT INDEX ft_project IF NOT EXISTS
FOR (n:Project) ON EACH [n.name];
CREATE FULLTEXT INDEX ft_recommendation IF NOT EXISTS
FOR (n:Recommendation) ON EACH [n.reason];
CREATE FULLTEXT INDEX ft_rubriccriterion IF NOT EXISTS
FOR (n:RubricCriterion) ON EACH [n.requirement, n.description];
CREATE FULLTEXT INDEX ft_scenario IF NOT EXISTS
FOR (n:Scenario) ON EACH [n.title, n.description];
CREATE FULLTEXT INDEX ft_skill IF NOT EXISTS
FOR (n:Skill) ON EACH [n.canonical_name, n.description];
CREATE FULLTEXT INDEX ft_skillassertion IF NOT EXISTS
FOR (n:SkillAssertion) ON EACH [n.rationale];
CREATE FULLTEXT INDEX ft_submission IF NOT EXISTS
FOR (n:Submission) ON EACH [n.text];
CREATE FULLTEXT INDEX ft_task IF NOT EXISTS
FOR (n:Task) ON EACH [n.headline, n.description];

// ==========================================================================
// 5. Property existence constraints  (ENTERPRISE ONLY - commented out)
// ==========================================================================

// Neo4j Community rejects these with:
//   'Property existence constraint requires Neo4j Enterprise Edition'
//
// Uncomment the whole section when running against Enterprise. The required
// properties below are derived automatically from the Pydantic models, so
// they stay in step with the Python contract.

// --- AccessGrant ---
// CREATE CONSTRAINT c_accessgrant_created_at_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_grant_key_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.grant_key IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_granted_at_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.granted_at IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_id_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_ingested_at_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_source_id_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_source_observed_at_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_source_system_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_accessgrant_source_type_exists IF NOT EXISTS
// FOR (n:AccessGrant) REQUIRE n.source_type IS NOT NULL;

// --- Artifact ---
// CREATE CONSTRAINT c_artifact_artifact_key_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.artifact_key IS NOT NULL;
// CREATE CONSTRAINT c_artifact_created_at_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_artifact_id_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_artifact_ingested_at_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_artifact_source_id_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_artifact_source_observed_at_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_artifact_source_system_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_artifact_source_type_exists IF NOT EXISTS
// FOR (n:Artifact) REQUIRE n.source_type IS NOT NULL;

// --- Assessment ---
// CREATE CONSTRAINT c_assessment_assessment_kind_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.assessment_kind IS NOT NULL;
// CREATE CONSTRAINT c_assessment_created_at_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_assessment_id_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_assessment_ingested_at_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_assessment_source_id_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_assessment_source_observed_at_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_assessment_source_system_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_assessment_source_type_exists IF NOT EXISTS
// FOR (n:Assessment) REQUIRE n.source_type IS NOT NULL;

// --- Attempt ---
// CREATE CONSTRAINT c_attempt_attempt_number_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.attempt_number IS NOT NULL;
// CREATE CONSTRAINT c_attempt_created_at_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_attempt_id_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_attempt_ingested_at_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_attempt_source_id_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_attempt_source_observed_at_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_attempt_source_system_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_attempt_source_type_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.source_type IS NOT NULL;
// CREATE CONSTRAINT c_attempt_verdict_exists IF NOT EXISTS
// FOR (n:Attempt) REQUIRE n.verdict IS NOT NULL;

// --- CareerGoal ---
// CREATE CONSTRAINT c_careergoal_created_at_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_id_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_ingested_at_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_source_id_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_source_observed_at_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_source_system_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_source_type_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.source_type IS NOT NULL;
// CREATE CONSTRAINT c_careergoal_status_exists IF NOT EXISTS
// FOR (n:CareerGoal) REQUIRE n.status IS NOT NULL;

// --- Cohort ---
// CREATE CONSTRAINT c_cohort_cohort_key_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.cohort_key IS NOT NULL;
// CREATE CONSTRAINT c_cohort_created_at_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_cohort_id_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_cohort_ingested_at_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_cohort_name_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.name IS NOT NULL;
// CREATE CONSTRAINT c_cohort_source_id_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_cohort_source_observed_at_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_cohort_source_system_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_cohort_source_type_exists IF NOT EXISTS
// FOR (n:Cohort) REQUIRE n.source_type IS NOT NULL;

// --- Employer ---
// CREATE CONSTRAINT c_employer_created_at_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_employer_employer_key_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.employer_key IS NOT NULL;
// CREATE CONSTRAINT c_employer_id_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_employer_ingested_at_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_employer_name_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.name IS NOT NULL;
// CREATE CONSTRAINT c_employer_source_id_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_employer_source_observed_at_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_employer_source_system_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_employer_source_type_exists IF NOT EXISTS
// FOR (n:Employer) REQUIRE n.source_type IS NOT NULL;

// --- Evidence ---
// CREATE CONSTRAINT c_evidence_content_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.content IS NOT NULL;
// CREATE CONSTRAINT c_evidence_created_at_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_evidence_evidence_type_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.evidence_type IS NOT NULL;
// CREATE CONSTRAINT c_evidence_id_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_evidence_ingested_at_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_evidence_observed_at_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.observed_at IS NOT NULL;
// CREATE CONSTRAINT c_evidence_source_id_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_evidence_source_observed_at_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_evidence_source_system_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_evidence_source_type_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.source_type IS NOT NULL;
// CREATE CONSTRAINT c_evidence_strength_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.strength IS NOT NULL;
// CREATE CONSTRAINT c_evidence_title_exists IF NOT EXISTS
// FOR (n:Evidence) REQUIRE n.title IS NOT NULL;

// --- Group ---
// CREATE CONSTRAINT c_group_created_at_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_group_group_key_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.group_key IS NOT NULL;
// CREATE CONSTRAINT c_group_id_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_group_ingested_at_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_group_name_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.name IS NOT NULL;
// CREATE CONSTRAINT c_group_source_id_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_group_source_observed_at_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_group_source_system_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_group_source_type_exists IF NOT EXISTS
// FOR (n:Group) REQUIRE n.source_type IS NOT NULL;

// --- Interaction ---
// CREATE CONSTRAINT c_interaction_created_at_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_interaction_id_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_interaction_ingested_at_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_interaction_interaction_kind_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.interaction_kind IS NOT NULL;
// CREATE CONSTRAINT c_interaction_occurred_at_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.occurred_at IS NOT NULL;
// CREATE CONSTRAINT c_interaction_source_id_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_interaction_source_observed_at_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_interaction_source_system_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_interaction_source_type_exists IF NOT EXISTS
// FOR (n:Interaction) REQUIRE n.source_type IS NOT NULL;

// --- Learner ---
// CREATE CONSTRAINT c_learner_canonical_email_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.canonical_email IS NOT NULL;
// CREATE CONSTRAINT c_learner_created_at_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_learner_display_name_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.display_name IS NOT NULL;
// CREATE CONSTRAINT c_learner_id_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_learner_ingested_at_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_learner_source_id_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_learner_source_observed_at_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_learner_source_system_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_learner_source_type_exists IF NOT EXISTS
// FOR (n:Learner) REQUIRE n.source_type IS NOT NULL;

// --- LearnerIdentity ---
// CREATE CONSTRAINT c_learneridentity_created_at_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_id_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_ingested_at_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_source_id_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_source_learner_id_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.source_learner_id IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_source_observed_at_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_source_system_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_learneridentity_source_type_exists IF NOT EXISTS
// FOR (n:LearnerIdentity) REQUIRE n.source_type IS NOT NULL;

// --- LearningExperience ---
// CREATE CONSTRAINT c_learningexperience_created_at_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_id_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_ingested_at_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_lx_key_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.lx_key IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_source_id_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_source_observed_at_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_source_system_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_source_type_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.source_type IS NOT NULL;
// CREATE CONSTRAINT c_learningexperience_status_exists IF NOT EXISTS
// FOR (n:LearningExperience) REQUIRE n.status IS NOT NULL;

// --- Meeting ---
// CREATE CONSTRAINT c_meeting_created_at_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_meeting_id_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_meeting_ingested_at_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_meeting_kind_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.kind IS NOT NULL;
// CREATE CONSTRAINT c_meeting_meeting_key_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.meeting_key IS NOT NULL;
// CREATE CONSTRAINT c_meeting_source_id_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_meeting_source_observed_at_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_meeting_source_system_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_meeting_source_type_exists IF NOT EXISTS
// FOR (n:Meeting) REQUIRE n.source_type IS NOT NULL;

// --- Observation ---
// CREATE CONSTRAINT c_observation_behavior_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.behavior IS NOT NULL;
// CREATE CONSTRAINT c_observation_category_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.category IS NOT NULL;
// CREATE CONSTRAINT c_observation_computed_at_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.computed_at IS NOT NULL;
// CREATE CONSTRAINT c_observation_computed_by_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.computed_by IS NOT NULL;
// CREATE CONSTRAINT c_observation_context_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.context IS NOT NULL;
// CREATE CONSTRAINT c_observation_created_at_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_observation_id_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_observation_observed_at_exists IF NOT EXISTS
// FOR (n:Observation) REQUIRE n.observed_at IS NOT NULL;

// --- Project ---
// CREATE CONSTRAINT c_project_created_at_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_project_id_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_project_ingested_at_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_project_name_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.name IS NOT NULL;
// CREATE CONSTRAINT c_project_project_key_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.project_key IS NOT NULL;
// CREATE CONSTRAINT c_project_source_id_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_project_source_observed_at_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_project_source_system_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_project_source_type_exists IF NOT EXISTS
// FOR (n:Project) REQUIRE n.source_type IS NOT NULL;

// --- Recommendation ---
// CREATE CONSTRAINT c_recommendation_computed_at_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.computed_at IS NOT NULL;
// CREATE CONSTRAINT c_recommendation_computed_by_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.computed_by IS NOT NULL;
// CREATE CONSTRAINT c_recommendation_created_at_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_recommendation_gap_type_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.gap_type IS NOT NULL;
// CREATE CONSTRAINT c_recommendation_id_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_recommendation_priority_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.priority IS NOT NULL;
// CREATE CONSTRAINT c_recommendation_reason_exists IF NOT EXISTS
// FOR (n:Recommendation) REQUIRE n.reason IS NOT NULL;

// --- Round ---
// CREATE CONSTRAINT c_round_created_at_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_round_id_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_round_ingested_at_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_round_name_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.name IS NOT NULL;
// CREATE CONSTRAINT c_round_round_key_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.round_key IS NOT NULL;
// CREATE CONSTRAINT c_round_source_id_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_round_source_observed_at_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_round_source_system_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_round_source_type_exists IF NOT EXISTS
// FOR (n:Round) REQUIRE n.source_type IS NOT NULL;

// --- Rubric ---
// CREATE CONSTRAINT c_rubric_created_at_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_rubric_id_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_rubric_ingested_at_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_rubric_rubric_key_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.rubric_key IS NOT NULL;
// CREATE CONSTRAINT c_rubric_source_id_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_rubric_source_observed_at_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_rubric_source_system_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_rubric_source_type_exists IF NOT EXISTS
// FOR (n:Rubric) REQUIRE n.source_type IS NOT NULL;

// --- RubricCriterion ---
// CREATE CONSTRAINT c_rubriccriterion_created_at_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_criterion_key_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.criterion_key IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_id_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_ingested_at_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_source_id_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_source_observed_at_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_source_system_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_rubriccriterion_source_type_exists IF NOT EXISTS
// FOR (n:RubricCriterion) REQUIRE n.source_type IS NOT NULL;

// --- Scenario ---
// CREATE CONSTRAINT c_scenario_created_at_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_scenario_id_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_scenario_ingested_at_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_scenario_scenario_key_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.scenario_key IS NOT NULL;
// CREATE CONSTRAINT c_scenario_source_id_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_scenario_source_observed_at_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_scenario_source_system_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_scenario_source_type_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.source_type IS NOT NULL;
// CREATE CONSTRAINT c_scenario_title_exists IF NOT EXISTS
// FOR (n:Scenario) REQUIRE n.title IS NOT NULL;

// --- Skill ---
// CREATE CONSTRAINT c_skill_canonical_name_exists IF NOT EXISTS
// FOR (n:Skill) REQUIRE n.canonical_name IS NOT NULL;
// CREATE CONSTRAINT c_skill_category_exists IF NOT EXISTS
// FOR (n:Skill) REQUIRE n.category IS NOT NULL;
// CREATE CONSTRAINT c_skill_created_at_exists IF NOT EXISTS
// FOR (n:Skill) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_skill_id_exists IF NOT EXISTS
// FOR (n:Skill) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_skill_slug_exists IF NOT EXISTS
// FOR (n:Skill) REQUIRE n.slug IS NOT NULL;

// --- SkillAssertion ---
// CREATE CONSTRAINT c_skillassertion_computed_at_exists IF NOT EXISTS
// FOR (n:SkillAssertion) REQUIRE n.computed_at IS NOT NULL;
// CREATE CONSTRAINT c_skillassertion_computed_by_exists IF NOT EXISTS
// FOR (n:SkillAssertion) REQUIRE n.computed_by IS NOT NULL;
// CREATE CONSTRAINT c_skillassertion_created_at_exists IF NOT EXISTS
// FOR (n:SkillAssertion) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_skillassertion_id_exists IF NOT EXISTS
// FOR (n:SkillAssertion) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_skillassertion_status_exists IF NOT EXISTS
// FOR (n:SkillAssertion) REQUIRE n.status IS NOT NULL;
// CREATE CONSTRAINT c_skillassertion_tier_exists IF NOT EXISTS
// FOR (n:SkillAssertion) REQUIRE n.tier IS NOT NULL;

// --- Submission ---
// CREATE CONSTRAINT c_submission_created_at_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_submission_id_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_submission_ingested_at_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_submission_kind_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.kind IS NOT NULL;
// CREATE CONSTRAINT c_submission_source_id_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_submission_source_observed_at_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_submission_source_system_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_submission_source_type_exists IF NOT EXISTS
// FOR (n:Submission) REQUIRE n.source_type IS NOT NULL;

// --- Task ---
// CREATE CONSTRAINT c_task_created_at_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.created_at IS NOT NULL;
// CREATE CONSTRAINT c_task_headline_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.headline IS NOT NULL;
// CREATE CONSTRAINT c_task_id_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.id IS NOT NULL;
// CREATE CONSTRAINT c_task_ingested_at_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.ingested_at IS NOT NULL;
// CREATE CONSTRAINT c_task_source_id_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.source_id IS NOT NULL;
// CREATE CONSTRAINT c_task_source_observed_at_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.source_observed_at IS NOT NULL;
// CREATE CONSTRAINT c_task_source_system_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.source_system IS NOT NULL;
// CREATE CONSTRAINT c_task_source_type_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.source_type IS NOT NULL;
// CREATE CONSTRAINT c_task_task_key_exists IF NOT EXISTS
// FOR (n:Task) REQUIRE n.task_key IS NOT NULL;

// Relationship property existence (ENTERPRISE ONLY).
// Enforces that graded criterion results always carry a verdict and a
// confidence - the Evidence-First rule applied at the relationship level.
//
// CREATE CONSTRAINT rel_scored_criterion_status_exists IF NOT EXISTS
// FOR ()-[r:SCORED_CRITERION]-() REQUIRE r.status IS NOT NULL;
// CREATE CONSTRAINT rel_scored_criterion_confidence_exists IF NOT EXISTS
// FOR ()-[r:SCORED_CRITERION]-() REQUIRE r.confidence IS NOT NULL;

// ==========================================================================
// 6. Verification queries  (run manually after loading the seed)
// ==========================================================================

// 6a. What got created.
// SHOW CONSTRAINTS;
// SHOW INDEXES;

// 6b. EVIDENCE-FIRST INVARIANTS. Each of these must return ZERO rows.
//     They are the database-side mirror of LearnerGraph._evidence_first.

// (i) no skill claim without supporting evidence
// MATCH (a:SkillAssertion)
// WHERE a.status <> 'no_evidence' AND NOT (a)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)
// RETURN a.id AS unsupported_assertion, a.status;

// (ii) no evidence without a traceable source record
// MATCH (e:Evidence) WHERE NOT (e)-[:DERIVED_FROM]->() RETURN e.id AS untraceable;

// (iii) no evidence detached from a learner
// MATCH (e:Evidence) WHERE NOT (e)-[:EVIDENCE_FOR_LEARNER]->(:Learner)
// RETURN e.id AS orphan_evidence;

// (iv) no behavioural observation without evidence
// MATCH (o:Observation) WHERE NOT (o)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)
// RETURN o.id AS unsupported_observation;

// (v) provenance coverage must be 100% (PRD success metric)
// MATCH (e:Evidence)
// WHERE e.source_system IS NULL OR e.source_id IS NULL OR e.source_observed_at IS NULL
// RETURN e.id AS missing_provenance;

// 6c. IDEMPOTENCY CHECK. Record the counts, re-run sample_learner_seed.cql,
//     then re-run this: the numbers must be identical.
// MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
// MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS rels ORDER BY rel;

// 6d. THE DEMO TRAVERSAL - 'Does this learner know Python? Show the evidence.'
// MATCH (l:Learner {canonical_email: 'learner-a4@example.invalid'})
//       -[:HAS_SKILL_ASSERTION]->(a:SkillAssertion)-[:ABOUT_SKILL]->(s:Skill {slug: 'python'})
// MATCH (a)-[:SUPPORTED_BY_EVIDENCE]->(e:Evidence)
// RETURN s.canonical_name AS skill, a.tier AS tier, a.status AS strength,
//        e.evidence_type AS type, e.source_system AS source,
//        e.observed_at AS observed, e.title AS evidence
// ORDER BY e.observed_at DESC;

// 6e. EVIDENCE COVERAGE per learner - PRD 8.2 fairness guard, so a
//     heavily-observed learner is not mistaken for a stronger one.
// MATCH (e:Evidence)-[:EVIDENCE_FOR_LEARNER]->(l:Learner)
// RETURN l.display_name AS learner, count(e) AS evidence_items,
//        count(DISTINCT e.source_system) AS distinct_sources
// ORDER BY evidence_items DESC;
