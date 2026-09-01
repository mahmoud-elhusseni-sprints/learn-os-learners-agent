# Development Workflow

## 1. General Rule

Do not push directly to the `main` branch.

Every developer should work on a separate feature branch and create a Pull Request when their work is ready.

The workflow is:

```text
main
  ^
  |
Pull Request
  ^
  |
Feature Branch
  ^
  |
Developer
```

The `main` branch should always contain code that is stable and ready for integration.

---

## 2. Create a Feature Branch

Before starting work, make sure your local `main` branch is up to date:

```bash
git checkout main
git pull origin main
```

Create a new feature branch:

```bash
git checkout -b feature/your-feature-name
```

Examples:

```bash
git checkout -b feature/graph-schema
git checkout -b feature/meeting-ingestion
git checkout -b feature/ai-agent
git checkout -b feature/talent-service
```

Use a short and descriptive branch name that reflects the feature being developed.

---

## 3. Work in the Correct Directory

Follow the repository architecture when adding or modifying code.

The current project structure is:

```text
src/app/
├── api/
│   └── routes/          → API endpoints
├── agents/              → AI agents
├── core/                → Shared configuration and core functionality
├── graph/               → Neo4j graph functionality
├── ingestion/           → Data ingestion and preprocessing
├── models/              → Domain/internal models
├── repositories/        → Database access
├── schemas/             → API request/response schemas
└── services/            → Business logic

tests/                   → Automated tests

docs/                    → Project documentation
```

Examples:

```text
src/app/api/routes/       → FastAPI routes
src/app/agents/           → AI agents
src/app/core/             → Configuration
src/app/graph/            → Neo4j queries, schema, constraints, connections
src/app/ingestion/        → Data loading and ingestion
src/app/models/           → Internal/domain models
src/app/repositories/     → Database operations
src/app/schemas/          → Pydantic schemas
src/app/services/         → Business logic
tests/                    → Automated tests
docs/                     → Documentation
```

Do not create duplicate implementations in random directories.

Before creating a new file, check whether the required functionality already belongs in an existing module.

---

## 4. Running the Project with Docker

The project uses Docker and Docker Compose as the standard development environment.

Developers do **not** need to create a Python virtual environment for this project.

Python dependencies and development tools such as Ruff, Black, MyPy, and Pytest are installed inside the Docker API image.

### Start the application

From the project root:

```bash
docker compose up --build
```

The first build may take some time because Docker may need to download the Python base image, Neo4j image, and Python dependencies.

After the containers start successfully:

```text
FastAPI API
    ↓
Docker
    ↓
Neo4j
```

The FastAPI application runs on:

```text
http://localhost:8000
```

FastAPI Swagger documentation:

```text
http://localhost:8000/docs
```

Neo4j Browser:

```text
http://localhost:7474
```

### Start without rebuilding

If there are no changes to the Dockerfile or Python dependencies:

```bash
docker compose up
```

### Run in the background

To start the services without attaching to their logs:

```bash
docker compose up -d
```

### Stop the services

If the application is running in the foreground:

```text
CTRL+C
```

Or stop the services from another terminal:

```bash
docker compose down
```

---

## 5. Write Tests

New functionality should include appropriate tests.

Tests belong under:

```text
tests/
```

For example:

```text
tests/
├── test_health.py
├── test_learners.py
├── test_talent.py
└── test_assessments.py
```

Tests are executed inside the Docker API container.

Run:

```bash
docker compose run --rm api pytest
```

A successful test run should report that all collected tests passed.

For example:

```text
1 passed
```

A Pull Request should not be merged while its tests are failing unless the team has explicitly agreed on the reason for the failure.

---

## 6. Ruff

Ruff is used for Python linting and import checking.

Ruff is installed inside the Docker API image.

Run Ruff with:

```bash
docker compose run --rm api ruff check .
```

A successful result should be:

```text
All checks passed!
```

If Ruff reports automatically fixable issues, they can be fixed with:

```bash
docker compose run --rm api ruff check . --fix
```

After fixing, run the check again:

```bash
docker compose run --rm api ruff check .
```

Do not ignore Ruff errors without understanding why they occur.

---

## 7. Black

Black is used to maintain consistent Python formatting across the project.

Black is installed inside the Docker API image.

### Check formatting

Run:

```bash
docker compose run --rm api black --check .
```

If Black reports that files would be reformatted, format the project with:

```bash
docker compose run --rm api black .
```

Then verify the formatting again:

```bash
docker compose run --rm api black --check .
```

A successful check should report that the files would be left unchanged.

---

## 8. MyPy

MyPy is used for static type checking.

Run MyPy inside the Docker API container:

```bash
docker compose run --rm api mypy src
```

A successful result should look similar to:

```text
Success: no issues found in ... source files
```

Developers should provide appropriate type annotations for functions, parameters, and return values.

When adding new functionality, make sure it does not introduce new MyPy errors.

---

## 9. Run All Checks Locally

Before pushing a feature branch, run all project checks through Docker:

```bash
docker compose run --rm api bash -c "ruff check . && black --check . && mypy src && pytest"
```

The checks run in this order:

```text
Ruff
  |
  v
Black
  |
  v
MyPy
  |
  v
Pytest
  |
  v
PASS / FAIL
```

The command stops if one of the checks fails.

All checks should pass before pushing the branch or creating/updating a Pull Request.

### Individual commands

Ruff:

```bash
docker compose run --rm api ruff check .
```

Black:

```bash
docker compose run --rm api black --check .
```

MyPy:

```bash
docker compose run --rm api mypy src
```

Pytest:

```bash
docker compose run --rm api pytest
```

---

## 10. Review Changes Before Committing

Before committing, check which files have been modified:

```bash
git status
```

