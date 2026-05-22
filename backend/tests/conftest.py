"""
Pytest shared configuration for the KDMARCHÉ / LOLODRIVE backend tests.

Loads test credentials from `/app/backend/.env.test` so that no password is
hard-coded in test files. Real CI/CD pipelines should override these values
through real environment variables (the file is only a local fallback).
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is a dev dependency; fall back gracefully
    load_dotenv = None  # type: ignore

_ENV_TEST_PATH = Path(__file__).resolve().parent.parent / ".env.test"
if load_dotenv and _ENV_TEST_PATH.exists():
    load_dotenv(_ENV_TEST_PATH, override=False)
