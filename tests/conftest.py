import os
import tempfile

import pytest

_database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_database_file.close()
os.unlink(_database_file.name)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_database_file.name}")
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test")

from src.app.database.base import Base  # noqa: E402
from src.app.database.connection import engine  # noqa: E402
from src.app.models import ConversationSession, Message, User  # noqa: E402, F401


@pytest.fixture(scope="session", autouse=True)
def test_database():
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    if os.path.exists(_database_file.name):
        os.unlink(_database_file.name)
