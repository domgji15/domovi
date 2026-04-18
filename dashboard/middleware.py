from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User

class AutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.AUTO_LOGIN_ENABLED and not request.user.is_authenticated:
            preferred_username = (settings.AUTO_LOGIN_USERNAME or "").strip()
            if preferred_username:
                user = User.objects.filter(username=preferred_username).first()
            else:
                user = User.objects.filter(is_superuser=True).order_by("id").first() or User.objects.order_by("id").first()
            if user:
                login(request, user)
        return self.get_response(request)
