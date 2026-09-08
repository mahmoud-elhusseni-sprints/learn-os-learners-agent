// ==========================================================================
// Professional Learner Graph - schema constraints and indexes
// ==========================================================================

// ontology version : 0.2.0
// schema version   : learner-graph/0.2.0
// node labels      : 3  (DataSource, LearnerProfile, MemoryCard)
// relationship types: 3
//
// GENERATED FILE - produced by scripts/generate_constraints.py from
// src/app/graph/schema.py. Do not hand-edit; change the models and
// regenerate.
//
// Neo4j Community Edition (docker-compose.yml pins neo4j:5-community):
// uniqueness constraints and indexes only. No property-existence
// constraints are emitted - those are Enterprise-only. The Pydantic
// models are the enforcement layer for required properties.
//
// Every statement uses IF NOT EXISTS, so this file is idempotent.


// ==========================================================================
// 1. Primary key uniqueness
// ==========================================================================

CREATE CONSTRAINT c_datasource_id_unique IF NOT EXISTS
FOR (n:DataSource) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_learnerprofile_id_unique IF NOT EXISTS
FOR (n:LearnerProfile) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT c_memorycard_id_unique IF NOT EXISTS
FOR (n:MemoryCard) REQUIRE n.id IS UNIQUE;

// ==========================================================================
// 2. Business key uniqueness
// ==========================================================================

// Guards against the same real-world record being ingested twice
// under two different generated ids.

CREATE CONSTRAINT c_datasource_bkey_unique IF NOT EXISTS
FOR (n:DataSource) REQUIRE n.datasource_id IS UNIQUE;
CREATE CONSTRAINT c_learnerprofile_bkey_unique IF NOT EXISTS
FOR (n:LearnerProfile) REQUIRE n.learner_id IS UNIQUE;
CREATE CONSTRAINT c_memorycard_bkey_unique IF NOT EXISTS
FOR (n:MemoryCard) REQUIRE n.card_id IS UNIQUE;

// ==========================================================================
// 3. Range indexes
// ==========================================================================

CREATE INDEX i_datasource_datasource_name IF NOT EXISTS
FOR (n:DataSource) ON (n.datasource_name);
CREATE INDEX i_datasource_timestamp IF NOT EXISTS
FOR (n:DataSource) ON (n.timestamp);
CREATE INDEX i_learnerprofile_name IF NOT EXISTS
FOR (n:LearnerProfile) ON (n.name);
CREATE INDEX i_learnerprofile_role IF NOT EXISTS
FOR (n:LearnerProfile) ON (n.role);
CREATE INDEX i_learnerprofile_group_name IF NOT EXISTS
FOR (n:LearnerProfile) ON (n.group_name);
CREATE INDEX i_learnerprofile_round_name IF NOT EXISTS
FOR (n:LearnerProfile) ON (n.round_name);
CREATE INDEX i_memorycard_metric_key IF NOT EXISTS
FOR (n:MemoryCard) ON (n.metric_key);
CREATE INDEX i_memorycard_created_at IF NOT EXISTS
FOR (n:MemoryCard) ON (n.created_at);

// ==========================================================================
// 4. Full-text indexes
// ==========================================================================

CREATE FULLTEXT INDEX ft_memorycard IF NOT EXISTS
FOR (n:MemoryCard) ON EACH [n.content, n.rationale];

// ==========================================================================
// 5. Verification queries (run manually after loading the seed)
// ==========================================================================

// SHOW CONSTRAINTS;
// SHOW INDEXES;

// A learner's full trail: their source records and the memory
// cards extracted from them.
// MATCH (l:LearnerProfile {learner_id: '127c834c-f7ce-4cc7-9a73-c8f93c8648aa'})
//       -[:PRODUCED]->(d:DataSource)
// OPTIONAL MATCH (d)-[:EXTRACTED_INTO]->(m:MemoryCard)
// RETURN d.datasource_name, d.timestamp, m.metric_key, m.content
// ORDER BY d.timestamp;

// Idempotency check: record counts, re-run the seed load, re-run this.
// MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
// MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS rels ORDER BY rel;
