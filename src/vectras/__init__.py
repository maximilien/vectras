# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from __future__ import annotations

from dotenv import find_dotenv, load_dotenv

# Load variables from a local .env file if present. Do not override existing env.
# This ensures services work when started directly (e.g., via test runners) without sourcing the shell.
_dotenv_path = find_dotenv(usecwd=True)
if _dotenv_path:
    load_dotenv(dotenv_path=_dotenv_path, override=False)

__all__ = ["__version__"]

__version__ = "0.1.0"
