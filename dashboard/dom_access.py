from .models import Dom, Profil


def get_allowed_domovi_for_user(user, profil=None):
    if profil is None:
        profil = Profil.objects.filter(user=user).select_related("dom").first()

    if not profil:
        return Dom.objects.none(), None

    if profil.role == "admin":
        return Dom.objects.all(), "admin"

    if profil.role == "upravitelj":
        upravitelj_domovi = profil.upravljani_domovi.all()
        if upravitelj_domovi.exists():
            return upravitelj_domovi, "upravitelj"
        if profil.dom_id:
            return Dom.objects.filter(id=profil.dom_id), "upravitelj"
        return Dom.objects.none(), "upravitelj"

    if profil.dom_id:
        return Dom.objects.filter(id=profil.dom_id), profil.role

    return Dom.objects.none(), profil.role


def resolve_selected_dom_id(request, posted_dom_id=None):
    cached_profil = getattr(request, "_cached_profil", None)
    domovi, role = get_allowed_domovi_for_user(request.user, profil=cached_profil)
    allowed_ids = set(domovi.values_list("id", flat=True))

    chosen = None
    if posted_dom_id is not None:
        try:
            posted_dom_id = int(posted_dom_id)
        except (TypeError, ValueError):
            posted_dom_id = None
        if posted_dom_id in allowed_ids:
            chosen = posted_dom_id

    if chosen is None:
        current = request.session.get("selected_dom")
        if current in allowed_ids:
            chosen = current

    if chosen is None:
        chosen = domovi.values_list("id", flat=True).first()

    if chosen is None:
        request.session.pop("selected_dom", None)
    else:
        request.session["selected_dom"] = chosen

    return domovi, chosen, role
