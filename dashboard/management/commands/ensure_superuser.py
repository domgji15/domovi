"""
Django management command: ensure_superuser

Creates a superuser if one does not already exist.
Credentials are read from environment variables with safe defaults.

Usage:
    python manage.py ensure_superuser

Environment variables (all optional):
    DJANGO_SUPERUSER_USERNAME  — default: admin
    DJANGO_SUPERUSER_EMAIL     — default: admin@domovi.local
    DJANGO_SUPERUSER_PASSWORD  — default: admin123
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser if one does not already exist."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@domovi.local").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123").strip()

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser already exists — skipping creation."
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser '{username}' created successfully."
            )
        )