Review the actual changes:

```bash
git diff
```

Make sure you are not accidentally committing generated or local files such as:

```text
.venv/
__pycache__/
.pytest_cache/
.env
```

Secrets, passwords, API keys, tokens, and other private credentials must never be committed.

---

## 11. Commit Changes

Stage your changes:

```bash
git add .
```

Create a descriptive commit:

```bash
git commit -m "Add graph schema"
```

Good commit messages describe what was added or changed.

Examples:

```text
Add learner endpoints
Add graph constraints
Implement meeting ingestion
Add talent search service
Add assessment schemas
Add employer agent
```

Avoid vague commit messages such as:

```text
update
changes
fix
test
stuff
```

---

## 12. Push Your Branch

Push your feature branch to GitHub:

```bash
git push -u origin feature/your-feature-name
```

After pushing, create a Pull Request targeting:

```text
main
```

Do not push directly to `main`.

---

## 13. Continuous Integration

GitHub Actions automatically runs the CI workflow when a Pull Request targeting `main` is created or updated.

The CI workflow performs the same quality checks used during local Docker development:

```text
Pull Request
     |
     v
GitHub Actions
     |
     +---- Install dependencies
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
PASS / FAIL
```

Developers should run the checks locally before pushing:

```bash
docker compose run --rm api bash -c "ruff check . && black --check . && mypy src && pytest"
```

This helps identify problems before the Pull Request reaches CI.

Developers do not normally need to manually trigger CI for standard Pull Requests.

---

## 14. Pull Request Rules

Before requesting a review, verify:

* Code is implemented in the correct directory.
* Tests have been added or updated when appropriate.
* Ruff passes.
* Black passes.
* MyPy passes.
* Pytest passes.
* No secrets or credentials are included.
* The Docker application starts successfully when relevant.
* The Pull Request has a clear description.
* The changes are limited to the intended feature.

Do not merge a Pull Request with failing CI checks unless the team has explicitly agreed that the failure is unrelated and will be fixed separately.

---

## 15. Keeping Your Branch Updated

Because multiple developers work simultaneously, `main` may change while you are working.

Update your local `main` branch regularly:

```bash
git checkout main
git pull origin main
```

Then return to your feature branch:

```bash
git checkout feature/your-feature-name
```

Update the feature branch using the Git strategy agreed upon by the team.

For example, if the team uses rebase:

```bash
git rebase main
```

If merge is preferred:

```bash
git merge main
```

If conflicts occur, resolve them carefully and run the complete Docker check again:

```bash
docker compose run --rm api bash -c "ruff check . && black --check . && mypy src && pytest"
```

---

## 16. Dependency Changes

If your feature requires a new Python package, add it to:

```text
pyproject.toml
```

Do not install a dependency only on your own machine and assume other developers have it.

For example, the Neo4j Python driver is declared as a project dependency in `pyproject.toml`.

After changing `pyproject.toml`, rebuild the API image:

```bash
docker compose up -d --build
```

This ensures that the updated dependencies are installed inside Docker.

You can verify that the package is available inside the container if necessary:

```bash
docker compose run --rm api python -m pip show package-name
```

---

## 17. Environment Variables and Secrets

Never commit `.env`.

The repository should contain:

```text
.env.example
```

This file documents the required configuration variables without exposing real secrets.

Each developer should create their own `.env` based on the example:

```bash
cp .env.example .env
```

Then add their local configuration values.

Never commit:

* passwords
* API keys
* access tokens
* private credentials
* secret configuration files

Make sure `.env` is included in `.gitignore`.

---

## 18. Code Ownership and Shared Interfaces

The repository is a shared codebase.

Each team member should communicate with the relevant developers when modifying shared interfaces such as:

* Graph schemas
* API schemas
* Repository interfaces
* Service interfaces
* Agent inputs and outputs
* Data ingestion formats

Changes to shared contracts should be discussed before implementation because they may affect multiple components.

For example, changing a Pydantic schema used by an API route may also require changes to:

```text
Route
  ↓
Service
  ↓
Repository
  ↓
Neo4j
```

Similarly, changing an agent's input/output format may affect the service or API layer using that agent.

---

## 19. Integration Principle

The goal is not for each team member to build an isolated application.

All components must integrate into the same architecture:

```text
                 API Client
                     |
                     v
              Routes / Agents
                     |
                     v
                  Services
                     |
                     v
               Repositories
                     |
                     v
                   Neo4j

Data Sources
     |
     v
Preprocessing
     |
     v
Ingestion
     |
     v
Neo4j
```

The main application layers should have clear responsibilities:

```text
Ingestion
    → Loads and prepares external data

Graph
    → Defines Neo4j schema, queries, constraints, and connections

Repositories
    → Communicate with the database

Services
    → Implement business logic

Agents
    → Implement AI-driven functionality

Routes
    → Expose functionality through the API

Schemas
    → Validate API inputs and outputs
```

When changing an interface, consider how the change affects the layers above and below it.

---

## 20. Recommended Developer Workflow

For every feature, follow this sequence:

```text
1. Update main
       |
       v
2. Create feature branch
       |
       v
3. Implement feature
       |
       v
4. Add/update tests
       |
       v
5. Run Docker application
       |
       v
6. Run Ruff
       |
       v
7. Run Black
       |
       v
8. Run MyPy
       |
       v
9. Run Pytest
       |
       v
10. Review git diff
       |
       v
11. Commit
       |
       v
12. Push feature branch
       |
       v
13. Create Pull Request
       |
       v
14. GitHub Actions CI
       |
       v
15. Code Review
       |
       v
16. Merge into main
```

The goal is to keep `main` stable, keep development environments consistent through Docker, and ensure that every Pull Request passes the project's automated quality checks before being merged.
