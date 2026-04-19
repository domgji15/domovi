import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Dom, Investicija, Korisnik, KorisnikUplata, Profil, Rezija, Smjena, Trosak, Zaposlenik
from .forms import InvesticijaForm, KorisnikForm, RezijaForm, TrosakForm, ZaposlenikForm
from .dom_access import resolve_selected_dom_id

MONTH_OPTIONS = (
    (1, "Sij"), (2, "Velj"), (3, "Ožu"), (4, "Tra"),
    (5, "Svi"), (6, "Lip"), (7, "Srp"), (8, "Kol"),
    (9, "Ruj"), (10, "Lis"), (11, "Stu"), (12, "Pro"),
)

INTERVAL_TO_MONTHS = {
    "bez_intervala": None,
    "mjesecno": 1,
    "kvartalno": 3,
    "polugodisnje": 6,
    "godisnje": 12,
}


def _build_year_options(dom_ids):
    """Build sorted year options from all financial data for given dom IDs."""
    year_candidates = {date.today().year}
    year_candidates.update(KorisnikUplata.objects.filter(korisnik__dom_id__in=dom_ids).values_list("godina", flat=True))
    year_candidates.update(Zaposlenik.objects.filter(dom_id__in=dom_ids).values_list("datum_ugovora__year", flat=True))
    year_candidates.update(Investicija.objects.filter(dom_id__in=dom_ids).values_list("datum__year", flat=True))
    year_candidates.update(Trosak.objects.filter(dom_id__in=dom_ids).values_list("datum__year", flat=True))
    year_candidates.update(Rezija.objects.filter(dom_id__in=dom_ids).values_list("datum_pocetka__year", flat=True))
    return sorted({y for y in year_candidates if y}, reverse=True)


# ==========================================
# DASHBOARD
# ==========================================

def _get_profil(request):
    if not hasattr(request, "_cached_profil"):
        request._cached_profil = Profil.objects.filter(user=request.user).select_related("dom").first()
    return request._cached_profil


def _build_calendar_payload(today, cal_month, cal_year):
    if cal_month < 1:
        cal_month = 12
        cal_year -= 1
    elif cal_month > 12:
        cal_month = 1
        cal_year += 1

    weeks = calendar.monthcalendar(cal_year, cal_month)
    month_names = [
        "Siječanj", "Veljača", "Ožujak", "Travanj", "Svibanj", "Lipanj",
        "Srpanj", "Kolovoz", "Rujan", "Listopad", "Studeni", "Prosinac",
    ]

    prev_month = cal_month - 1
    prev_year = cal_year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = cal_month + 1
    next_year = cal_year
    if next_month == 13:
        next_month = 1
        next_year += 1

    return {
        "cal_title": f"{month_names[cal_month - 1]} {cal_year}.",
        "cal_weeks": weeks,
        "cal_today": today,
        "cal_month": cal_month,
        "cal_year": cal_year,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
    }


def _resolve_employee_for_user(profil, selected_dom):
    if not profil or not selected_dom:
        return None

    if not profil.zaposlenik_id:
        return None

    if profil.zaposlenik.dom_id != selected_dom:
        return None

    return profil.zaposlenik


def _build_employee_schedule(today, employee=None):
    week_start = today - timedelta(days=today.weekday())
    shift_meta = {
        "jutarnja": ("Jutarnja", "07:00 - 15:00"),
        "popodnevna": ("Popodnevna", "15:00 - 23:00"),
        "nocna": ("Noćna", "23:00 - 07:00"),
        "slobodno": ("Slobodno", "-"),
    }

    shift_map = {}
    if employee:
        week_end = week_start + timedelta(days=6)
        shifts = Smjena.objects.filter(
            zaposlenik=employee,
            datum__range=(week_start, week_end),
        )
        shift_map = {item.datum: item.tip_smjene for item in shifts}

    week_schedule = []
    for day_index in range(7):
        current_day = week_start + timedelta(days=day_index)
        is_weekend = current_day.weekday() >= 5
        selected_shift = shift_map.get(current_day)
        if selected_shift:
            shift_name, work_hours = shift_meta.get(selected_shift, ("Nije definirano", "-"))
        elif employee is None:
            shift_name, work_hours = ("Nije postavljeno", "-")
        elif is_weekend:
            shift_name, work_hours = ("Neradni dan", "-")
        else:
            shift_name, work_hours = ("Nije postavljeno", "-")

        week_schedule.append({
            "datum": current_day,
            "smjena": shift_name,
            "radno_vrijeme": work_hours,
            "is_today": current_day == today,
            "is_weekend": is_weekend,
        })

    today_schedule = next((item for item in week_schedule if item["is_today"]), week_schedule[0])
    week_end = week_start + timedelta(days=6)
    week_label = f"{week_start.strftime('%d.%m.%Y.')} - {week_end.strftime('%d.%m.%Y.')}"

    return today_schedule, week_schedule, week_label


