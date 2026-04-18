from django import forms
from .models import Investicija, Korisnik, Rezija, Trosak, Zaposlenik


# =====================================
# KORISNIK FORMA
# =====================================

class KorisnikForm(forms.ModelForm):

    class Meta:
        model = Korisnik
        exclude = ["dom"]   # dom se postavlja iz sessiona

        widgets = {
            "ime_prezime": forms.TextInput(attrs={"class": "form-control"}),
            "datum_rodenja": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "oib": forms.TextInput(attrs={"class": "form-control"}),
            "mbo": forms.TextInput(attrs={"class": "form-control"}),
            "soba": forms.TextInput(attrs={"class": "form-control"}),
            "datum_dolaska": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "iznos": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "mjesecna_clanarina": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "kontakt_obitelji": forms.TextInput(attrs={"class": "form-control"}),
            "kontakt_obitelji_telefon": forms.TextInput(attrs={"class": "form-control"}),
        }

    # Validacija OIB-a
    def clean_oib(self):
        oib = self.cleaned_data.get("oib")
        if oib and (len(oib) != 11 or not oib.isdigit()):
            raise forms.ValidationError("OIB mora imati točno 11 znamenki.")
        return oib


# =====================================
# ZAPOSLENIK FORMA
# =====================================

class ZaposlenikForm(forms.ModelForm):

    class Meta:
        model = Zaposlenik
        exclude = ["dom"]   # dom dolazi iz sessiona

        widgets = {
            "ime_prezime": forms.TextInput(attrs={"class": "form-control"}),
            "pozicija": forms.TextInput(attrs={"class": "form-control"}),
            "bruto": forms.NumberInput(attrs={"class": "form-control"}),
            "neto": forms.NumberInput(attrs={"class": "form-control"}),
            "datum_ugovora": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
        }


class InvesticijaForm(forms.ModelForm):

    class Meta:
        model = Investicija
        exclude = ["dom"]

        widgets = {
            "naziv": forms.TextInput(attrs={"class": "form-control"}),
            "iznos": forms.NumberInput(attrs={"class": "form-control"}),
            "datum": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
        }


class TrosakForm(forms.ModelForm):

    class Meta:
        model = Trosak
        exclude = ["dom"]

        widgets = {
            "naziv": forms.TextInput(attrs={"class": "form-control"}),
            "kategorija": forms.Select(attrs={"class": "form-select"}),
            "iznos": forms.NumberInput(attrs={"class": "form-control"}),
            "trgovina": forms.TextInput(attrs={"class": "form-control"}),
            "meso": forms.TextInput(attrs={"class": "form-control"}),
            "datum": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        kategorija = cleaned_data.get("kategorija")
        trgovina = (cleaned_data.get("trgovina") or "").strip()
        meso = (cleaned_data.get("meso") or "").strip()

        if kategorija == "kuhinja":
            if not trgovina:
                self.add_error("trgovina", "Trgovina je obavezna za trošak hrane.")
            if not meso:
                self.add_error("meso", "Polje meso je obavezno za trošak hrane.")

        return cleaned_data


class RezijaForm(forms.ModelForm):

    class Meta:
        model = Rezija
        exclude = ["dom"]

        widgets = {
            "naziv": forms.TextInput(attrs={"class": "form-control"}),
            "iznos": forms.NumberInput(attrs={"class": "form-control"}),
            "interval": forms.Select(attrs={"class": "form-select"}),
            "datum_pocetka": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "datum_zavrsetka": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "aktivna": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        datum_pocetka = cleaned_data.get("datum_pocetka")
        datum_zavrsetka = cleaned_data.get("datum_zavrsetka")

        if datum_pocetka and datum_zavrsetka and datum_zavrsetka < datum_pocetka:
            self.add_error("datum_zavrsetka", "Završni datum ne može biti prije datuma početka.")

        return cleaned_data
