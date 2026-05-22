"""Shared database registry for tests and modules.

KDM originally had a few route files that instantiated their own Motor client.
This registry allows server.py/test_server.py to inject the same db reference,
which improves testability and avoids mock Mongo isolation issues.
"""

_db = None


def set_database(database):
    global _db
    _db = database
    return _db


def get_database():
    if _db is None:
        raise RuntimeError("Database not initialized. Call set_database(db) from server.py")
    return _db