@login_required
def index(request):
    allowed_domovi, selected_dom, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    profil = _get_profil(request)

    if profil and profil.role == "zaposlenik":
        dom_obj = Dom.objects.filter(id=selected_dom).first() if selected_dom else None
        dom_kapacitet = dom_obj.kapacitet if dom_obj else 0
        broj_korisnika = Korisnik.objects.filter(dom_id=selected_dom).count() if selected_dom else 0
        slobodna_mjesta = max(dom_kapacitet - broj_korisnika, 0)
        popunjenost = round((broj_korisnika / dom_kapacitet) * 100) if dom_kapacitet else 0
        if popunjenost > 100:
            popunjenost = 100
        display_name = request.user.first_name or request.user.get_full_name() or request.user.username
        today = date.today()
        employee = _resolve_employee_for_user(profil, selected_dom)
        today_schedule, week_schedule, week_label = _build_employee_schedule(today, employee=employee)

        try:
            cal_month = int(request.GET.get("m", today.month))
            cal_year = int(request.GET.get("y", today.year))
        except (TypeError, ValueError):
            cal_month = today.month
            cal_year = today.year

        cal_ctx = _build_calendar_payload(today, cal_month, cal_year)

        return render(request, "dashboard/index_zaposlenik.html", {
            "ime": display_name,
            "broj_korisnika": broj_korisnika,
            "popunjenost": popunjenost,
            "popunjenost_data": [broj_korisnika, slobodna_mjesta],
            **cal_ctx,
            "today_schedule": today_schedule,
            "week_schedule": week_schedule,
            "week_label": week_label,
        })

    selected_scope, selected_year, selected_quarter, selected_month, period_start, period_end = _parse_period(request)
    selected_dom_filter_raw = request.GET.get("dom_filter", "all")
    selected_dom_filter = "all"
    if selected_dom_filter_raw and selected_dom_filter_raw != "all":
        try:
            selected_dom_filter = str(int(selected_dom_filter_raw))
        except (TypeError, ValueError):
            selected_dom_filter = "all"

    dom_filter_options = list(allowed_domovi.order_by("naziv"))
    if selected_dom_filter != "all":
        allowed_ids_set = set(allowed_ids)
        dom_filter_id = int(selected_dom_filter)
        if dom_filter_id not in allowed_ids_set:
            selected_dom_filter = "all"
            filtered_domovi = allowed_domovi.order_by("naziv")
            filtered_ids = allowed_ids
        else:
            filtered_domovi = allowed_domovi.filter(id=dom_filter_id).order_by("naziv")
            filtered_ids = [dom_filter_id]
    else:
        filtered_domovi = allowed_domovi.order_by("naziv")
        filtered_ids = allowed_ids

    if not allowed_ids:
        return render(request, "dashboard/index.html", {
            "selected_dom": selected_dom,
            "selected_scope": selected_scope,
            "selected_year": selected_year,
            "selected_quarter": selected_quarter,
            "selected_month": selected_month,
            "selected_dom_filter": selected_dom_filter,
            "dom_filter_options": [],
            "year_options": [date.today().year],
            "month_options": MONTH_OPTIONS,
            "ukupan_broj_korisnika": 0,
            "broj_neplacenih_korisnika": 0,
            "ukupan_broj_zaposlenika": 0,
            "ukupna_primanja": Decimal("0"),
            "ukupni_troskovi": Decimal("0"),
            "saldo": Decimal("0"),
            "popunjenost": 0,
            "dom_popunjenost": [],
            "dom_financije": [],
            "dom_overview": [],
            "alerts": [],
            "dom_labels": [],
            "dom_popunjenost_data": [],
            "dom_primanja_data": [],
            "dom_troskovi_data": [],
            "line_labels": ["Sij", "Velj", "Ožu", "Tra", "Svi", "Lip", "Srp", "Kol", "Ruj", "Lis", "Stu", "Pro"],
            "line_data_primanja": [0] * 12,
            "line_data_troskovi": [0] * 12,
            "donut_primanja_data": [0, 0],
            "donut_troskovi_data": [0, 0, 0],
        })

    kpi_korisnici_qs = Korisnik.objects.filter(dom_id__in=allowed_ids)
    kpi_uplate_qs = KorisnikUplata.objects.filter(korisnik__dom_id__in=allowed_ids)
    kpi_investicije_qs = Investicija.objects.filter(dom_id__in=allowed_ids)
    kpi_zaposlenici_qs = Zaposlenik.objects.filter(dom_id__in=allowed_ids)
    kpi_troskovi_qs = Trosak.objects.filter(dom_id__in=allowed_ids)
    kpi_rezije_qs = Rezija.objects.filter(dom_id__in=allowed_ids, aktivna=True)

    korisnici_qs = Korisnik.objects.filter(dom_id__in=filtered_ids)
    uplate_qs = KorisnikUplata.objects.filter(korisnik__dom_id__in=filtered_ids)
    investicije_qs = Investicija.objects.filter(dom_id__in=filtered_ids)
    zaposlenici_qs = Zaposlenik.objects.filter(dom_id__in=filtered_ids)
    troskovi_qs = Trosak.objects.filter(dom_id__in=filtered_ids)
    rezije_qs = Rezija.objects.filter(dom_id__in=filtered_ids, aktivna=True)

    def _period_troskovi(employees_qs, rezije_period_qs, troskovi_period_qs, p_start, p_end):
        place = Decimal("0")
        for zaposlenik in employees_qs:
            count = _count_occurrences(zaposlenik.datum_ugovora, 1, p_start, p_end)
            place += Decimal(zaposlenik.bruto) * count

        rezije_total = Decimal("0")
        for rezija in rezije_period_qs:
            interval_months = INTERVAL_TO_MONTHS.get(rezija.interval, 1)
            if interval_months is None:
                count = 1 if p_start <= rezija.datum_pocetka <= p_end else 0
            else:
                count = _count_occurrences_with_end(
                    rezija.datum_pocetka,
                    rezija.datum_zavrsetka,
                    interval_months,
                    p_start,
                    p_end,
                )
            rezije_total += Decimal(rezija.iznos) * count

        kuhinja = (
            troskovi_period_qs.filter(kategorija="kuhinja").aggregate(total=Sum("iznos"))["total"] or Decimal("0")
        )
        popravci = (
            troskovi_period_qs.filter(kategorija="popravci").aggregate(total=Sum("iznos"))["total"] or Decimal("0")
        )
        opcenito = (
            troskovi_period_qs.filter(kategorija="opcenito").aggregate(total=Sum("iznos"))["total"] or Decimal("0")
        )
        odrzavanje = kuhinja + popravci + opcenito
        return place, rezije_total, odrzavanje

    kpi_korisnici_primanja_period = _filter_uplate_for_period(
        kpi_uplate_qs,
        selected_scope,
        selected_year,
        selected_quarter,
        selected_month,
    ).aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    kpi_investicije_period = (
        kpi_investicije_qs.filter(datum__range=(period_start, period_end)).aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    )
    kpi_place_period, kpi_rezije_period, kpi_odrzavanje_period = _period_troskovi(
        kpi_zaposlenici_qs,
        kpi_rezije_qs,
        kpi_troskovi_qs.filter(datum__range=(period_start, period_end)),
        period_start,
        period_end,
    )

    korisnici_primanja_period = _filter_uplate_for_period(
        uplate_qs,
        selected_scope,
        selected_year,
        selected_quarter,
        selected_month,
    ).aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    investicije_period = (
        investicije_qs.filter(datum__range=(period_start, period_end)).aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    )
    place_period, rezije_period, odrzavanje_period = _period_troskovi(
        zaposlenici_qs,
        rezije_qs,
        troskovi_qs.filter(datum__range=(period_start, period_end)),
        period_start,
        period_end,
    )

    ukupan_broj_korisnika = kpi_korisnici_qs.count()
    placeni_korisnici_ids = set(
        KorisnikUplata.objects.filter(
            korisnik__dom_id__in=allowed_ids,
            godina=selected_year,
            mjesec=selected_month,
        ).values_list("korisnik_id", flat=True)
    )
    broj_neplacenih_korisnika = kpi_korisnici_qs.exclude(id__in=placeni_korisnici_ids).count()
    ukupan_broj_zaposlenika = kpi_zaposlenici_qs.count()
    ukupna_primanja = kpi_korisnici_primanja_period + kpi_investicije_period

    korisnici_per_dom = {
        row["dom_id"]: row["total"]
        for row in korisnici_qs.values("dom_id").annotate(total=Count("id"))
    }
    dom_popunjenost = []
    for dom in filtered_domovi:
        broj_korisnika = korisnici_per_dom.get(dom.id, 0)
        postotak = round((broj_korisnika / dom.kapacitet) * 100) if dom.kapacitet > 0 else 0
        if postotak > 100:
            postotak = 100
        dom_popunjenost.append({
            "naziv": dom.naziv,
            "broj_korisnika": broj_korisnika,
            "kapacitet": dom.kapacitet,
            "postotak": postotak,
        })

    total_capacity = allowed_domovi.aggregate(total=Sum("kapacitet"))["total"] or 0
    popunjenost = 0
    if total_capacity > 0:
        popunjenost = round((ukupan_broj_korisnika / total_capacity) * 100)
        if popunjenost > 100:
            popunjenost = 100

    ukupni_troskovi = kpi_place_period + kpi_rezije_period + kpi_odrzavanje_period
    saldo = ukupna_primanja - ukupni_troskovi

    dom_financije = []
    dom_overview = []
    zaposlenici_per_dom = {
        row["dom_id"]: row["total"]
        for row in zaposlenici_qs.values("dom_id").annotate(total=Count("id"))
    }

    # Pre-aggregate per-dom data to avoid N+1 queries
    uplate_per_dom = {
        row["korisnik__dom_id"]: row["total"]
        for row in _filter_uplate_for_period(
            uplate_qs, selected_scope, selected_year, selected_quarter, selected_month,
        ).values("korisnik__dom_id").annotate(total=Sum("iznos"))
    }
    investicije_per_dom = {
        row["dom_id"]: row["total"]
        for row in investicije_qs.filter(
            datum__range=(period_start, period_end),
        ).values("dom_id").annotate(total=Sum("iznos"))
    }
    troskovi_per_dom_kat = {}
    for row in troskovi_qs.filter(
        datum__range=(period_start, period_end),
    ).values("dom_id", "kategorija").annotate(total=Sum("iznos")):
        troskovi_per_dom_kat.setdefault(row["dom_id"], {})[row["kategorija"]] = row["total"] or Decimal("0")

    # Group employees and rezije by dom for salary/rezije calculations
    zaposlenici_by_dom = {}
    for zap in zaposlenici_qs:
        zaposlenici_by_dom.setdefault(zap.dom_id, []).append(zap)
    rezije_by_dom = {}
    for rez in rezije_qs:
        rezije_by_dom.setdefault(rez.dom_id, []).append(rez)

    popunjenost_by_name = {x["naziv"]: x["postotak"] for x in dom_popunjenost}

    for dom in filtered_domovi:
        dom_uplate = uplate_per_dom.get(dom.id, Decimal("0"))
        dom_inv = investicije_per_dom.get(dom.id, Decimal("0"))
        dom_primanja = dom_uplate + dom_inv

        # Calculate salary costs
        dom_place_period = Decimal("0")
        for zap in zaposlenici_by_dom.get(dom.id, []):
            count = _count_occurrences(zap.datum_ugovora, 1, period_start, period_end)
            dom_place_period += Decimal(zap.bruto) * count

        # Calculate rezije costs
        dom_rezije_period = Decimal("0")
        for rez in rezije_by_dom.get(dom.id, []):
            interval_months = INTERVAL_TO_MONTHS.get(rez.interval, 1)
            if interval_months is None:
                count = 1 if period_start <= rez.datum_pocetka <= period_end else 0
            else:
                count = _count_occurrences_with_end(
                    rez.datum_pocetka, rez.datum_zavrsetka, interval_months, period_start, period_end,
                )
            dom_rezije_period += Decimal(rez.iznos) * count

        # Maintenance costs from pre-aggregated data
        dom_kat = troskovi_per_dom_kat.get(dom.id, {})
        dom_odrzavanje_period = (
            dom_kat.get("kuhinja", Decimal("0"))
            + dom_kat.get("popravci", Decimal("0"))
            + dom_kat.get("opcenito", Decimal("0"))
        )

        dom_ukupni_troskovi = dom_place_period + dom_rezije_period + dom_odrzavanje_period

        dom_financije.append({
            "naziv": dom.naziv,
            "primanja": dom_primanja,
            "troskovi": dom_ukupni_troskovi,
        })
        dom_overview.append({
            "id": dom.id,
            "naziv": dom.naziv,
            "korisnici": korisnici_per_dom.get(dom.id, 0),
            "zaposlenici": zaposlenici_per_dom.get(dom.id, 0),
            "popunjenost": popunjenost_by_name.get(dom.naziv, 0),
            "primanja": dom_primanja,
            "troskovi": dom_ukupni_troskovi,
            "saldo": dom_primanja - dom_ukupni_troskovi,
        })

    line_labels = ["Sij", "Velj", "Ožu", "Tra", "Svi", "Lip", "Srp", "Kol", "Ruj", "Lis", "Stu", "Pro"]
    line_data_primanja = []
    line_data_troskovi = []
    for month in range(1, 13):
        m_start = date(selected_year, month, 1)
        m_end = date(selected_year, month, calendar.monthrange(selected_year, month)[1])
        korisnici_month = (
            uplate_qs.filter(godina=selected_year, mjesec=month).aggregate(total=Sum("iznos"))["total"] or Decimal("0")
        )
        investicije_month = (
            investicije_qs.filter(datum__range=(m_start, m_end)).aggregate(total=Sum("iznos"))["total"] or Decimal("0")
        )
        line_data_primanja.append(float(korisnici_month + investicije_month))

        place_month, rezije_month, odrzavanje_month = _period_troskovi(
            zaposlenici_qs,
            rezije_qs,
            troskovi_qs.filter(datum__range=(m_start, m_end)),
            m_start,
            m_end,
        )
        line_data_troskovi.append(float(place_month + rezije_month + odrzavanje_month))

    donut_primanja_data = [float(kpi_korisnici_primanja_period), float(kpi_investicije_period)]
    donut_troskovi_data = [float(kpi_place_period), float(kpi_rezije_period), float(kpi_odrzavanje_period)]

    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    current_month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    # Pre-aggregate current month troškovi per dom for alerts (avoid N+1)
    cur_month_troskovi_per_dom = {
        row["dom_id"]: row["total"]
        for row in Trosak.objects.filter(
            dom_id__in=filtered_ids,
            datum__range=(current_month_start, current_month_end),
        ).values("dom_id").annotate(total=Sum("iznos"))
    }

    # Pre-compute current month salary and rezije per dom using already-fetched data
    cur_month_has_cost = {}
    for dom_id in [row["id"] for row in dom_overview]:
        place = Decimal("0")
        for zap in zaposlenici_by_dom.get(dom_id, []):
            count = _count_occurrences(zap.datum_ugovora, 1, current_month_start, current_month_end)
            place += Decimal(zap.bruto) * count
        rez_total = Decimal("0")
        for rez in rezije_by_dom.get(dom_id, []):
            interval_months = INTERVAL_TO_MONTHS.get(rez.interval, 1)
            if interval_months is None:
                count = 1 if current_month_start <= rez.datum_pocetka <= current_month_end else 0
            else:
                count = _count_occurrences_with_end(
                    rez.datum_pocetka, rez.datum_zavrsetka, interval_months, current_month_start, current_month_end,
                )
            rez_total += Decimal(rez.iznos) * count
        odrzavanje = cur_month_troskovi_per_dom.get(dom_id, Decimal("0"))
        cur_month_has_cost[dom_id] = (place + rez_total + odrzavanje) > 0

    alerts = []
    for row in dom_overview:
        if row["popunjenost"] >= 90:
            alerts.append({
                "type": "warning",
                "text": f"Dom {row['naziv']} je preko 90% popunjenosti ({row['popunjenost']}%).",
                "url": f"{reverse('dashboard')}?scope={selected_scope}&year={selected_year}&month={selected_month}&quarter={selected_quarter}&dom_filter={row['id']}",
            })
        if row["saldo"] < 0:
            alerts.append({
                "type": "danger",
                "text": f"Dom {row['naziv']} ima negativan saldo ({row['saldo']:,.2f} €).",
                "url": f"{reverse('dashboard')}?scope={selected_scope}&year={selected_year}&month={selected_month}&quarter={selected_quarter}&dom_filter={row['id']}",
            })

        if not cur_month_has_cost.get(row["id"], False):
            alerts.append({
                "type": "info",
                "text": f"Dom {row['naziv']} nema unosa troškova u tekućem mjesecu.",
                "url": f"{reverse('financije_troskovi')}?scope={selected_scope}&year={selected_year}&month={selected_month}&quarter={selected_quarter}",
            })

    soon_end = today + timedelta(days=30)
    for rezija in Rezija.objects.filter(
        dom_id__in=filtered_ids,
        aktivna=True,
        datum_zavrsetka__isnull=False,
        datum_zavrsetka__range=(today, soon_end),
    ).select_related("dom"):
        alerts.append({
            "type": "warning",
            "text": f"Režija '{rezija.naziv}' za dom {rezija.dom.naziv} završava {rezija.datum_zavrsetka.strftime('%d.%m.%Y.')}.",
            "url": reverse("rezija_detail", args=[rezija.id]),
        })

    year_options = _build_year_options(allowed_ids)

    dom_labels = [d["naziv"] for d in dom_popunjenost]
    dom_popunjenost_data = [d["postotak"] for d in dom_popunjenost]
    dom_primanja_data = [float(d["primanja"]) for d in dom_financije]
    dom_troskovi_data = [float(d["troskovi"]) for d in dom_financije]

    return render(request, "dashboard/index.html", {
        "selected_dom": selected_dom,
        "selected_scope": selected_scope,
        "selected_year": selected_year,
        "selected_quarter": selected_quarter,
        "selected_month": selected_month,
        "selected_dom_filter": selected_dom_filter,
        "dom_filter_options": dom_filter_options,
        "year_options": year_options,
        "month_options": MONTH_OPTIONS,
        "ukupan_broj_korisnika": ukupan_broj_korisnika,
        "broj_neplacenih_korisnika": broj_neplacenih_korisnika,
        "ukupan_broj_zaposlenika": ukupan_broj_zaposlenika,
        "ukupna_primanja": ukupna_primanja,
        "ukupni_troskovi": ukupni_troskovi,
        "saldo": saldo,
        "popunjenost": popunjenost,
        "dom_popunjenost": dom_popunjenost,
        "dom_financije": dom_financije,
        "dom_overview": dom_overview,
        "alerts": alerts,
        "dom_labels": dom_labels,
        "dom_popunjenost_data": dom_popunjenost_data,
        "dom_primanja_data": dom_primanja_data,
        "dom_troskovi_data": dom_troskovi_data,
        "line_labels": line_labels,
        "line_data_primanja": line_data_primanja,
        "line_data_troskovi": line_data_troskovi,
        "donut_primanja_data": donut_primanja_data,
        "donut_troskovi_data": donut_troskovi_data,
    })


