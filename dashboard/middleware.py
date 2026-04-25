from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User


class ForcePasswordChangeMiddleware:
    EXEMPT_PREFIXES = ('/change-password/', '/logout/', '/admin/', '/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
                try:
                    if request.user.user_profile.must_change_password:
                        from django.shortcuts import redirect
                        return redirect('change_password')
                except Exception:
                    pass  # No UserProfile yet — skip redirect
        return self.get_response(request)


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
