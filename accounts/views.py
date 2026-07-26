import hmac
import json

from safezee_inventory import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from webauthn.helpers import parse_registration_credential_json

import webauthn
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
    AuthenticationCredential,
)
from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse

from .models import PasskeyCredential
from .webauthn_utils import bytes_to_b64url, b64url_to_bytes

SESSION_KEY_AUTHENTICATED = "sz_authenticated"
SESSION_KEY_REG_CHALLENGE = "sz_reg_challenge"
SESSION_KEY_AUTH_CHALLENGE = "sz_auth_challenge"

# A fixed "user handle" — WebAuthn requires one, but since this app
# has exactly one person, we don't need a real user table.
SINGLE_USER_HANDLE = b"safezee-owner"
SINGLE_USER_NAME = "owner"
SINGLE_USER_DISPLAY_NAME = "SAFEZEE Inventory"


def _check_enrollment_secret(request):
    """Constant-time comparison against DJANGO_ENROLLMENT_SECRET."""
    try:
        provided = json.loads(request.body or b"{}").get("secret", "")
    except (json.JSONDecodeError, UnicodeDecodeError):
        provided = ""
    expected = settings.PASSKEY_ENROLLMENT_SECRET
    if not expected:
        return False
    return hmac.compare_digest(str(provided), str(expected))


# ------------------------------------------------------------------
# PAGES
# ------------------------------------------------------------------
@require_GET
@ensure_csrf_cookie
def login_page(request):
    if request.session.get(SESSION_KEY_AUTHENTICATED):
        return redirect("/")
    has_credentials = PasskeyCredential.objects.exists()
    return render(request, "accounts/login.html", {"has_credentials": has_credentials})


@require_GET
@ensure_csrf_cookie
def register_page(request):
    return render(request, "accounts/register.html")


@require_POST
def logout_view(request):
    request.session.flush()
    return redirect("accounts:login")


# ------------------------------------------------------------------
# REGISTRATION (enrolling a new passkey — protected by a shared secret)
# ------------------------------------------------------------------
@require_POST
def registration_options(request):
    if not _check_enrollment_secret(request):
        return HttpResponseForbidden("Invalid enrollment secret.")

    existing = PasskeyCredential.objects.all()
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.credential_id))
        for c in existing
    ]

    options = webauthn.generate_registration_options(
        rp_id=settings.PASSKEY_RP_ID,
        rp_name=settings.PASSKEY_RP_NAME,
        user_id=SINGLE_USER_HANDLE,
        user_name=SINGLE_USER_NAME,
        user_display_name=SINGLE_USER_DISPLAY_NAME,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    request.session[SESSION_KEY_REG_CHALLENGE] = bytes_to_b64url(options.challenge)

    return JsonResponse(json.loads(webauthn.options_to_json(options)))


@require_POST
def registration_verify(request):
    if not _check_enrollment_secret(request):
        return HttpResponseForbidden("Invalid enrollment secret.")

    challenge_b64 = request.session.get(SESSION_KEY_REG_CHALLENGE)
    if not challenge_b64:
        return JsonResponse({"ok": False, "message": "No registration in progress."}, status=400)

    try:
        body = json.loads(request.body.decode("utf-8"))
        credential_json = json.dumps(body.get("credential"))
        device_label = (body.get("device_label") or "").strip()[:100]

        credential = parse_registration_credential_json(credential_json)

        verified = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=b64url_to_bytes(challenge_b64),
            expected_rp_id=settings.PASSKEY_RP_ID,
            expected_origin=settings.PASSKEY_ORIGIN,
            require_user_verification=True,
        )
    except InvalidRegistrationResponse as exc:
        return JsonResponse({"ok": False, "message": f"Could not verify passkey: {exc}"}, status=400)
    except Exception as exc:  # noqa: BLE001 — surface any parsing error to the client
        return JsonResponse({"ok": False, "message": f"Registration failed: {exc}"}, status=400)

    PasskeyCredential.objects.create(
        credential_id=bytes_to_b64url(verified.credential_id),
        public_key=bytes_to_b64url(verified.credential_public_key),
        sign_count=verified.sign_count,
        device_label=device_label,
    )

    del request.session[SESSION_KEY_REG_CHALLENGE]
    request.session[SESSION_KEY_AUTHENTICATED] = True

    return JsonResponse({"ok": True, "message": "Passkey registered.", "redirect": "/"})


# ------------------------------------------------------------------
# LOGIN (authenticating with an already-registered passkey)
# ------------------------------------------------------------------
@require_POST
def authentication_options(request):
    credentials = PasskeyCredential.objects.all()
    if not credentials.exists():
        return JsonResponse(
            {"ok": False, "message": "No passkey has been registered yet."}, status=400
        )

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.credential_id))
        for c in credentials
    ]

    options = webauthn.generate_authentication_options(
        rp_id=settings.PASSKEY_RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    request.session[SESSION_KEY_AUTH_CHALLENGE] = bytes_to_b64url(options.challenge)

    return JsonResponse(json.loads(webauthn.options_to_json(options)))


@require_POST
def authentication_verify(request):
    challenge_b64 = request.session.get(SESSION_KEY_AUTH_CHALLENGE)
    if not challenge_b64:
        return JsonResponse({"ok": False, "message": "No login attempt in progress."}, status=400)

    try:
        body = json.loads(request.body.decode("utf-8"))
        credential_json = json.dumps(body.get("credential"))
        credential = AuthenticationCredential.parse_raw(credential_json)

        stored = PasskeyCredential.objects.get(
            credential_id=bytes_to_b64url(credential.raw_id)
        )

        verified = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=b64url_to_bytes(challenge_b64),
            expected_rp_id=settings.PASSKEY_RP_ID,
            expected_origin=settings.PASSKEY_ORIGIN,
            credential_public_key=b64url_to_bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except PasskeyCredential.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Unrecognized passkey."}, status=400)
    except InvalidAuthenticationResponse as exc:
        return JsonResponse({"ok": False, "message": f"Could not verify passkey: {exc}"}, status=400)
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"ok": False, "message": f"Login failed: {exc}"}, status=400)

    stored.sign_count = verified.new_sign_count
    stored.last_used_at = timezone.now()
    stored.save(update_fields=["sign_count", "last_used_at"])

    del request.session[SESSION_KEY_AUTH_CHALLENGE]
    request.session[SESSION_KEY_AUTHENTICATED] = True

    return JsonResponse({"ok": True, "message": "Signed in.", "redirect": "/"})
