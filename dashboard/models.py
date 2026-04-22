from django.db import models
from django.contrib.auth.models import User


# =====================================
# KLIJENT
# =====================================

class Klijent(models.Model):
    naziv = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Klijent"
        verbose_name_plural = "Klijenti"

    def __str__(self):
        return self.naziv


# =====================================
# DOM
# =====================================

class Dom(models.Model):
    naziv = models.CharField(max_length=255)
    kapacitet = models.PositiveIntegerField(default=0)
    klijent = models.ForeignKey("Klijent", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = "Dom"
        verbose_name_plural = "Domovi"

    def __str__(self):
        return self.naziv


# =====================================
# PROFIL (vezan uz User)
# =====================================

class Profil(models.Model):

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("upravitelj", "Upravitelj"),
        ("zaposlenik", "Zaposlenik"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    klijent = models.ForeignKey("Klijent", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Klijent")
    dom = models.ForeignKey("Dom", on_delete=models.SET_NULL, null=True, blank=True)
    zaposlenik = models.OneToOneField(
        "Zaposlenik",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="profil",
    )
    upravljani_domovi = models.ManyToManyField(
        "Dom",
        blank=True,
        related_name="upravitelji",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profili"

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# =====================================
# KORISNIK
# =====================================

class Korisnik(models.Model):

    ime_prezime = models.CharField(max_length=255)
    datum_rodenja = models.DateField()
    oib = models.CharField(max_length=11, unique=True)
    mbo = models.CharField(max_length=50)
    soba = models.CharField(max_length=50)
    datum_dolaska = models.DateField()
    iznos = models.DecimalField(max_digits=10, decimal_places=2)
    mjesecna_clanarina = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    kontakt_obitelji = models.CharField(max_length=255)
    kontakt_obitelji_telefon = models.CharField(max_length=30, blank=True, default="")

    dom = models.ForeignKey(Dom, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Korisnik doma"
        verbose_name_plural = "Korisnici doma"

    def __str__(self):
        return self.ime_prezime


class KorisnikUplata(models.Model):
    korisnik = models.ForeignKey("Korisnik", on_delete=models.CASCADE, related_name="uplate")
    godina = models.PositiveIntegerField()
    mjesec = models.PositiveSmallIntegerField()
    iznos = models.DecimalField(max_digits=10, decimal_places=2)
    datum_potvrde = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Uplata korisnika"
        verbose_name_plural = "Uplate korisnika"
        unique_together = ("korisnik", "godina", "mjesec")
        ordering = ("-godina", "-mjesec", "-datum_potvrde")

    def __str__(self):
        return f"{self.korisnik.ime_prezime} - {self.mjesec:02d}/{self.godina} ({self.iznos} €)"


# =====================================
# ZAPOSLENIK
# =====================================

class Zaposlenik(models.Model):

    ime_prezime = models.CharField(max_length=255)
    pozicija = models.CharField(max_length=255)

    bruto = models.DecimalField(max_digits=10, decimal_places=2)
    neto = models.DecimalField(max_digits=10, decimal_places=2)

    datum_ugovora = models.DateField()

    dom = models.ForeignKey(Dom, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Zaposlenik"
        verbose_name_plural = "Zaposlenici"

    def __str__(self):
        return self.ime_prezime


class Smjena(models.Model):
    TIP_SMJENE = [
        ("jutarnja", "Jutarnja"),
        ("popodnevna", "Popodnevna"),
        ("nocna", "Noćna"),
        ("slobodno", "Slobodno"),
    ]

    zaposlenik = models.ForeignKey("Zaposlenik", on_delete=models.CASCADE, related_name="smjene")
    datum = models.DateField()
    tip_smjene = models.CharField(max_length=20, choices=TIP_SMJENE, default="jutarnja")

    class Meta:
        verbose_name = "Smjena"
        verbose_name_plural = "Smjene"
        unique_together = ("zaposlenik", "datum")
        ordering = ("datum", "zaposlenik__ime_prezime")

    def __str__(self):
        return f"{self.zaposlenik.ime_prezime} - {self.datum} ({self.get_tip_smjene_display()})"


# =====================================
# FINANCIJE
# =====================================

class Investicija(models.Model):
    naziv = models.CharField(max_length=255)
    iznos = models.DecimalField(max_digits=10, decimal_places=2)
    datum = models.DateField()
    dom = models.ForeignKey(Dom, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Investicija"
        verbose_name_plural = "Investicije"

    def __str__(self):
        return self.naziv


class Trosak(models.Model):
    KATEGORIJE = [
        ("kuhinja", "Troškovi kuhinje"),
        ("popravci", "Popravci u domu"),
        ("opcenito", "Općeniti troškovi"),
    ]

    naziv = models.CharField(max_length=255)
    kategorija = models.CharField(max_length=20, choices=KATEGORIJE)
    iznos = models.DecimalField(max_digits=10, decimal_places=2)
    trgovina = models.CharField(max_length=255, blank=True, default="")
    meso = models.CharField(max_length=255, blank=True, default="")
    datum = models.DateField()
    dom = models.ForeignKey(Dom, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Trošak"
        verbose_name_plural = "Troškovi"

    def __str__(self):
        return f"{self.naziv} ({self.get_kategorija_display()})"


class Rezija(models.Model):
    INTERVALI = [
        ("bez_intervala", "Bez intervala"),
        ("mjesecno", "Mjesečno"),
        ("kvartalno", "Kvartalno"),
        ("polugodisnje", "Polugodišnje"),
        ("godisnje", "Godišnje"),
    ]

    naziv = models.CharField(max_length=255)
    iznos = models.DecimalField(max_digits=10, decimal_places=2)
    interval = models.CharField(max_length=20, choices=INTERVALI, default="mjesecno")
    datum_pocetka = models.DateField()
    datum_zavrsetka = models.DateField(blank=True, null=True)
    aktivna = models.BooleanField(default=True)
    dom = models.ForeignKey(Dom, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Režija"
        verbose_name_plural = "Režije"

    def __str__(self):
        return f"{self.naziv} ({self.get_interval_display()})"
