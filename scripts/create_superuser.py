#!/usr/bin/env python
"""
Standalone script: create_superuser.py

Creates a Django superuser if one does not already exist.
Intended to be run as a pre-deploy or post-migrate step.

Usage:
    python scripts/create_superuser.py

Environment variables (all optional):
    DJANGO_SETTINGS_MODULE     — default: config.settings
    DJANGO_SUPERUSER_USERNAME  — default: admin
    DJANGO_SUPERUSER_EMAIL     — default: admin@domovi.local
    DJANGO_SUPERUSER_PASSWORD  — default: admin123
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: make sure the project root is on sys.path so Django can be
# imported regardless of the working directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402  (import after sys.path manipulation)

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin").strip()
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@domovi.local").strip()
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123").strip()

if User.objects.filter(is_superuser=True).exists():
    print(f"[ensure_superuser] Superuser already exists — skipping creation.")
    sys.exit(0)

User.objects.create_superuser(username=username, email=email, password=password)
print(f"[ensure_superuser] Superuser '{username}' created successfully.")
