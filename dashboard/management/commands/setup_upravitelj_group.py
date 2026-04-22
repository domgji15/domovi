from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Kreira grupu 'Upravitelji' s potrebnim permisijama"

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name="Upravitelji")

        perm_codenames = [
            ("dashboard", "zaposlenik", "add_zaposlenik"),
            ("dashboard", "zaposlenik", "change_zaposlenik"),
            ("dashboard", "zaposlenik", "view_zaposlenik"),
            ("auth", "user", "add_user"),
            ("auth", "user", "change_user"),
            ("auth", "user", "view_user"),
            ("dashboard", "profil", "add_profil"),
            ("dashboard", "profil", "change_profil"),
            ("dashboard", "profil", "view_profil"),
        ]

        perms = []
        for app_label, model, codename in perm_codenames:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                perm = Permission.objects.get(content_type=ct, codename=codename)
                perms.append(perm)
            except (ContentType.DoesNotExist, Permission.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f"Permisija nije pronađena: {codename} ({e})"))

        group.permissions.set(perms)

        action = "Kreirana" if created else "Ažurirana"
        self.stdout.write(self.style.SUCCESS(
            f"{action} grupa 'Upravitelji' s {len(perms)} permisija."
        ))
        self.stdout.write("")
        self.stdout.write("Kako dodijeliti upravitelja:")
        self.stdout.write("  1. Kreirati korisnika u adminu")
        self.stdout.write("  2. Postaviti is_staff = True")
        self.stdout.write("  3. Dodati u grupu 'Upravitelji'")
        self.stdout.write("  4. Otvoriti/kreirati njihov Profil → role='upravitelj',")
        self.stdout.write("     upravljani_domovi = domovi kojima upravljaju")
