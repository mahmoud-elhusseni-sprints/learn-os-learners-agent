## Data Location

The processed project data is stored in the project's Hugging Face Dataset repository.

**Dataset:** `<HUGGING_FACE_DATASET_URL>`

The actual processed data is stored externally and is not committed to the GitHub repository.

---

## How to Get the Data

The project uses Hugging Face to store the processed JSONL files.

The required Hugging Face dependencies are installed inside the Docker environment, so developers do not need to install them separately in a local virtual environment.

The ingestion code should retrieve the required files from the Hugging Face Dataset repository.

### 1. Configure the Hugging Face Dataset

Use the dataset URL provided by the team:

```text
<HUGGING_FACE_DATASET_URL>
```

For example:

```text
https://huggingface.co/datasets/<OWNER>/<DATASET_NAME>
```


### 2. Download the Processed Data

From the project root, start the Docker environment:

```bash
docker compose up -d --build
```

The ingestion process can then download the required files from the Hugging Face Dataset.

The expected processed files are:

```text
learners.jsonl
meeting_memory_cards.jsonl
interaction_logs.jsonl
```

The exact filenames and fields must follow:

```text
docs/data_schema.md
```

### 3. Load the Data into Neo4j

After the processed JSONL files have been retrieved, the ingestion loader loads the data into Neo4j.

The expected flow is:

```text
Hugging Face Dataset
        |
        v
Processed JSONL
        |
        v
Ingestion Loader
        |
        v
Neo4j
```

The ingestion team is responsible for ensuring that the downloaded data matches the expected schema before loading it into Neo4j.

### Important

Do not:

* Commit JSONL dataset files to GitHub.
* Hard-code the Hugging Face dataset URL in multiple places.
* Commit Hugging Face access tokens.
* Put real credentials in `.env.example`.
* Change the agreed filenames or field names without coordinating with