@login_required
def employee_calendar_data(request):
    profil = _get_profil(request)
    if not profil or profil.role != "zaposlenik":
        return HttpResponseForbidden("Samo zaposlenik može dohvatiti ovaj kalendar.")

    today = date.today()
    try:
        cal_month = int(request.GET.get("m", today.month))
        cal_year = int(request.GET.get("y", today.year))
    except (TypeError, ValueError):
        cal_month = today.month
        cal_year = today.year

    cal_ctx = _build_calendar_payload(today, cal_month, cal_year)

    return JsonResponse({
        "title": cal_ctx["cal_title"],
        "weeks": cal_ctx["cal_weeks"],
        "today_day": today.day,
        "today_month": today.month,
        "today_year": today.year,
        "cal_month": cal_ctx["cal_month"],
        "cal_year": cal_ctx["cal_year"],
    })


@login_required
def switch_dom(request):
    if request.method == "POST":
        posted_dom_id = request.POST.get("dom_id")
        resolve_selected_dom_id(request, posted_dom_id=posted_dom_id)

        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"
        return redirect(next_url)

    return redirect("dashboard")


# ==========================================
# KORISNICI
# ==========================================

@login_required
def korisnici_list(request):

    _, selected_dom, _ = resolve_selected_dom_id(request)
    query = request.GET.get("q")
    today = date.today()
    selected_year = request.GET.get("year")
    selected_month = request.GET.get("month")

    try:
        selected_year = int(selected_year) if selected_year else today.year
    except (TypeError, ValueError):
        selected_year = today.year

    try:
        selected_month = int(selected_month) if selected_month else today.month
    except (TypeError, ValueError):
        selected_month = today.month
    if selected_month < 1 or selected_month > 12:
        selected_month = today.month

    if not selected_dom:
        korisnici = Korisnik.objects.none()
    else:
        korisnici = Korisnik.objects.filter(dom_id=selected_dom)

        if query:
            korisnici = korisnici.filter(
                Q(ime_prezime__icontains=query) | Q(oib__icontains=query)
            )

    korisnici = korisnici.order_by("ime_prezime")
    uplate_qs = KorisnikUplata.objects.filter(
        korisnik__in=korisnici,
        godina=selected_year,
        mjesec=selected_month,
    )
    uplate_map = {u.korisnik_id: u for u in uplate_qs}
    ukupno_uplaceno_map = {
        row["korisnik_id"]: row["total"] or Decimal("0")
        for row in KorisnikUplata.objects.filter(korisnik__in=korisnici)
        .values("korisnik_id")
        .annotate(total=Sum("iznos"))
    }

    korisnici_rows = []
    unpaid_korisnici = []
    for korisnik in korisnici:
        uplata = uplate_map.get(korisnik.id)
        ukupno_uplaceno = ukupno_uplaceno_map.get(korisnik.id, Decimal("0"))
        preostalo = Decimal(korisnik.iznos or 0) - ukupno_uplaceno
        if preostalo < 0:
            preostalo = Decimal("0")
        is_fully_paid = preostalo <= 0

        if uplata:
            predlozeno = Decimal(uplata.iznos or 0)
        else:
            predlozeno = Decimal(korisnik.mjesecna_clanarina or 0)
            if preostalo > 0 and (predlozeno <= 0 or predlozeno > preostalo):
                predlozeno = preostalo

        korisnici_rows.append({
            "korisnik": korisnik,
            "uplata": uplata,
            "ukupno_uplaceno": ukupno_uplaceno,
            "preostalo": preostalo,
            "is_fully_paid": is_fully_paid,
            "can_submit": not (is_fully_paid and not uplata),
            "suggested_amount": predlozeno,
        })
        if not uplata and not is_fully_paid:
            unpaid_korisnici.append(korisnik)

    return render(request, "dashboard/korisnici_list.html", {
        "korisnici": korisnici,
        "korisnici_rows": korisnici_rows,
        "unpaid_korisnici": unpaid_korisnici,
        "query": query,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "month_options": MONTH_OPTIONS,
        "year_options": sorted({
            today.year,
            *KorisnikUplata.objects.filter(korisnik__dom_id=selected_dom).values_list("godina", flat=True),
        }, reverse=True) if selected_dom else [today.year],
    })


