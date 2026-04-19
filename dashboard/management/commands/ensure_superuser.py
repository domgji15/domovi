import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

DEFAULT_USERNAME = "admin"
DEFAULT_EMAIL = "admin@domovi.local"
DEFAULT_PASSWORD = "admin123"


class Command(BaseCommand):
    help = "Create a superuser if one does not already exist (safe to run on every deploy)."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", DEFAULT_USERNAME).strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", DEFAULT_EMAIL).strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", DEFAULT_PASSWORD).strip()

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING("Superuser already exists — skipping creation.")
            )
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(f"Superuser '{username}' created successfully.")
        )
