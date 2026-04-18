from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path("dashboard/zaposlenik-kalendar/", views.employee_calendar_data, name="employee_calendar_data"),
    path("promijeni-dom/", views.switch_dom, name="switch_dom"),
    path("profil/", views.profil_view, name="profil"),
    path("financije/", views.financije, name="financije"),
    path("financije/primanja/", views.financije_primanja, name="financije_primanja"),
    path("financije/troskovi/", views.financije_troskovi, name="financije_troskovi"),
    path("financije/rezije/", views.financije_rezije, name="financije_rezije"),

    path("korisnici/", views.korisnici_list, name="korisnici_list"),
    path("korisnici/uplata/postavi/", views.korisnik_uplata_set, name="korisnik_uplata_set"),
    path("korisnici/dodaj/", views.korisnik_create, name="korisnik_create"),
    path("korisnici/<int:pk>/edit/", views.korisnik_update, name="korisnik_update"),
    path("korisnici/<int:pk>/delete/", views.korisnik_delete, name="korisnik_delete"),
    path("korisnici/<int:pk>/", views.korisnik_detail, name="korisnik_detail"),

    path("zaposlenici/", views.zaposlenici_list, name="zaposlenici_list"),
path("zaposlenici/dodaj/", views.zaposlenik_create, name="zaposlenik_create"),
    path("zaposlenici/<int:pk>/", views.zaposlenik_detail, name="zaposlenik_detail"),
path("zaposlenici/<int:pk>/edit/", views.zaposlenik_update, name="zaposlenik_update"),
    path("zaposlenici/<int:pk>/delete/", views.zaposlenik_delete, name="zaposlenik_delete"),
    path("zaposlenici/smjene/postavi/", views.smjena_set, name="smjena_set"),

    path("investicije/dodaj/", views.investicija_create, name="investicija_create"),
    path("investicije/<int:pk>/", views.investicija_detail, name="investicija_detail"),
    path("investicije/<int:pk>/edit/", views.investicija_update, name="investicija_update"),
    path("investicije/<int:pk>/delete/", views.investicija_delete, name="investicija_delete"),

    path("troskovi/dodaj/", views.trosak_create, name="trosak_create"),
    path("troskovi/<int:pk>/", views.trosak_detail, name="trosak_detail"),
    path("troskovi/<int:pk>/edit/", views.trosak_update, name="trosak_update"),
    path("troskovi/<int:pk>/delete/", views.trosak_delete, name="trosak_delete"),

    path("rezije/dodaj/", views.rezija_create, name="rezija_create"),
    path("rezije/<int:pk>/", views.rezija_detail, name="rezija_detail"),
    path("rezije/<int:pk>/edit/", views.rezija_update, name="rezija_update"),
    path("rezije/<int:pk>/delete/", views.rezija_delete, name="rezija_delete"),

]
