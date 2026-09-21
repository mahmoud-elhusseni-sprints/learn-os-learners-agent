# Full Tests

These scripts exercise the main backend flow in order:

```powershell
python full_test/test_preprocessing.py
python full_test/test_data_loading.py
python full_test/test_agent_questions.py --learner "Learner A4" --question "Did they work with Python?"
```

Run the first script with `--with-llm` only when the LLM environment variables
are configured. The data-loading script requires a reachable Neo4j instance.

For cross-learner evidence questions, omit `--learner`:

```powershell
python full_test/test_agent_questions.py --question "Which learner has the strongest evidence in Python?"
```
