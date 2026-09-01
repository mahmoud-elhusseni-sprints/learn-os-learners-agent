# System Architecture

## 1. Overview

The Professional Learner Graph system converts learner activity and other sources of evidence into a structured professional graph.

The backend application is implemented using FastAPI and communicates with Neo4j through the repository and graph layers.

The main architectural flow is:

```text
Data Sources
     |
     v
Preprocessing
     |
     v
Ingestion
     |
     v
Neo4j Graph Database
     ^
     |
Repositories
     ^
     |
Services <---- AI Agents
     ^
     |
API Routes
     ^
     |
Frontend / API Client
```

Each layer has a specific responsibility and should not duplicate responsibilities belonging to another layer.

---

## 2. Repository Structure

The backend application is contained inside `src/app/`.

```text
src/
└── app/
    ├── api/
    │   └── routes/
    │
    ├── agents/
    │
    ├── core/
    │
    ├── graph/
    │
    ├── ingestion/
    │
    ├── models/
    │
    ├── repositories/
    │
    ├── schemas/
    │
    ├── services/
    │
    └── main.py

tests/

docs/

.github/
```

Each directory has a specific responsibility.

---

## 3. `src/app/main.py`

`main.py` is the FastAPI application entry point.

Its responsibilities include:

* Creating the FastAPI application.
* Registering API routers.
* Configuring application-level settings when necessary.

Business logic should not be implemented directly in `main.py`.

Conceptually:

```text
main.py
   |
   +-- health router
   +-- learners router
   +-- talent router
   +-- assessment router
```

---

## 4. `src/app/api/routes/`

Routes define the HTTP API exposed by the backend.

Current route groups include:

```text
src/app/api/routes/

├── health.py
├── learners.py
├── talent.py
└── assessment.py
```

A route should:

1. Receive an HTTP request.
2. Validate the request using a schema.
3. Call the appropriate service.
4. Return the service result using the appropriate response schema.

Routes should not contain database queries or complex business logic.

The expected flow is:

```text
HTTP Request
     |
     v
API Route
     |
     v
Service
     |
     v
Response
```

---

## 5. `src/app/schemas/`

Schemas define the structure of data entering and leaving the API.

They are implemented using Pydantic models.

Examples include:

```text
LearnerRequest
LearnerResponse

TalentSearchRequest
TalentSearchResponse
CandidateComparisonRequest
CandidateComparisonResponse

AssessmentRequest
AssessmentResponse
AssessmentResultRequest
AssessmentResultResponse
```

Schemas are responsible for:

* Request validation.
* Response validation.
* Defining API contracts.
* Making expected data structures explicit.

Schemas should not perform database operations or contain business logic.

---

## 6. `src/app/services/`

Services contain application and business logic.

Current services include:

```text
src/app/services/

├── learner_service.py
├── talent_service.py
└── assessment_service.py
```

A service receives validated data from a route and determines what operation should be performed.

Example:

```text
Talent Route
     |
     v
Talent Service
     |
     v
Talent Repository
```

Services should not contain raw HTTP handling or direct request parsing.

---

## 7. `src/app/repositories/`

Repositories handle access to persistent data.

For the graph-based system, repositories communicate with the graph layer and perform the required database operations.

Example:

```text
talent_service.py
       |
       v
talent_repository.py
       |
       v
graph/queries.py
       |
       v
Neo4j
```

The repository layer separates database access from business logic.

Repositories should contain database-access operations rather than API or AI-specific logic.

---

## 8. `src/app/graph/`

The graph module contains Neo4j-specific functionality.

Expected components include:

```text
graph/

├── connections.py
├── schema.py
├── queries.py
└── constraints.py
```



### `connections.py`

Responsible for creating and managing the Neo4j driver/connection.

### `schema.py`

Defines the expected graph structure, including nodes and relationships.

Examples:

```text
Learner
Skill
Assessment
Evidence
Task
Project
```

Relationships may include:

```text
Learner --HAS_SKILL--> Skill
Learner --HAS_EVIDENCE--> Evidence
Learner --TOOK--> Assessment
Evidence --SUPPORTS--> Skill
```

