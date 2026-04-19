from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.sites import NotRegistered
from .models import Dom, Investicija, Klijent, Korisnik, KorisnikUplata, Profil, Rezija, Smjena, Trosak, Zaposlenik


class DomInline(admin.TabularInline):
    model = Dom
    extra = 0


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "dom", "zaposlenik", "klijent")
    list_filter = ("role", "dom__klijent", "dom")
    search_fields = ("user__username", "user__first_name", "user__last_name", "dom__naziv", "zaposlenik__ime_prezime")
    filter_horizontal = ("upravljani_domovi",)
    autocomplete_fields = ("zaposlenik",)

    @admin.display(description="Klijent")
    def klijent(self, obj):
        return obj.dom.klijent if obj.dom_id else "-"


try:
    admin.site.unregister(User)
except NotRegistered:
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Osobni podaci", {"fields": ("first_name", "last_name", "email")}),
        ("Dozvole", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Važni datumi", {"fields": ("last_login", "date_joined")}),
    )


@admin.register(Klijent)
class KlijentAdmin(admin.ModelAdmin):
    list_display = ("naziv",)
    search_fields = ("naziv",)
    inlines = (DomInline,)


@admin.register(Dom)
class DomAdmin(admin.ModelAdmin):
    list_display = ("naziv", "klijent", "kapacitet")
    list_filter = ("klijent",)
    search_fields = ("naziv", "klijent__naziv")


@admin.register(Korisnik)
class KorisnikAdmin(admin.ModelAdmin):
    list_display = ("ime_prezime", "oib", "mbo", "dom", "klijent")
    list_filter = ("dom__klijent", "dom")
    search_fields = ("ime_prezime", "oib", "mbo", "dom__naziv", "dom__klijent__naziv")
    fieldsets = (
        ("Osobni podaci", {
            "fields": ("ime_prezime", "oib", "mbo", "datum_rodenja"),
        }),
        ("Smještaj i financije", {
            "fields": ("dom", "soba", "datum_dolaska", "iznos", "mjesecna_clanarina"),
        }),
        ("Kontakt obitelji", {
            "fields": ("kontakt_obitelji", "kontakt_obitelji_telefon"),
        }),
    )

    @admin.display(description="Klijent")
    def klijent(self, obj):
        return obj.dom.klijent if obj.dom_id else "-"


@admin.register(KorisnikUplata)
class KorisnikUplataAdmin(admin.ModelAdmin):
    list_display = ("korisnik", "godina", "mjesec", "iznos", "datum_potvrde", "dom", "klijent")
    list_filter = ("godina", "mjesec", "korisnik__dom__klijent", "korisnik__dom")
    search_fields = ("korisnik__ime_prezime", "korisnik__oib")
    raw_id_fields = ("korisnik",)

    @admin.display(description="Dom")
    def dom(self, obj):
        return obj.korisnik.dom if obj.korisnik_id else "-"

    @admin.display(description="Klijent")
    def klijent(self, obj):
        if obj.korisnik_id and obj.korisnik.dom_id:
            return obj.korisnik.dom.klijent
        return "-"


@admin.register(Zaposlenik)
class ZaposlenikAdmin(admin.ModelAdmin):
    list_display = ("ime_prezime", "pozicija", "dom", "klijent")
    list_filter = ("dom__klijent", "dom", "pozicija")
    search_fields = ("ime_prezime", "pozicija", "dom__naziv", "dom__klijent__naziv")

    @admin.display(description="Klijent")
    def klijent(self, obj):
        return obj.dom.klijent if obj.dom_id else "-"

@admin.register(Investicija)
class InvesticijaAdmin(admin.ModelAdmin):
    list_display = ("naziv", "iznos", "datum", "dom", "klijent")
    list_filter = ("dom__klijent", "dom", "datum")
    search_fields = ("naziv", "dom__naziv", "dom__klijent__naziv")

    @admin.display(description="Klijent")
    def klijent(self, obj):
        return obj.dom.klijent if obj.dom_id else "-"


@admin.register(Trosak)
class TrosakAdmin(admin.ModelAdmin):
    list_display = ("naziv", "kategorija", "iznos", "datum", "dom", "klijent")
    list_filter = ("kategorija", "dom__klijent", "dom", "datum")
    search_fields = ("naziv", "dom__naziv", "dom__klijent__naziv")

    @admin.display(description="Klijent")
    def klijent(self, obj):
        return obj.dom.klijent if obj.dom_id else "-"


@admin.register(Rezija)
class RezijaAdmin(admin.ModelAdmin):
    list_display = ("naziv", "iznos", "interval", "datum_pocetka", "datum_zavrsetka", "aktivna", "dom", "klijent")
    list_filter = ("interval", "aktivna", "dom__klijent", "dom")
    search_fields = ("naziv", "dom__naziv", "dom__klijent__naziv")

    @admin.display(description="Klijent")
    def klijent(self, obj):
        return obj.dom.klijent if obj.dom_id else "-"


@admin.register(Smjena)
class SmjenaAdmin(admin.ModelAdmin):
    list_display = ("zaposlenik", "datum", "tip_smjene", "dom", "klijent")
    list_filter = ("tip_smjene", "datum", "zaposlenik__dom__klijent", "zaposlenik__dom")
    search_fields = ("zaposlenik__ime_prezime",)
    raw_id_fields = ("zaposlenik",)

    @admin.display(description="Dom")
    def dom(self, obj):
        return obj.zaposlenik.dom if obj.zaposlenik_id else "-"

    @admin.display(description="Klijent")
    def klijent(self, obj):
        if obj.zaposlenik_id and obj.zaposlenik.dom_id:
            return obj.zaposlenik.dom.klijent
        return "-"
