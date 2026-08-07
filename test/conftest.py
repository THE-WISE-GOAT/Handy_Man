"""
Shared pytest setup for the Handy_Man / Kamigo backend test suite.

WHY THIS FILE IS NECESSARY
--------------------------
Two backend modules do real work at IMPORT time, which makes the application
impossible to import in a test process without side effects:

  1. `src.database.database` opens a live PostgreSQL connection at module
     level and runs `CREATE EXTENSION IF NOT EXISTS vector;`. Because
     `src/database/__init__.py` re-exports `Base` from it, merely importing
     anything under `src.database` tries to reach a database.

  2. `src.ai.customer_chat_analyser_nvidia` constructs an OpenAI client at
     module level using `os.environ["NVIDIA_API_KEY"]` — a bare subscript,
     so a missing key raises KeyError during import.

Rather than modify application code, this conftest prepares the import
environment BEFORE any `src.*` module is imported:

  * A stub `src.database.database` is pre-seeded into `sys.modules`. Python
    checks `sys.modules` before loading a module from disk, so every later
    `from src.database.database import ...` resolves to the stub and the
    real file — with its connection code — never executes. The stub exposes
    a genuine `declarative_base()` as `Base`, so the ORM classes in
    `src.core.model` still build exactly as they do in production; only the
    network connection is missing.

  * Placeholder environment variables are set so `Settings` validates and
    the NVIDIA client constructs without contacting anything.

TWO IMPORT SPELLINGS
--------------------
The test modules import application code as `backend.src.…`, while the
application imports itself as `src.…` (that is what runs in the container,
where `backend/` IS the working directory). Both spellings therefore appear
in one test process, and left alone Python would load each module twice —
producing two unrelated `Base` objects, two sets of ORM classes, and a real
`database.py` execution through the un-stubbed second path.

A meta-path finder resolves this by aliasing rather than re-loading: any
`backend.src.X` import is served the already-imported `src.X` module object.
One module identity, one `Base`, and the database stub covers both spellings.

Every test in this suite is deterministic and offline: none performs network
I/O and none requires a database.

RUNNING
-------
From the repository root:

    pytest test/

The suite needs the backend's own dependencies (pytest, sqlalchemy, pydantic,
pyjwt, passlib+argon2, geoalchemy2, pgvector, openai, httpx, python-dotenv),
all of which are already in requirements.txt.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import os
import sys
import types
from pathlib import Path

# ── Import path ──────────────────────────────────────────────────────────────
# Two roots are needed, because two import spellings are in play:
#   * `backend/`   — application modules import each other as `src.core...`
#   * repo root    — the test modules import them as `backend.src.core...`
# pytest only adds the rootdir of the test file itself, so both go on the path
# explicitly.
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
for _path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


# ── Environment placeholders ─────────────────────────────────────────────────
# `setdefault` is deliberate: a developer's real .env still wins, so these
# only fill gaps and let a clean CI checkout run with no .env at all.
_ENV_DEFAULTS = {
    "NVIDIA_API_KEY": "nvapi-test-key-never-used",
    "GEMINI_API_KEY": "test-gemini-key-never-used",
    "DATABASE_HOSTNAME": "localhost",
    "DATABASE_PORT": "5432",
    "POSTGRES_EXPOSE_PORT": "5432",
    "DATABASE_NAME": "handyman_test",
    "DATABASE_USERNAME": "test_user",
    "DATABASE_PASSWORD": "test_password",
    "PUBLIC_API_URL": "http://127.0.0.1:8000",
    "SECRET_KEY": "test-secret-key-for-unit-tests-only",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
}
for _key, _value in _ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)


# ── Offline stand-in for the database module ─────────────────────────────────
def _install_database_stub() -> None:
    """
    Pre-seed `sys.modules["src.database.database"]` so the real module — which
    connects to PostgreSQL on import — is never loaded.

    Only the names the rest of the codebase imports from it are required:
    `Base`, `engine`, `SessionLocal`, and `get_db`. `Base` must be a real
    declarative base, because `src.core.model` builds every ORM class on it.
    """
    if "src.database.database" in sys.modules:
        return

    from sqlalchemy.orm import declarative_base

    stub = types.ModuleType("src.database.database")
    stub.__doc__ = "Offline test stub — see test/conftest.py."
    stub.Base = declarative_base()
    stub.engine = None
    stub.SessionLocal = None
    stub.SQLALCHEMY_DATABASE_URL = "postgresql://offline-test-stub"

    def get_db():
        """Fail loudly if a unit test ever tries to hit a real database."""
        raise RuntimeError(
            "get_db() is stubbed out in this suite — these tests are "
            "intentionally database-free."
        )

    stub.get_db = get_db
    sys.modules["src.database.database"] = stub


# ── `backend.src.*` -> `src.*` aliasing ──────────────────────────────────────
_ALIAS_PREFIX = "backend.src"
_REAL_PREFIX = "src"


class _AliasLoader(importlib.abc.Loader):
    """Return the existing `src.*` module instead of loading a second copy."""

    def create_module(self, spec: importlib.machinery.ModuleSpec):
        real_name = _REAL_PREFIX + spec.name[len(_ALIAS_PREFIX):]
        module = importlib.import_module(real_name)
        # Registering under the alias too means later imports short-circuit in
        # sys.modules and never reach this loader again.
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module: types.ModuleType) -> None:
        # Already executed under its real name — running it again would rebuild
        # every ORM class and re-trigger module-level side effects.
        pass


class _AliasFinder(importlib.abc.MetaPathFinder):
    """
    Installed at the front of `sys.meta_path`, so it intercepts before the
    filesystem finder. This is what keeps `backend.src.database.database`
    resolving to the offline stub rather than the real connecting module.
    """

    def find_spec(self, fullname, path=None, target=None):
        if fullname == _ALIAS_PREFIX or fullname.startswith(_ALIAS_PREFIX + "."):
            return importlib.machinery.ModuleSpec(
                fullname, _AliasLoader(), is_package=True
            )
        return None


def _install_alias_finder() -> None:
    if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _AliasFinder())


_install_database_stub()
_install_alias_finder()