@login_required
def korisnik_uplata_set(request):
    if request.method != "POST":
        return redirect("korisnici_list")

    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može potvrđivati uplate.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))

    korisnik_id = request.POST.get("korisnik_id")
    godina = request.POST.get("godina")
    mjesec = request.POST.get("mjesec")
    action = (request.POST.get("action") or "set").strip().lower()
    iznos_raw = request.POST.get("iznos")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/korisnici/"
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/korisnici/"

    try:
        godina = int(godina)
        mjesec = int(mjesec)
    except (TypeError, ValueError):
        messages.error(request, "Neispravan period uplate.")
        return redirect(next_url)

    if mjesec < 1 or mjesec > 12:
        messages.error(request, "Neispravan mjesec.")
        return redirect(next_url)

    korisnik = get_object_or_404(Korisnik, pk=korisnik_id, dom_id__in=allowed_ids)
    postojeca_uplata = KorisnikUplata.objects.filter(korisnik=korisnik, godina=godina, mjesec=mjesec).first()

    if action == "delete":
        if postojeca_uplata:
            postojeca_uplata.delete()
            messages.success(request, "Uplata je poništena.")
        else:
            messages.info(request, "Za odabrani mjesec ne postoji evidentirana uplata.")
        return redirect(next_url)

    try:
        iznos = Decimal((iznos_raw or "").replace(",", "."))
    except Exception:
        messages.error(request, "Upišite ispravan iznos uplate.")
        return redirect(next_url)

    if iznos <= 0:
        messages.error(request, "Iznos uplate mora biti veći od 0.")
        return redirect(next_url)

    ukupno_ostalih_uplata = (
        KorisnikUplata.objects.filter(korisnik=korisnik)
        .exclude(id=postojeca_uplata.id if postojeca_uplata else None)
        .aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    )
    ukupno_za_platiti = Decimal(korisnik.iznos or 0)
    preostalo_limit = ukupno_za_platiti - ukupno_ostalih_uplata

    if preostalo_limit <= 0 and not postojeca_uplata:
        messages.error(request, "Korisnik je već uplatio puni iznos. Nije moguće dodati novu uplatu.")
        return redirect(next_url)

    if iznos > preostalo_limit:
        messages.error(request, f"Uplata ne može biti veća od preostalog iznosa ({preostalo_limit:,.2f} €).")
        return redirect(next_url)

    iznos = iznos.quantize(Decimal("0.01"))
    KorisnikUplata.objects.update_or_create(
        korisnik=korisnik,
        godina=godina,
        mjesec=mjesec,
        defaults={"iznos": iznos},
    )
    messages.success(request, "Uplata je označena kao plaćena.")
    return redirect(next_url)


