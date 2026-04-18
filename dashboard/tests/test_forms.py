from django.test import TestCase

from dashboard.forms import KorisnikForm, RezijaForm, TrosakForm


class KorisnikFormTests(TestCase):
    def test_rejects_oib_with_invalid_length(self):
        form = KorisnikForm(
            data={
                "ime_prezime": "Ana Horvat",
                "datum_rodenja": "1950-01-01",
                "oib": "12345",
                "mbo": "MBO-1",
                "soba": "12A",
                "datum_dolaska": "2025-01-01",
                "iznos": "500.00",
                "mjesecna_clanarina": "100.00",
                "kontakt_obitelji": "Marko Horvat",
                "kontakt_obitelji_telefon": "0911111111",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("oib", form.errors)


class TrosakFormTests(TestCase):
    def test_kuhinja_requires_trgovina_and_meso(self):
        form = TrosakForm(
            data={
                "naziv": "Nabava hrane",
                "kategorija": "kuhinja",
                "iznos": "75.00",
                "trgovina": "",
                "meso": "",
                "datum": "2026-01-10",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("trgovina", form.errors)
        self.assertIn("meso", form.errors)

    def test_non_kuhinja_allows_empty_trgovina_and_meso(self):
        form = TrosakForm(
            data={
                "naziv": "Popravak lifta",
                "kategorija": "popravci",
                "iznos": "150.00",
                "trgovina": "",
                "meso": "",
                "datum": "2026-01-10",
            }
        )

        self.assertTrue(form.is_valid())


class RezijaFormTests(TestCase):
    def test_rejects_end_date_before_start_date(self):
        form = RezijaForm(
            data={
                "naziv": "Struja",
                "iznos": "300.00",
                "interval": "mjesecno",
                "datum_pocetka": "2026-02-01",
                "datum_zavrsetka": "2026-01-01",
                "aktivna": True,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("datum_zavrsetka", form.errors)
