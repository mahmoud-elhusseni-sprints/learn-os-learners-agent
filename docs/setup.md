# Development Setup Guide

## 1. Overview

This document explains how to set up and run the Professional Learner Graph project on a clean development machine.

The project uses:

* Python 3.11
* FastAPI for the backend API
* Neo4j for the graph database
* Docker and Docker Compose for the development environment
* Ruff for linting
* Black for code formatting
* MyPy for type checking
* Pytest for automated tests
* GitHub Actions for continuous integration

**Docker is the standard development environment for this project.**

Developers do not need to create a local Python virtual environment or install Ruff, Black, MyPy, or Pytest manually. These tools are installed inside the API Docker image.

---

## 2. Prerequisites

Install the following before starting:

* Git
* Docker
* Docker Compose

Verify Docker:

```bash
docker --version
```

Verify Docker Compose:

```bash
docker compose version
```

Python does not need to be installed locally to run the application or development checks because the project runs through Docker.

---

## 3. Clone the Repository

Clone the repository:

```bash
git clone <REPOSITORY_URL>
```

Enter the project directory:

```bash
cd learn-os-learners-agent
```

---

## 4. Environment Variables

The repository contains an `.env.example` file.

Create your local environment file:

```bash
cp .env.example .env
```

Configure the required values in `.env`.

Example:

```env
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
```

The `.env` file is local to your machine and must not be committed to Git.

Never commit:

* passwords
* API keys
* access tokens
* private credentials
* other secrets

---

## 5. Build and Start the Application

Build the Docker images and start the services:

```bash
docker compose up -d --build
```

Check the running containers:

```bash
docker compose ps
```

The expected services are:

```text
API
Neo4j
```

The `--build` option should be used after changes to the Dockerfile, `pyproject.toml`, or other files that affect the Docker image.

---

## 6. Access the API

The FastAPI application runs on port `8000`.

Open:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

The Swagger/OpenAPI interface allows developers to inspect and test the available API endpoints.

---

## 7. Access Neo4j

Neo4j Browser is available at:

```text
http://localhost:7474
```

Use the credentials configured in `.env`.

The Python backend communicates with Neo4j using:

```text
bolt://neo4j:7687
```

Inside Docker Compose, `neo4j` is the service name used by the API container to reach the Neo4j container.

---

## 8. Database Persistence

Neo4j uses a Docker volume to persist database data.

The volume is defined in `docker-compose.yml`:

```yaml
volumes:
  neo4j_data:
```

The Neo4j service mounts the volume to its data directory:

```yaml
volumes:
  - neo4j_data:/data
```

Restarting or recreating the Neo4j container does not automatically remove the stored database data.

---

## 9. Stop the Application

To stop the containers:

```bash
docker compose down
```

The database volume is preserved.

To stop the containers and remove the database volume:

```bash
docker compose down -v
```

**Warning:** `docker compose down -v` deletes the local Neo4j database data.

---

## 10. View Logs

View all service logs:

```bash
docker compose logs
```

View API logs:

```bash
docker compose logs api
```

View Neo4j logs:

```bash
docker compose logs neo4j
```

Follow logs continuously:

```bash
docker compose logs -f
```

To stop following the logs, press:

```text
Ctrl+C
```

This stops viewing the logs; it does not stop the containers.

---

# 11. Development Checks

Ruff, Black, MyPy, and Pytest are installed inside the API Docker image.

Developers should run these tools through Docker rather than installing them locally.

## Run All Checks

The recommended command before pushing a feature branch is:

```bash
docker compose run --rm api bash -c "ruff check . && black --check . && mypy src && pytest"
```

This runs all checks in sequence:

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
```

If a check fails, fix the reported problem and run the complete command again.

A successful run should end with all checks passing and the test suite completing successfully.

---

## 12. Ruff

Ruff checks Python code for linting and code-quality problems.

Run:

```bash
docker compose run --rm api ruff check .
```

If Ruff reports automatically fixable issues:

```bash
docker compose run --rm api ruff check . --fix
```

Run Ruff again afterward:

```bash
docker compose run --rm api ruff check .
```

---

## 13. Black

Black checks that Python files follow the project's formatting rules.

Check formatting:

```bash
docker compose run --rm api black --check .
```

If files need formatting:

```bash
docker compose run --rm api black .
```

Then check again:

```bash
docker compose run --rm api black --check .
```

---

## 14. MyPy

MyPy checks Python type annotations.

Run:

```bash
docker compose run --rm api mypy src
```

New functions should include appropriate return and parameter type annotations.

---

## 15. Pytest

Tests are located under:

```text
tests/
```

Run the test suite:

```bash
docker compose run --rm api pytest
```

The project should not be merged when its tests are failing.

New functionality should include appropriate tests.

---

## 16. Running a Feature During Development

The application can be started with:

```bash
docker compose up
```

or in the background:

```bash
docker compose up -d
```

When the application is running, the API is available at:

```text
http://localhost:8000
```

To stop following `docker compose up` logs, press:

```text
Ctrl+C
```

If the terminal becomes unavailable while the application is running, open another terminal. The containers continue running independently.

---

## 17. Troubleshooting

### Containers are not starting

Check their status:

```bash
docker compose ps
```

Then inspect the logs:

```bash
docker compose logs
```

For API-specific logs:

```bash
docker compose logs api
```

For Neo4j:

```bash
docker compose logs neo4j
```

### Neo4j is unhealthy

Check:

```bash
docker compose logs neo4j
```

Make sure the configured Neo4j password is correct and that the required ports are available.

### Port 8000 is already in use

Another application may already be using port `8000`.

Stop the conflicting application or change the host port in `docker-compose.yml`.

### Port 7474 is already in use

Another Neo4j instance or application may already be using port `7474`.

Stop the conflicting service or change the host port.

### Development tools are not found

If you see:

```text
ruff: command not found
```

or:

```text
black: command not found
```

the Docker image may not have been rebuilt after a dependency change.

Rebuild it:

```bash
docker compose up -d --build
```

Then verify the tools:

```bash
docker compose run --rm api ruff --version
docker compose run --rm api black --version
docker compose run --rm api mypy --version
docker compose run --rm api pytest --version
```

---

## 18. Development Principles

All developers should use the same repository structure and Docker-based development environment.

Application code belongs under:

```text
src/app/
```

Tests belong under:

```text
tests/
```

Documentation belongs under:

```text
docs/
```

Do not commit:

* `.env`
* passwords
* API keys
* access tokens
* private credentials
* local virtual environments
* generated cache files

The development tools should be defined in `pyproject.toml` and installed through the Docker image so that all developers and CI use the same tool configuration.