@login_required
def korisnik_create(request):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može dodavati korisnike.")

    _, selected_dom, _ = resolve_selected_dom_id(request)
    if not selected_dom:
        return HttpResponseForbidden("Nemate pristup nijednom domu.")

    form = KorisnikForm(request.POST or None)

    if form.is_valid():
        instance = form.save(commit=False)
        instance.dom_id = selected_dom
        instance.save()
        return redirect("korisnici_list")

    return render(request, "dashboard/korisnik_form.html", {
        "form": form,
        "form_title": "Dodaj korisnika",
    })


@login_required
def korisnik_update(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može uređivati korisnike.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    korisnik = get_object_or_404(Korisnik, pk=pk, dom_id__in=allowed_ids)
    form = KorisnikForm(request.POST or None, instance=korisnik)

    if form.is_valid():
        form.save()
        return redirect("korisnici_list")

    return render(request, "dashboard/korisnik_form.html", {
        "form": form,
        "form_title": "Uredi korisnika",
    })


@login_required
def korisnik_delete(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može brisati korisnike.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    korisnik = get_object_or_404(Korisnik, pk=pk, dom_id__in=allowed_ids)

    if request.method == "POST":
        korisnik.delete()
        return redirect("korisnici_list")

    return render(request, "dashboard/korisnik_delete.html", {
        "korisnik": korisnik
    })

@login_required
def korisnik_detail(request, pk):

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    korisnik = get_object_or_404(Korisnik, pk=pk, dom_id__in=allowed_ids)
    uplate = KorisnikUplata.objects.filter(korisnik=korisnik).order_by("-godina", "-mjesec")
    ukupno_uplaceno = uplate.aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    ukupno_za_platiti = Decimal(korisnik.iznos or 0)
    preostalo = ukupno_za_platiti - ukupno_uplaceno

    return render(request, "dashboard/korisnik_detail.html", {
        "korisnik": korisnik,
        "uplate": uplate,
        "broj_placenih_mjeseci": uplate.count(),
        "ukupno_uplaceno": ukupno_uplaceno,
        "preostalo": preostalo,
        "mjesecna_clanarina": korisnik.mjesecna_clanarina,
    })


# ==========================================
# ZAPOSLENICI
# ==========================================

@login_required
def zaposlenici_list(request):

    _, selected_dom, _ = resolve_selected_dom_id(request)
    profil = _get_profil(request)
    query = request.GET.get("q")
    can_manage_shifts = not (profil and profil.role == "zaposlenik")

    week_start_raw = request.GET.get("week_start")
    try:
        week_start = date.fromisoformat(week_start_raw) if week_start_raw else date.today()
    except (TypeError, ValueError):
        week_start = date.today()
    week_start = week_start - timedelta(days=week_start.weekday())
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    week_end = week_days[-1]

    if not selected_dom:
        zaposlenici = Zaposlenik.objects.none()
        totals = {"bruto_sum": 0, "neto_sum": 0}
        week_rows = []
    else:
        zaposlenici = Zaposlenik.objects.filter(dom_id=selected_dom)
        if query:
            zaposlenici = zaposlenici.filter(
                Q(ime_prezime__icontains=query) | Q(pozicija__icontains=query)
            )

        totals = zaposlenici.aggregate(
            bruto_sum=Sum("bruto"),
            neto_sum=Sum("neto"),
        )

        shifts = Smjena.objects.filter(
            zaposlenik__in=zaposlenici,
            datum__range=(week_start, week_end),
        )
        shift_map = {(item.zaposlenik_id, item.datum): item.tip_smjene for item in shifts}

        week_rows = []
        for zaposlenik in zaposlenici:
            day_items = []
            for day in week_days:
                day_items.append({
                    "datum": day,
                    "tip_smjene": shift_map.get((zaposlenik.id, day), "slobodno"),
                })
            week_rows.append({
                "zaposlenik": zaposlenik,
                "days": day_items,
            })

    return render(request, "dashboard/zaposlenici_list.html", {
        "zaposlenici": zaposlenici,
        "totals": totals,
        "query": query,
        "week_days": week_days,
        "week_rows": week_rows,
        "week_start": week_start,
        "week_label": f"{week_start.strftime('%d.%m.%Y.')} - {week_end.strftime('%d.%m.%Y.')}",
        "prev_week_start": week_start - timedelta(days=7),
        "next_week_start": week_start + timedelta(days=7),
        "shift_choices": Smjena.TIP_SMJENE,
        "can_manage_shifts": can_manage_shifts,
    })


@login_required
def smjena_set(request):
    if request.method != "POST":
        return redirect("zaposlenici_list")

    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može uređivati smjene.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))

    zaposlenik_id = request.POST.get("zaposlenik_id")
    datum_raw = request.POST.get("datum")
    tip_smjene = request.POST.get("tip_smjene")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/zaposlenici/"
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/zaposlenici/"

    try:
        datum_value = date.fromisoformat(datum_raw)
    except (TypeError, ValueError):
        messages.error(request, "Neispravan datum smjene.")
        return redirect(next_url)

    if tip_smjene not in {choice[0] for choice in Smjena.TIP_SMJENE}:
        messages.error(request, "Neispravan tip smjene.")
        return redirect(next_url)

    zaposlenik = get_object_or_404(
        Zaposlenik,
        pk=zaposlenik_id,
        dom_id__in=allowed_ids,
    )

    Smjena.objects.update_or_create(
        zaposlenik=zaposlenik,
        datum=datum_value,
        defaults={"tip_smjene": tip_smjene},
    )
    messages.success(request, "Smjena je spremljena.")
    return redirect(next_url)


