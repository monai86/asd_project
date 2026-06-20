"""Database session placeholder.

The v2 MVP runs in mock repository mode. This module exists so the API boundary
can move to SQLAlchemy or SQLModel without changing route signatures.
"""


def get_db_session():
    return None
