from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.sites import NotRegistered
from django.db.models import Q
from .models import Dom, Investicija, Klijent, Korisnik, KorisnikUplata, Profil, Rezija, Smjena, Trosak, UserProfile, Zaposlenik

# ---------------------------------------------------------------------------
# Scoped admin za upravitelje
#
# Kako dodijeliti upravitelja:
# 1. Kreirati korisnika u adminu
# 2. Postaviti is_staff = True
# 3. Dodati u grupu "Upravitelji"  (python manage.py setup_upravitelj_group)
# 4. Otvoriti/kreirati njihov Profil → role="upravitelj",
#    upravljani_domovi = domovi kojima upravljaju
# ---------------------------------------------------------------------------


def _get_managed_dom_ids(request):
    """Vraća set dom ID-eva kojima upravatelj upravlja."""
    try:
        profil = request.user.profil
    except Profil.DoesNotExist:
        return set()
    if profil.role != "upravitelj":
        return set()
    ids = set(profil.upravljani_domovi.values_list("id", flat=True))
    if not ids and profil.dom_id:
        ids = {profil.dom_id}
    return ids


def _is_upravitelj(request):
    try:
        return request.user.profil.role == "upravitelj"
    except Profil.DoesNotExist:
        return False


class DomInline(admin.TabularInline):
    model = Dom
    extra = 0


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "dom", "zaposlenik", "get_klijent")
    list_filter = ("role", "dom__klijent", "dom")
    search_fields = ("user__username", "user__first_name", "user__last_name", "dom__naziv", "zaposlenik__ime_prezime")
    filter_horizontal = ("upravljani_domovi",)
    autocomplete_fields = ("zaposlenik",)
    fields = ("user", "dom", "role", "zaposlenik", "upravljani_domovi")

    @admin.display(description="Klijent")
    def get_klijent(self, obj):
        if obj.klijent_id:
            return obj.klijent
        return obj.dom.klijent if obj.dom_id else "-"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        dom_ids = _get_managed_dom_ids(request)
        return qs.filter(Q(zaposlenik__dom_id__in=dom_ids) | Q(dom_id__in=dom_ids))


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ("must_change_password",)


class ProfilInline(admin.StackedInline):
    model = Profil
    extra = 0
    can_delete = False

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("klijent", "dom", "role", "zaposlenik", "upravljani_domovi")
        return ("role", "zaposlenik")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "zaposlenik" and not request.user.is_superuser:
            kwargs["queryset"] = Zaposlenik.objects.filter(
                dom_id__in=_get_managed_dom_ids(request)
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


try:
    admin.site.unregister(User)
except NotRegistered:
    pass


@admin.action(description="Zahtijevaj promjenu lozinke pri sljedećoj prijavi")
def zahtijevaj_promjenu_lozinke(modeladmin, request, queryset):
    for user in queryset:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.must_change_password = True
        profile.save()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    inlines = [UserProfileInline, ProfilInline]
    actions = [zahtijevaj_promjenu_lozinke]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Osobni podaci", {"fields": ("first_name", "last_name", "email")}),
        ("Dozvole", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Važni datumi", {"fields": ("last_login", "date_joined")}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        dom_ids = _get_managed_dom_ids(request)
        return qs.filter(
            Q(pk=request.user.pk) | Q(profil__zaposlenik__dom_id__in=dom_ids)
        )

    def has_delete_permission(self, request, obj=None):
        if _is_upravitelj(request):
            return False
        return super().has_delete_permission(request, obj)


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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(dom_id__in=_get_managed_dom_ids(request))

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not obj.dom_id:
            dom_ids = _get_managed_dom_ids(request)
            if dom_ids:
                obj.dom_id = next(iter(dom_ids))
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "dom" and not request.user.is_superuser:
            kwargs["queryset"] = Dom.objects.filter(id__in=_get_managed_dom_ids(request))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        if _is_upravitelj(request):
            return False
        return super().has_delete_permission(request, obj)

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
