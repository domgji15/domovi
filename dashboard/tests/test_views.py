from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from dashboard.models import Dom, Klijent, Profil


class ViewSecurityTests(TestCase):
    def setUp(self):
        self.klijent = Klijent.objects.create(naziv="Klijent A")
        self.dom = Dom.objects.create(naziv="Dom A", kapacitet=20, klijent=self.klijent)

    def _create_user_with_profile(self, username, role):
        user = User.objects.create_user(username=username, password="test-pass-123")
        Profil.objects.create(user=user, dom=self.dom, role=role)
        return user

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_employee_calendar_forbidden_for_non_employee(self):
        user = self._create_user_with_profile("admin-user", "admin")
        self.client.force_login(user)

        response = self.client.get(reverse("employee_calendar_data"))

        self.assertEqual(response.status_code, 403)

    def test_korisnik_create_forbidden_for_employee(self):
        user = self._create_user_with_profile("employee-user", "zaposlenik")
        self.client.force_login(user)

        response = self.client.get(reverse("korisnik_create"))

        self.assertEqual(response.status_code, 403)

    def test_financije_forbidden_for_employee(self):
        user = self._create_user_with_profile("employee-fin", "zaposlenik")
        self.client.force_login(user)

        response = self.client.get(reverse("financije"))

        self.assertEqual(response.status_code, 403)

    def test_switch_dom_blocks_external_redirect_target(self):
        user = self._create_user_with_profile("admin-switch", "admin")
        self.client.force_login(user)

        response = self.client.post(
            reverse("switch_dom"),
            data={"dom_id": str(self.dom.id), "next": "https://evil.example/"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        self.assertEqual(self.client.session.get("selected_dom"), self.dom.id)

    def test_zaposlenik_update_forbidden_for_employee(self):
        user = self._create_user_with_profile("emp-user", "zaposlenik")
        zaposlenik = self.dom.zaposlenik_set.create(
            ime_prezime="Test Employee", pozicija="Radnik",
            bruto=1000, neto=800, datum_ugovora="2024-01-01"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("zaposlenik_update", args=[zaposlenik.id]))

        self.assertEqual(response.status_code, 403)

    def test_zaposlenik_delete_forbidden_for_employee(self):
        user = self._create_user_with_profile("emp-user", "zaposlenik")
        zaposlenik = self.dom.zaposlenik_set.create(
            ime_prezime="Test Employee", pozicija="Radnik",
            bruto=1000, neto=800, datum_ugovora="2024-01-01"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("zaposlenik_delete", args=[zaposlenik.id]))

        self.assertEqual(response.status_code, 403)

    def test_rezija_update_forbidden_for_employee(self):
        from dashboard.models import Rezija
        user = self._create_user_with_profile("emp-user", "zaposlenik")
        rezija = Rezija.objects.create(
            naziv="Struja", iznos=300, interval="mjesecno",
            datum_pocetka="2024-01-01", aktivna=True, dom=self.dom
        )
        self.client.force_login(user)

        response = self.client.get(reverse("rezija_update", args=[rezija.id]))

        self.assertEqual(response.status_code, 403)

    def test_rezija_delete_forbidden_for_employee(self):
        from dashboard.models import Rezija
        user = self._create_user_with_profile("emp-user", "zaposlenik")
        rezija = Rezija.objects.create(
            naziv="Struja", iznos=300, interval="mjesecno",
            datum_pocetka="2024-01-01", aktivna=True, dom=self.dom
        )
        self.client.force_login(user)

        response = self.client.get(reverse("rezija_delete", args=[rezija.id]))

        self.assertEqual(response.status_code, 403)
