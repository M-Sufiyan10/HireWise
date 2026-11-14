"""Shared pytest fixtures.

Tests run against a dedicated, throwaway database (``HireWise_test`` by default,
override with TEST_MONGO_DB_NAME) so they never touch real resume data.
DB tests are skipped automatically when MongoDB is not reachable.
"""
import os

import pytest
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/")
TEST_DB_NAME = os.getenv("TEST_MONGO_DB_NAME", "HireWise_test")
os.environ["MONGO_DB_NAME"] = TEST_DB_NAME


@pytest.fixture
def db():
    from Db import ResumeDatabase

    try:
        database = ResumeDatabase(db_name=TEST_DB_NAME)
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"MongoDB not available: {e}")

    database.collection.delete_many({})
    yield database
    if database.client is not None:
        database.client.drop_database(TEST_DB_NAME)
        database.close_connection()