The final graph model should be agreed upon by the relevant team members before major changes are made.

### `queries.py`

Contains reusable Cypher queries for retrieving and modifying graph data.

Examples:

```text
get learner
get learner skills
get learner evidence
search candidates
get assessment
```

### `constraints.py`

Contains Neo4j constraints and indexes required to maintain data integrity and improve query performance.

---

## 9. `src/app/ingestion/`

The ingestion layer transfers processed external data into the graph.

The expected pipeline is:

```text
Raw Data
   |
   v
Preprocessing
   |
   v
Clean / Structured Data
   |
   v
Ingestion
   |
   v
Neo4j
```

Different data sources may have separate preprocessing pipelines, but they should eventually produce data in an agreed format that the ingestion layer can load into the graph.

The ingestion layer should focus on transforming and loading data rather than implementing API or business logic.

---

## 10. `src/app/agents/`

Agents contain AI/LLM-based functionality.

Agents are responsible for:

* Interpreting natural-language requests.
* Performing AI-specific reasoning.
* Calling defined tools or services.
* Producing AI-related responses.

Agents should not directly implement all database logic.

They should use defined services or tools to access system data.

Example:

```text
User Request
     |
     v
AI Agent
     |
     v
Service / Tool
     |
     v
Repository
     |
     v
Neo4j
```

---

## 11. `src/app/models/`

Models represent internal/domain objects when the application requires them.

They are different from API schemas.

* Schemas primarily define API input/output contracts.
* Models represent application/domain concepts used internally.

The exact model structure may evolve as implementation progresses.

---

## 12. `src/app/core/`

The core module contains shared application infrastructure and configuration.

Potential responsibilities include:

* Environment configuration.
* Shared constants.
* Application settings.
* Common utilities required across multiple modules.

Secrets must never be hard-coded in this directory.

---

## 13. Tests

Automated tests are located under:

```text
tests/
```

Example:

```text
tests/
├── test_health.py
├── test_learners.py
├── test_talent.py
└── test_assessment.py
```

Tests should verify the behavior of the corresponding application components.

New functionality should include appropriate tests whenever practical.

Tests are also executed automatically by the CI pipeline.

---

## 14. Layer Responsibilities

The main responsibilities of each layer are:

```text
API Routes       → HTTP/API handling

Schemas          → Request/response validation and contracts

Services         → Business/application logic

Repositories     → Database access

Graph            → Neo4j-specific functionality

Agents           → AI/LLM reasoning and tool use

Ingestion        → Loading processed data

Models           → Internal/domain representations

Core             → Shared configuration/infrastructure
```

Avoid placing functionality in a layer that belongs to another layer.

For example:

* Do not put Cypher queries inside API routes.
* Do not put business logic inside schemas.
* Do not put HTTP handling inside repositories.
* Do not make AI agents directly manage database connections.
* Do not hard-code secrets in application code.

---

## 15. End-to-End Example

For a request such as:

```text
"What are the best five candidates for this job?"
```

the expected architecture is:

```text
Client
  |
  v
Talent Route
  |
  v
AI Agent / Requirement Parser
  |
  v
Extracted Job Requirements
  |
  v
Talent Service
  |
  v
Talent Repository
  |
  v
Graph Queries
  |
  v
Neo4j
  |
  v
Candidate Evidence
  |
  v
Service / Agent
  |
  v
Talent Response
  |
  v
Client
```

The exact division between the AI agent, service, and repository may evolve as implementation progresses.

---

## 16. Architecture Principle

The project follows a separation-of-responsibilities approach.

Each component should have a clear purpose and communicate with the appropriate layer.

```text
Frontend / API Client
          |
          v
      API Routes
          |
          v
        Schemas
          |
          v
       Services
          |
          v
    Repositories
          |
          v
        Graph
          |
          v
        Neo4j
```

AI agents can interact with services and tools when AI-based reasoning is required:

```text
User
 |
 v
AI Agent
 |
 v
Services / Tools
 |
 v
Repositories
 |
 v
Neo4j
```

Changes to shared interfaces such as schemas, graph structures, repository interfaces, service interfaces, or agent inputs/outputs should be communicated with the relevant team members before implementation.
