from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from dashboard.dom_access import get_allowed_domovi_for_user, resolve_selected_dom_id
from dashboard.models import Dom, Klijent, Profil


class DomAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.klijent = Klijent.objects.create(naziv="Klijent A")
        self.dom_a = Dom.objects.create(naziv="Dom A", kapacitet=10, klijent=self.klijent)
        self.dom_b = Dom.objects.create(naziv="Dom B", kapacitet=15, klijent=self.klijent)

    def _request_with_user(self, user):
        request = self.factory.get("/")
        request.user = user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        return request

    def test_admin_gets_all_domovi(self):
        user = User.objects.create_user(username="admin")
        Profil.objects.create(user=user, dom=self.dom_a, role="admin")

        domovi, role = get_allowed_domovi_for_user(user)

        self.assertEqual(role, "admin")
        self.assertCountEqual(domovi.values_list("id", flat=True), [self.dom_a.id, self.dom_b.id])

    def test_upravitelj_gets_only_assigned_domovi(self):
        user = User.objects.create_user(username="upravitelj")
        profil = Profil.objects.create(user=user, dom=self.dom_a, role="upravitelj")
        profil.upravljani_domovi.add(self.dom_b)

        domovi, role = get_allowed_domovi_for_user(user)

        self.assertEqual(role, "upravitelj")
        self.assertCountEqual(domovi.values_list("id", flat=True), [self.dom_b.id])

    def test_resolve_selected_dom_falls_back_when_posted_not_allowed(self):
        user = User.objects.create_user(username="zaposlenik")
        Profil.objects.create(user=user, dom=self.dom_a, role="zaposlenik")
        request = self._request_with_user(user)

        domovi, selected_dom_id, role = resolve_selected_dom_id(request, posted_dom_id=str(self.dom_b.id))

        self.assertEqual(role, "zaposlenik")
        self.assertEqual(selected_dom_id, self.dom_a.id)
        self.assertEqual(request.session.get("selected_dom"), self.dom_a.id)
        self.assertCountEqual(domovi.values_list("id", flat=True), [self.dom_a.id])
