"""
Neo4j database constraints.

These constraints ensure that important identifiers
remain unique across the graph.
"""

CONSTRAINTS = [
    # Learner
    """
    CREATE CONSTRAINT learner_id_unique IF NOT EXISTS
    FOR (l:Learner)
    REQUIRE l.learner_id IS UNIQUE
    """,
    # Round
    """
    CREATE CONSTRAINT round_id_unique IF NOT EXISTS
    FOR (r:Round)
    REQUIRE r.round_id IS UNIQUE
    """,
    # Track
    """
    CREATE CONSTRAINT track_id_unique IF NOT EXISTS
    FOR (t:Track)
    REQUIRE t.track_id IS UNIQUE
    """,
    # Skill
    """
    CREATE CONSTRAINT skill_id_unique IF NOT EXISTS
    FOR (s:Skill)
    REQUIRE s.skill_id IS UNIQUE
    """,
    # Task
    """
    CREATE CONSTRAINT task_id_unique IF NOT EXISTS
    FOR (t:Task)
    REQUIRE t.task_id IS UNIQUE
    """,
    # Project
    """
    CREATE CONSTRAINT project_id_unique IF NOT EXISTS
    FOR (p:Project)
    REQUIRE p.project_id IS UNIQUE
    """,
    # Assessment
    """
    CREATE CONSTRAINT assessment_id_unique IF NOT EXISTS
    FOR (a:Assessment)
    REQUIRE a.assessment_id IS UNIQUE
    """,
    # Evidence
    """
    CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
    FOR (e:Evidence)
    REQUIRE e.evidence_id IS UNIQUE
    """,
    # Feedback
    """
    CREATE CONSTRAINT feedback_id_unique IF NOT EXISTS
    FOR (f:Feedback)
    REQUIRE f.feedback_id IS UNIQUE
    """,
    # Observation
    """
    CREATE CONSTRAINT observation_id_unique IF NOT EXISTS
    FOR (o:Observation)
    REQUIRE o.observation_id IS UNIQUE
    """,
    # Scenario
    """
    CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS
    FOR (s:Scenario)
    REQUIRE s.scenario_id IS UNIQUE
    """,
    # Recommendation
    """
    CREATE CONSTRAINT recommendation_id_unique IF NOT EXISTS
    FOR (r:Recommendation)
    REQUIRE r.recommendation_id IS UNIQUE
    """,
]
