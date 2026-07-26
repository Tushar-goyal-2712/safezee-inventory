from django.shortcuts import redirect
from django.urls import reverse

# URL path prefixes that must remain reachable WITHOUT being logged in
# (otherwise nobody could ever reach the login/registration pages).
_PUBLIC_PREFIXES = (
    "/accounts/",
    "/static/",
    "/admin/",
)


class PasskeyAuthMiddleware:
    """
    Blocks every request to the app until the session has been marked
    authenticated via a successful passkey login. This is the entire
    access-control layer for SAFEZEE Inventory — there is no Django
    User model involved.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES):
            return self.get_response(request)

        if request.session.get("sz_authenticated"):
            return self.get_response(request)

        return redirect(f"{reverse('accounts:login')}?next={path}")