@login_required
def zaposlenik_create(request):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može dodavati zaposlenike.")

    _, selected_dom, _ = resolve_selected_dom_id(request)
    if not selected_dom:
        return HttpResponseForbidden("Nemate pristup nijednom domu.")

    form = ZaposlenikForm(request.POST or None)

    if form.is_valid():
        instance = form.save(commit=False)
        instance.dom_id = selected_dom
        instance.save()
        return redirect("zaposlenici_list")

    return render(request, "dashboard/zaposlenik_form.html", {
        "form": form,
        "form_title": "Dodaj zaposlenika",
    })


@login_required
def zaposlenik_update(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može uređivati zaposlenike.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    zaposlenik = get_object_or_404(Zaposlenik, pk=pk, dom_id__in=allowed_ids)
    form = ZaposlenikForm(request.POST or None, instance=zaposlenik)

    if form.is_valid():
        form.save()
        return redirect("zaposlenici_list")

    return render(request, "dashboard/zaposlenik_form.html", {
        "form": form,
        "form_title": "Uredi zaposlenika",
    })


@login_required
def zaposlenik_delete(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može brisati zaposlenike.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    zaposlenik = get_object_or_404(Zaposlenik, pk=pk, dom_id__in=allowed_ids)

    if request.method == "POST":
        zaposlenik.delete()
        return redirect("zaposlenici_list")

    return render(request, "dashboard/zaposlenik_delete.html", {
        "zaposlenik": zaposlenik
    })

@login_required
def zaposlenik_detail(request, pk):

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    zaposlenik = get_object_or_404(Zaposlenik, pk=pk, dom_id__in=allowed_ids)

    return render(request, "dashboard/zaposlenik_detail.html", {
        "zaposlenik": zaposlenik
    })


@login_required
def profil_view(request):
    profil = Profil.objects.filter(user=request.user).prefetch_related("upravljani_domovi").first()
    upravljani_domovi = profil.upravljani_domovi.all() if profil else []

    return render(request, "dashboard/profil.html", {
        "user_obj": request.user,
        "profil_obj": profil,
        "upravljani_domovi": upravljani_domovi,
    })


# ==========================================
# FINANCIJE
# ==========================================

def _add_months(value, months):
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _months_between(d1, d2):
    """Return the number of months from d1 to d2 (can be negative)."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _count_occurrences(start_date, interval_months, period_start, period_end):
    if start_date > period_end:
        return 0

    if start_date >= period_start:
        first_in_period = start_date
        steps_to_first = 0
    else:
        # Calculate how many intervals to skip to reach period_start
        months_gap = _months_between(start_date, period_start)
        steps_to_first = max(0, months_gap // interval_months)
        first_in_period = _add_months(start_date, steps_to_first * interval_months)
        # Might have landed before period_start, advance once more if needed
        if first_in_period < period_start:
            steps_to_first += 1
            first_in_period = _add_months(start_date, steps_to_first * interval_months)

    if first_in_period > period_end:
        return 0

    # Count how many occurrences fit between first_in_period and period_end
    months_remaining = _months_between(first_in_period, period_end)
    return months_remaining // interval_months + 1


def _count_occurrences_with_end(start_date, end_date, interval_months, period_start, period_end):
    if end_date and end_date < period_start:
        return 0

    effective_end = period_end if not end_date else min(period_end, end_date)
    if start_date > effective_end:
        return 0

    return _count_occurrences(start_date, interval_months, period_start, effective_end)


def _parse_period(request):
    today = date.today()
    selected_scope = request.GET.get("scope", "month")
    selected_year = request.GET.get("year")
    selected_quarter = request.GET.get("quarter", "1")
    selected_month = request.GET.get("month")

    try:
        selected_year = int(selected_year) if selected_year else today.year
    except ValueError:
        selected_year = today.year

    if selected_scope not in {"month", "quarter", "year"}:
        selected_scope = "month"

    try:
        selected_month = int(selected_month) if selected_month else today.month
    except ValueError:
        selected_month = today.month
    if selected_month < 1 or selected_month > 12:
        selected_month = today.month

    if selected_quarter not in {"1", "2", "3", "4"}:
        selected_quarter = str(((today.month - 1) // 3) + 1)

    if selected_scope == "year":
        period_start = date(selected_year, 1, 1)
        period_end = date(selected_year, 12, 31)
    elif selected_scope == "quarter":
        quarter = int(selected_quarter)
        month_start = (quarter - 1) * 3 + 1
        month_end = month_start + 2
        period_start = date(selected_year, month_start, 1)
        period_end = date(selected_year, month_end, calendar.monthrange(selected_year, month_end)[1])
    else:
        period_start = date(selected_year, selected_month, 1)
        period_end = date(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1])

    return selected_scope, selected_year, selected_quarter, selected_month, period_start, period_end


def _filter_uplate_for_period(uplate_qs, selected_scope, selected_year, selected_quarter, selected_month):
    if selected_scope == "year":
        return uplate_qs.filter(godina=selected_year)
    if selected_scope == "quarter":
        quarter = int(selected_quarter)
        quarter_months = [(quarter - 1) * 3 + i for i in (1, 2, 3)]
        return uplate_qs.filter(godina=selected_year, mjesec__in=quarter_months)
    return uplate_qs.filter(godina=selected_year, mjesec=selected_month)


def _empty_financije_context(selected_scope, selected_year, selected_quarter, selected_month):
    return {
        "korisnici_primanja": Decimal("0"),
        "investicije_sum": Decimal("0"),
        "place_sum": Decimal("0"),
        "rezije_sum": Decimal("0"),
        "kuhinja_sum": Decimal("0"),
        "popravci_sum": Decimal("0"),
        "opcenito_sum": Decimal("0"),
        "ukupna_primanja": Decimal("0"),
        "ukupni_troskovi": Decimal("0"),
        "saldo": Decimal("0"),
        "investicije": Investicija.objects.none(),
        "korisnici_uplate": KorisnikUplata.objects.none(),
        "troskovi": Trosak.objects.none(),
        "rezije": Rezija.objects.none(),
        "selected_scope": selected_scope,
        "selected_year": selected_year,
        "selected_quarter": selected_quarter,
        "selected_month": selected_month,
        "year_options": [date.today().year],
        "month_options": MONTH_OPTIONS,
    }


def _build_financije_context(selected_dom, selected_scope, selected_year, selected_quarter, selected_month, period_start, period_end):
    if not selected_dom:
        return _empty_financije_context(selected_scope, selected_year, selected_quarter, selected_month)

    korisnici_primanja = _filter_uplate_for_period(
        KorisnikUplata.objects.filter(korisnik__dom_id=selected_dom),
        selected_scope,
        selected_year,
        selected_quarter,
        selected_month,
    ).aggregate(total=Sum("iznos"))["total"] or Decimal("0")

    investicije_qs = Investicija.objects.filter(
        dom_id=selected_dom,
        datum__range=(period_start, period_end),
    ).order_by("-datum", "-id")
    investicije_sum = investicije_qs.aggregate(total=Sum("iznos"))["total"] or Decimal("0")
    korisnici_uplate_qs = _filter_uplate_for_period(
        KorisnikUplata.objects.filter(korisnik__dom_id=selected_dom).select_related("korisnik"),
        selected_scope,
        selected_year,
        selected_quarter,
        selected_month,
    ).order_by("-godina", "-mjesec", "-datum_potvrde")

    place_sum = Decimal("0")
    for zaposlenik in Zaposlenik.objects.filter(dom_id=selected_dom):
        monthly = Decimal(zaposlenik.bruto)
        count = _count_occurrences(zaposlenik.datum_ugovora, 1, period_start, period_end)
        place_sum += monthly * count

    rezije_qs = Rezija.objects.filter(dom_id=selected_dom).order_by("naziv")
    rezije_sum = Decimal("0")
    for rezija in rezije_qs:
        if not rezija.aktivna:
            continue
        interval_months = INTERVAL_TO_MONTHS.get(rezija.interval, 1)
        if interval_months is None:
            if rezija.datum_zavrsetka:
                count = 1 if period_start <= rezija.datum_pocetka <= period_end and rezija.datum_pocetka <= rezija.datum_zavrsetka else 0
            else:
                count = 1 if period_start <= rezija.datum_pocetka <= period_end else 0
        else:
            count = _count_occurrences_with_end(
                rezija.datum_pocetka,
                rezija.datum_zavrsetka,
                interval_months,
                period_start,
                period_end,
            )
        rezije_sum += Decimal(rezija.iznos) * count

    troskovi_qs = Trosak.objects.filter(
        dom_id=selected_dom,
        datum__range=(period_start, period_end),
    ).order_by("-datum", "-id")
    troskovi_agg = troskovi_qs.values("kategorija").annotate(total=Sum("iznos"))
    troskovi_po_kategoriji = {row["kategorija"]: row["total"] or Decimal("0") for row in troskovi_agg}

    kuhinja_sum = troskovi_po_kategoriji.get("kuhinja", Decimal("0"))
    popravci_sum = troskovi_po_kategoriji.get("popravci", Decimal("0"))
    opcenito_sum = troskovi_po_kategoriji.get("opcenito", Decimal("0"))

    ukupna_primanja = korisnici_primanja + investicije_sum
    ukupni_troskovi = place_sum + rezije_sum + kuhinja_sum + popravci_sum + opcenito_sum
    saldo = ukupna_primanja - ukupni_troskovi

    year_options = _build_year_options([selected_dom])

    return {
        "korisnici_primanja": korisnici_primanja,
        "investicije_sum": investicije_sum,
        "place_sum": place_sum,
        "rezije_sum": rezije_sum,
        "kuhinja_sum": kuhinja_sum,
        "popravci_sum": popravci_sum,
        "opcenito_sum": opcenito_sum,
        "ukupna_primanja": ukupna_primanja,
        "ukupni_troskovi": ukupni_troskovi,
        "saldo": saldo,
        "investicije": investicije_qs,
        "korisnici_uplate": korisnici_uplate_qs,
        "troskovi": troskovi_qs,
        "rezije": rezije_qs,
        "selected_scope": selected_scope,
        "selected_year": selected_year,
        "selected_quarter": selected_quarter,
        "selected_month": selected_month,
        "year_options": year_options,
        "month_options": MONTH_OPTIONS,
    }

def _financije_view(request, template_name):
    """Shared financije view logic for all financije pages."""
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik nema pristup financijama.")

    _, selected_dom, _ = resolve_selected_dom_id(request)
    selected_scope, selected_year, selected_quarter, selected_month, period_start, period_end = _parse_period(request)
    context = _build_financije_context(
        selected_dom, selected_scope, selected_year, selected_quarter, selected_month, period_start, period_end
    )
    return render(request, template_name, context)


@login_required
def financije(request):
    return _financije_view(request, "dashboard/financije.html")


@login_required
def financije_primanja(request):
    return _financije_view(request, "dashboard/financije_primanja.html")


@login_required
def financije_troskovi(request):
    return _financije_view(request, "dashboard/financije_troskovi.html")


@login_required
def financije_rezije(request):
    return _financije_view(request, "dashboard/financije_rezije.html")


@login_required
def investicija_create(request):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik nema pristup investicijama.")

    _, selected_dom, _ = resolve_selected_dom_id(request)
    if not selected_dom:
        return HttpResponseForbidden("Nemate pristup nijednom domu.")

    form = InvesticijaForm(request.POST or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.dom_id = selected_dom
        instance.save()
        return redirect("financije")

    return render(request, "dashboard/investicija_form.html", {"form": form})


@login_required
def investicija_update(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik nema pristup investicijama.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    investicija = get_object_or_404(Investicija, pk=pk, dom_id__in=allowed_ids)

    form = InvesticijaForm(request.POST or None, instance=investicija)
    if form.is_valid():
        form.save()
        return redirect("financije")

    return render(request, "dashboard/investicija_form.html", {"form": form})


@login_required
def investicija_delete(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik nema pristup investicijama.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    investicija = get_object_or_404(Investicija, pk=pk, dom_id__in=allowed_ids)

    if request.method == "POST":
        investicija.delete()
        return redirect("financije")

    return render(request, "dashboard/investicija_delete.html", {"investicija": investicija})


@login_required
def investicija_detail(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik nema pristup investicijama.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    investicija = get_object_or_404(Investicija, pk=pk, dom_id__in=allowed_ids)

    return render(request, "dashboard/investicija_detail.html", {"investicija": investicija})


@login_required
def trosak_create(request):
    profil = _get_profil(request)
    _, selected_dom, _ = resolve_selected_dom_id(request)
    if not selected_dom:
        return HttpResponseForbidden("Nemate pristup nijednom domu.")

    form = TrosakForm(request.POST or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.dom_id = selected_dom
        instance.save()
        messages.success(request, "Trošak je uspješno spremljen.")
        if profil and profil.role == "zaposlenik":
            return redirect("dashboard")
        return redirect("financije")
    if request.method == "POST":
        messages.error(request, "Spremanje troška nije uspjelo. Provjerite unesene podatke.")

    return render(request, "dashboard/trosak_form.html", {"form": form})


@login_required
def trosak_update(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može uređivati troškove.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    trosak = get_object_or_404(Trosak, pk=pk, dom_id__in=allowed_ids)

    form = TrosakForm(request.POST or None, instance=trosak)
    if form.is_valid():
        form.save()
        return redirect("financije")

    return render(request, "dashboard/trosak_form.html", {"form": form})


@login_required
def trosak_delete(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može brisati troškove.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    trosak = get_object_or_404(Trosak, pk=pk, dom_id__in=allowed_ids)

    if request.method == "POST":
        trosak.delete()
        return redirect("financije")

    return render(request, "dashboard/trosak_delete.html", {"trosak": trosak})


@login_required
def trosak_detail(request, pk):
    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    trosak = get_object_or_404(Trosak, pk=pk, dom_id__in=allowed_ids)

    return render(request, "dashboard/trosak_detail.html", {"trosak": trosak})


@login_required
def rezija_create(request):
    profil = _get_profil(request)
    _, selected_dom, _ = resolve_selected_dom_id(request)
    if not selected_dom:
        return HttpResponseForbidden("Nemate pristup nijednom domu.")

    form = RezijaForm(request.POST or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.dom_id = selected_dom
        instance.save()
        messages.success(request, "Režija je uspješno spremljena.")
        if profil and profil.role == "zaposlenik":
            return redirect("dashboard")
        return redirect("financije")
    if request.method == "POST":
        messages.error(request, "Spremanje režije nije uspjelo. Provjerite unesene podatke.")

    return render(request, "dashboard/rezija_form.html", {"form": form})


@login_required
def rezija_update(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može uređivati režije.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    rezija = get_object_or_404(Rezija, pk=pk, dom_id__in=allowed_ids)

    form = RezijaForm(request.POST or None, instance=rezija)
    if form.is_valid():
        form.save()
        return redirect("financije")

    return render(request, "dashboard/rezija_form.html", {"form": form})


@login_required
def rezija_delete(request, pk):
    profil = _get_profil(request)
    if profil and profil.role == "zaposlenik":
        return HttpResponseForbidden("Zaposlenik ne može brisati režije.")

    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    rezija = get_object_or_404(Rezija, pk=pk, dom_id__in=allowed_ids)

    if request.method == "POST":
        rezija.delete()
        return redirect("financije")

    return render(request, "dashboard/rezija_delete.html", {"rezija": rezija})


@login_required
def rezija_detail(request, pk):
    allowed_domovi, _, _ = resolve_selected_dom_id(request)
    allowed_ids = list(allowed_domovi.values_list("id", flat=True))
    rezija = get_object_or_404(Rezija, pk=pk, dom_id__in=allowed_ids)

    return render(request, "dashboard/rezija_detail.html", {"rezija": rezija})
