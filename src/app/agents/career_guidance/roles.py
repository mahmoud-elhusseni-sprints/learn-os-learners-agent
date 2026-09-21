"""Target-role competency frameworks for the Career Guidance Agent.

Competencies are defined once in ``COMPETENCY_LIBRARY`` and reused by each
role with a role-specific importance and required level, so adding a career
means adding one ``RoleDefinition`` - no agent logic changes.

Non-technical competencies reference the team's shared taxonomy in
``src.app.core.tags``; the registry rejects any tag that is not in it.

Action templates may use two placeholders:
``{anchor}`` - the learner's own strongest piece of work (filled in Python),
``{competencies}`` - the competency labels a project covers.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from src.app.core.tags import ALLOWED_TAXONOMY_SET
from src.app.schemas.career_guidance import (
    ActionTemplate,
    CompetencyKind,
    CompetencyRequirement,
    Importance,
    ProficiencyLevel,
    RoleDefinition,
)

TECHNICAL = CompetencyKind.TECHNICAL
NON_TECHNICAL = CompetencyKind.NON_TECHNICAL
CRITICAL = Importance.CRITICAL
IMPORTANT = Importance.IMPORTANT


def normalize(text: str) -> str:
    """Lowercase words only, so 'A/B Testing' and 'a b testing' match."""
    return " ".join(re.findall(r"[a-z0-9+#]+", text.lower()))


def _competency(
    key: str,
    label: str,
    kind: CompetencyKind,
    aliases: list[str],
    course: tuple[str, str],
    task: tuple[str, str],
    taxonomy_tags: list[str] | None = None,
) -> CompetencyRequirement:
    return CompetencyRequirement(
        key=key,
        label=label,
        kind=kind,
        aliases=aliases,
        taxonomy_tags=taxonomy_tags or [],
        course=ActionTemplate(title=course[0], action=course[1]),
        task=ActionTemplate(title=task[0], action=task[1]),
    )


COMPETENCY_LIBRARY: dict[str, CompetencyRequirement] = {
    item.key: item
    for item in (
        # --- technical -------------------------------------------------------
        _competency(
            "python",
            "Python programming",
            TECHNICAL,
            ["python", "python programming", "python 3"],
            (
                "Complete a structured intermediate Python course",
                "Work through an intermediate Python course covering data "
                "structures, typing, error handling and packaging, and finish "
                "every graded exercise.",
            ),
            (
                "Ship a small, reviewed Python utility",
                "Write a typed Python module that solves a real problem from "
                "your current work, add unit tests, and request a code review.",
            ),
        ),
        _competency(
            "sql",
            "SQL and relational data",
            TECHNICAL,
            ["sql", "postgresql", "postgres", "mysql", "relational databases"],
            (
                "Complete a structured SQL course",
                "Take a SQL course covering joins, aggregation, window "
                "functions and indexing, and complete its practice queries.",
            ),
            (
                "Answer three business questions with SQL",
                "Write documented SQL queries that answer three concrete "
                "questions on a real or public dataset and have them reviewed.",
            ),
        ),
        _competency(
            "apis",
            "API design and integration",
            TECHNICAL,
            ["api", "apis", "rest api", "rest apis", "fastapi", "api development"],
            (
                "Complete a course on REST API design",
                "Take a course on REST API design covering resources, status "
                "codes, validation, authentication and versioning.",
            ),
            (
                "Build and document a small validated API",
                "Build a small FastAPI service with request validation, error "
                "handling and an OpenAPI description, then have it reviewed.",
            ),
        ),
        _competency(
            "data_analysis",
            "Data analysis",
            TECHNICAL,
            ["data analysis", "pandas", "exploratory data analysis", "eda"],
            (
                "Complete a structured data analysis course",
                "Take a data analysis course covering cleaning, aggregation, "
                "visualisation and communicating findings.",
            ),
            (
                "Publish a short exploratory analysis",
                "Analyse one dataset end to end and write up three findings, "
                "each supported by a chart and the code that produced it.",
            ),
        ),
        _competency(
            "machine_learning",
            "Machine learning",
            TECHNICAL,
            ["machine learning", "ml", "deep learning", "nlp", "model training"],
            (
                "Complete a structured machine learning course",
                "Take a machine learning course covering supervised learning, "
                "evaluation metrics, overfitting and model selection.",
            ),
            (
                "Train and evaluate a baseline model",
                "Train a baseline model on a public dataset, compare it with "
                "one improvement, and document the evaluation honestly.",
            ),
        ),
        _competency(
            "rag_pipelines",
            "RAG pipelines and LLM applications",
            TECHNICAL,
            [
                "rag",
                "rag pipelines",
                "retrieval augmented generation",
                "llm applications",
                "langchain",
            ],
            (
                "Complete a course on retrieval-augmented generation",
                "Take a course on RAG covering chunking, embeddings, retrieval "
                "evaluation and grounding answers in sources.",
            ),
            (
                "Build a small evaluated RAG prototype",
                "Build a retrieval-augmented prototype over a small document "
                "set and measure retrieval quality on ten test questions.",
            ),
        ),
        _competency(
            "testing",
            "Automated testing",
            TECHNICAL,
            ["testing", "unit testing", "pytest", "test automation", "tdd"],
            (
                "Complete a course on automated testing",
                "Take a course on automated testing covering unit tests, "
                "fixtures, mocking and test design.",
            ),
            (
                "Add a meaningful test suite to existing code",
                "Add unit tests with edge cases and mocked dependencies to one "
                "module you have already written, and report the coverage.",
            ),
        ),
        _competency(
            "software_engineering",
            "Software engineering practices",
            TECHNICAL,
            [
                "software engineering",
                "git",
                "version control",
                "clean code",
                "code review",
            ],
            (
                "Complete a course on software engineering practices",
                "Take a course covering version control workflows, code "
                "review, modular design and maintainability.",
            ),
            (
                "Refactor a module through a reviewed pull request",
                "Refactor one module for readability and structure, open a "
                "pull request with a clear description, and address review "
                "comments.",
            ),
        ),
        _competency(
            "system_design",
            "System design",
            TECHNICAL,
            ["system design", "architecture", "software architecture"],
            (
                "Complete a course on system design fundamentals",
                "Take a system design course covering components, data flow, "
                "scaling and trade-offs.",
            ),
            (
                "Write a design document for a real feature",
                "Write a one-page design document for a feature, including a "
                "component diagram, trade-offs, and risks, and have it reviewed.",
            ),
        ),
        _competency(
            "ai_product_literacy",
            "AI product literacy",
            TECHNICAL,
            ["ai product literacy", "ai literacy", "llm products", "ai products"],
            (
                "Complete a course on building AI products",
                "Take a course on AI products covering model capabilities, "
                "evaluation, risks and product trade-offs.",
            ),
            (
                "Evaluate an AI feature against user needs",
                "Evaluate one existing AI feature on five realistic user tasks "
                "and write up where it succeeds, fails and what you would change.",
            ),
        ),
        _competency(
            "experimentation",
            "Experimentation and product analytics",
            TECHNICAL,
            ["experimentation", "a/b testing", "ab testing", "product analytics"],
            (
                "Complete a course on product experimentation",
                "Take a course covering hypotheses, A/B test design, sample "
                "size and interpreting results.",
            ),
            (
                "Design one product experiment",
                "Write an experiment plan for a real product change: hypothesis, "
                "metric, sample size estimate and decision rule.",
            ),
        ),
        # --- non-technical ---------------------------------------------------
        _competency(
            "technical_presentation",
            "Presenting technical work",
            NON_TECHNICAL,
            ["presentation", "presentations", "presenting", "public speaking", "demo"],
            (
                "Complete a short course on presenting technical work",
                "Take a short course on structuring and delivering technical "
                "presentations for mixed audiences.",
            ),
            (
                "Present one of your projects to a non-technical audience",
                "Prepare and deliver a 10-minute presentation explaining "
                "{anchor} to a non-technical audience, then collect written "
                "feedback on clarity from at least two listeners.",
            ),
            ["communication"],
        ),
        _competency(
            "documentation",
            "Technical documentation",
            NON_TECHNICAL,
            ["documentation", "technical writing", "readme", "prd", "specs"],
            (
                "Complete a short technical writing course",
                "Take a technical writing course covering audience, structure, "
                "and documenting decisions.",
            ),
            (
                "Write clear documentation for existing work",
                "Write a README for {anchor} that explains its purpose, setup, "
                "design decisions and limitations, and ask a peer to follow it.",
            ),
            ["communication"],
        ),
        _competency(
            "stakeholder_communication",
            "Stakeholder and client communication",
            NON_TECHNICAL,
            [
                "stakeholder communication",
                "client communication",
                "stakeholder management",
            ],
            (
                "Complete a course on stakeholder communication",
                "Take a course on stakeholder communication covering status "
                "updates, expectation setting and difficult conversations.",
            ),
            (
                "Send a structured status update to a stakeholder",
                "Write and send a status update about {anchor} covering "
                "progress, risks and next steps, and record the response.",
            ),
            ["communication"],
        ),
        _competency(
            "collaboration",
            "Collaboration and teamwork",
            NON_TECHNICAL,
            ["collaboration", "teamwork", "pair programming", "team collaboration"],
            (
                "Complete a short course on effective team collaboration",
                "Take a short course on collaboration practices such as shared "
                "ownership, handoffs and constructive disagreement.",
            ),
            (
                "Deliver a small piece of work with a teammate",
                "Pair with a teammate on one small task, agree on a split of "
                "responsibilities up front, and write a short joint summary "
                "of what each person contributed.",
            ),
            ["teamwork_collaboration"],
        ),
        _competency(
            "feedback_assimilation",
            "Receiving and applying feedback",
            NON_TECHNICAL,
            [
                "feedback",
                "receiving feedback",
                "applying feedback",
                "feedback assimilation",
                "incorporating feedback",
            ],
            (
                "Complete a short course on giving and receiving feedback",
                "Take a short course on receiving feedback, separating the "
                "message from the delivery, and turning it into action.",
            ),
            (
                "Request feedback on existing work and apply it visibly",
                "Ask a mentor or peer to review {anchor}, list each point of "
                "feedback, apply the changes, and document what changed and why.",
            ),
            ["adaptability_learning"],
        ),
        _competency(
            "retrospective_execution",
            "Running and acting on retrospectives",
            NON_TECHNICAL,
            ["retrospective", "retrospectives", "retro", "lessons learned"],
            (
                "Complete a short course on agile retrospectives",
                "Take a short course on retrospective formats and on turning "
                "retrospective outcomes into tracked actions.",
            ),
            (
                "Run a retrospective and follow up on its actions",
                "Run a 30-minute retrospective on {anchor}, record three "
                "concrete actions, and report two weeks later on which ones "
                "were completed.",
            ),
            ["adaptability_learning"],
        ),
        _competency(
            "prioritization",
            "Prioritization and roadmapping",
            NON_TECHNICAL,
            ["prioritization", "prioritisation", "roadmapping", "backlog management"],
            (
                "Complete a course on product prioritization",
                "Take a course covering prioritization frameworks, roadmaps "
                "and communicating trade-offs.",
            ),
            (
                "Prioritize a real backlog and justify the order",
                "Rank ten real backlog items with a stated framework and write "
                "a short justification for the top three and the bottom three.",
            ),
            ["time_task_management"],
        ),
    )
}


def _role_competency(
    key: str,
    importance: Importance,
    required_level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE,
) -> CompetencyRequirement:
    return COMPETENCY_LIBRARY[key].model_copy(
        update={"importance": importance, "required_level": required_level}
    )


AI_ENGINEER = RoleDefinition(
    role_id="ai_engineer",
    title="AI Engineer",
    aliases=["ai engineering", "machine learning engineer", "ml engineer"],
    competencies=[
        _role_competency("python", CRITICAL),
        _role_competency("apis", CRITICAL),
        _role_competency("machine_learning", CRITICAL),
        _role_competency("software_engineering", CRITICAL),
        _role_competency("rag_pipelines", IMPORTANT),
        _role_competency("testing", IMPORTANT),
        _role_competency("sql", IMPORTANT),
        _role_competency("data_analysis", IMPORTANT),
        _role_competency("system_design", IMPORTANT, ProficiencyLevel.BEGINNER),
        _role_competency("technical_presentation", CRITICAL),
        _role_competency("collaboration", CRITICAL),
        _role_competency("feedback_assimilation", CRITICAL),
        _role_competency("documentation", IMPORTANT),
        _role_competency("stakeholder_communication", IMPORTANT),
        _role_competency("retrospective_execution", IMPORTANT),
    ],
    project=ActionTemplate(
        title="Build an end-to-end portfolio project",
        action=(
            "Design and build a small end-to-end application that exercises "
            "{competencies}. Include automated tests, a README explaining your "
            "design decisions, and a short demo recording, then ask a mentor "
            "to review it."
        ),
    ),
)

PRODUCT_MANAGER = RoleDefinition(
    role_id="product_manager",
    title="Product Manager",
    aliases=["product management", "pm", "product owner"],
    competencies=[
        _role_competency("data_analysis", CRITICAL),
        _role_competency("experimentation", IMPORTANT),
        _role_competency("ai_product_literacy", IMPORTANT),
        _role_competency("sql", IMPORTANT, ProficiencyLevel.BEGINNER),
        _role_competency("stakeholder_communication", CRITICAL),
        _role_competency("technical_presentation", CRITICAL),
        _role_competency("collaboration", CRITICAL),
        _role_competency("prioritization", CRITICAL),
        _role_competency("feedback_assimilation", IMPORTANT),
        _role_competency("documentation", IMPORTANT),
        _role_competency("retrospective_execution", IMPORTANT),
    ],
    project=ActionTemplate(
        title="Run a product discovery mini-project",
        action=(
            "Pick a real user problem and produce a product brief that "
            "demonstrates {competencies}: define the success metric, support "
            "decisions with data, and review the brief with a mentor."
        ),
    ),
)


class RoleRegistry:
    """Looks up a role by id, title or alias, and validates role definitions."""

    def __init__(self, roles: Iterable[RoleDefinition]) -> None:
        self._roles: dict[str, RoleDefinition] = {}
        self._index: dict[str, str] = {}
        for role in roles:
            self.register(role)

    def register(self, role: RoleDefinition) -> None:
        if role.role_id in self._roles:
            raise ValueError(f"Role '{role.role_id}' is already registered.")
        for competency in role.competencies:
            unknown = set(competency.taxonomy_tags) - ALLOWED_TAXONOMY_SET
            if unknown:
                raise ValueError(
                    f"Competency '{competency.key}' uses tags outside the shared "
                    f"taxonomy: {', '.join(sorted(unknown))}"
                )
        self._roles[role.role_id] = role
        for name in (role.role_id, role.title, *role.aliases):
            self._index[normalize(name)] = role.role_id

    def resolve(self, target_role: str) -> RoleDefinition | None:
        return self._roles.get(self._index.get(normalize(target_role), ""))

    @property
    def titles(self) -> list[str]:
        return sorted(role.title for role in self._roles.values())


DEFAULT_ROLE_REGISTRY = RoleRegistry([AI_ENGINEER, PRODUCT_MANAGER])
