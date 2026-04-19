#!/usr/bin/env python
"""
Idempotent superuser creation script for automated deployments.

Reads credentials from environment variables:
  DJANGO_SUPERUSER_USERNAME  (default: admin)
  DJANGO_SUPERUSER_EMAIL     (default: admin@domovi.local)
  DJANGO_SUPERUSER_PASSWORD  (default: admin123)

Skips creation silently if a superuser already exists.
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402 — must come after setup()

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@domovi.local")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123")

if User.objects.filter(is_superuser=True).exists():
    print(f"[create_superuser] Superuser already exists — skipping.")
    sys.exit(0)

User.objects.create_superuser(username=username, email=email, password=password)
print(f"[create_superuser] Superuser '{username}' created successfully.")
