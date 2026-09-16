# Booking Analytics Package

!![CI Build](https://github.com/AwenegRooney/skye8-ds-aweneg-rooney/actions/workflows/ci.yml/badge.svg)

[LIVE URL](https://skye8-ds-aweneg-rooney.onrender.com)

A Python package for analyzing interurban transport booking data, verifying schema integrity, and evaluating operational booking dynamics.

## Overview

This package structures data processing routines for interurban transit datasets, enabling seamless data ingestion, model validation, and SQL-driven analytical pipelines.
- Database: Local PostgreSQL.

## Project Layout

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
    ├── conflict-note.md
    ├── findings.md
│   └── load_decisions.md
├── sql/
    ├── analytics.sql
    ├── exercise.sql
    └── schema.sql
├── src/
│   └── booking_analytics/
│       ├── __init__.py
        ├── cli.py
        ├── data_cleaner.py
        ├── db.py
        ├── loader.py
│       └── validated_retention.py
├── tests/
│   ├── __init__.py
    ├── conftest.py
    ├── test_basic.py
    ├── test_parsing.py
│   └── test_pipeline.py
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```

## Installation

Create a clean virtual environment and install in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## QuickStart

Execute the CLI to verify installation:

```bash
booking-analytics
```

Run the test suite to ensure everything is functioning correctly:

```bash
# Code formatting check
black --check .

# Code linting
ruff check .

# Static type checking
mypy src/

# Run tests
pytest
```

## Results Summary

- Configured build system with `pyproject.toml` supporting ediatable mode (`pip install -e .[dev]`).
- Enforce strict type hint coverge with `mypy` and code formatting with `black` and fast linting via ruff.
- Integrated pre-commit configuration ensuring checks run prior to accepting any commit.
- Configured GitHub Actions pipeline to validate code style, type annotations, and test passes on every push.