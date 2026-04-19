from .models import Profil
from .dom_access import resolve_selected_dom_id


def global_dom_context(request):

    if not request.user.is_authenticated:
        return {}

    if not hasattr(request, "_cached_profil"):
        request._cached_profil = Profil.objects.filter(user=request.user).select_related("dom").first()
    profil = request._cached_profil

    if profil is None:
        return {
            "domovi": [],
            "selected_dom": None,
            "profil": None,
            "show_dom_dropdown": False,
        }

    domovi, selected_dom, role = resolve_selected_dom_id(request)
    show_dom_dropdown = role in {"admin", "upravitelj"} and domovi.exists()

    return {
        "domovi": domovi,
        "selected_dom": selected_dom,
        "profil": profil,
        "show_dom_dropdown": show_dom_dropdown,
    }
