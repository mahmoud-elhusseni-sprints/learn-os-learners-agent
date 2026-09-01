## Quick Start

1. Clone the repository.
2. Follow `docs/setup.md` to configure Docker and environment variables.
3. Read `docs/architecture.md` to understand where your work belongs.
4. Read `docs/data.md` if your task involves data.
5. Read `docs/development.md` before creating a feature branch or Pull Request.


## Documentation Guide

The `docs/` directory contains the detailed documentation for the project.

The **README.md is the main starting point** for the repository. It provides an overview of the project, explains how to get started, and directs developers to the appropriate documentation for more detailed information.

### Documentation Structure

```text
docs/
├── setup.md
├── architecture.md
├── development.md
└── data.md
```

### `docs/setup.md` — Development Setup

Read this document when setting up the project for the first time.

It explains:

* Required software and prerequisites.
* How to clone the repository.
* How to configure `.env`.
* How to build and start the Docker containers.
* How to access the FastAPI API.
* How to access Neo4j.
* How to stop and restart the application.
* How to view Docker logs.
* Common setup and Docker troubleshooting.

**Use this document when:**
You are a new developer joining the project or need to set up the project on a new machine.

---

### `docs/architecture.md` — System Architecture

Read this document before implementing or modifying backend functionality.

It explains:

* The overall system architecture.
* The repository structure.
* The responsibility of each backend layer.
* API routes.
* Pydantic schemas.
* Services.
* Repositories.
* Neo4j graph functionality.
* Data ingestion.
* AI agents.
* Domain models.
* Core configuration.
* How the different layers communicate.

The main architectural flow is:

```text
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
Graph / Neo4j
```

AI agents and ingestion components integrate with these layers according to the architecture described in `architecture.md`.

**Use this document when:**
You need to know **where new code belongs**, how components communicate, or what responsibility a particular directory has.

---

### `docs/development.md` — Development Workflow

Read this document before starting development work.

It explains the team's development and Git workflow, including:

* Feature branches.
* Pull Requests.
* Commit conventions.
* Running tests.
* Running Ruff.
* Running Black.
* Running MyPy.
* Docker-based development checks.
* GitHub Actions CI.
* Keeping branches synchronized with `main`.
* Dependency changes.
* Environment variables and secrets.
* Code ownership.
* Integration principles.

The standard workflow is:

```text
Create Feature Branch
        |
        v
Implement Feature
        |
        v
Run Docker Checks
        |
        +---- Ruff
        |
        +---- Black
        |
        +---- MyPy
        |
        +---- Pytest
        |
        v
Commit
        |
        v
Push Branch
        |
        v
Create Pull Request
        |
        v
GitHub Actions CI
        |
        v
Code Review
        |
        v
Merge to main
```

**Use this document when:**
You are starting a feature, preparing a Pull Request, running quality checks, or working with Git/GitHub.

---

### `docs/data.md` — Data Guide

Read this document when working with project data.

It explains:

* Where the project data comes from.
* How to obtain the required datasets.
* How data should be prepared.
* Expected data formats.
* How processed data is transferred into the project.
* How data is loaded into Neo4j.
* Where data files should be stored.
* Which data should and should not be committed to Git.
* The expected ingestion workflow.

The general data pipeline is:

```text
External Data Sources
        |
        v
Data Collection
        |
        v
Preprocessing
        |
        v
Structured Data
        |
        v
Ingestion
        |
        v
Neo4j
```

**Use this document when:**
You are collecting, preparing, preprocessing, or loading data into the system.

---

## Where Should I Look?

Use this table as a quick reference:

| If you want to...                               | Read                   |
| ----------------------------------------------- | ---------------------- |
| Set up the project                              | `docs/setup.md`        |
| Start Docker / Neo4j / API                      | `docs/setup.md`        |
| Understand the architecture                     | `docs/architecture.md` |
| Know where to put new code                      | `docs/architecture.md` |
| Understand routes, services, repositories, etc. | `docs/architecture.md` |
| Start a new feature                             | `docs/development.md`  |
| Create a Git branch                             | `docs/development.md`  |
| Run Ruff / Black / MyPy / Pytest                | `docs/development.md`  |
| Understand GitHub Actions CI                    | `docs/development.md`  |
| Create a Pull Request                           | `docs/development.md`  |
| Obtain project data                             | `docs/data.md`         |
| Prepare or preprocess data                      | `docs/data.md`         |
| Load data into Neo4j                            | `docs/data.md`         |
| Understand the data pipeline                    | `docs/data.md`         |

### Recommended Reading Order

For a new team member, follow this order:

```text
README.md
    |
    v
docs/setup.md
    |
    v
docs/architecture.md
    |
    v
docs/data.md
    |
    v
docs/development.md
```

After completing the setup, developers should read the architecture documentation before implementing features.

The README should remain a high-level guide rather than duplicating the detailed documentation. Detailed procedures and rules should be maintained in the appropriate document under `docs/`.
