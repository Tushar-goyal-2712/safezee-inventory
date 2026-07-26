# SAFEZEE Inventory

Internal fire-extinguisher stock tracker for SAFEZEE Fire Protection.
Single person, no username/password — sign-in is via **passkey**
(Face ID / Touch ID / Windows Hello / security key). Django +
PostgreSQL (Neon) + Bootstrap 5 + vanilla JS.

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` and fill in:
- `DATABASE_URL` — your Neon PostgreSQL connection string
- `DJANGO_SECRET_KEY` — any long random string
- `PASSKEY_ENROLLMENT_SECRET` — generate one with:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- For **local development**, leave `PASSKEY_RP_ID=localhost` and
  `PASSKEY_ORIGIN=http://localhost:8000` as-is — passkeys work over
  plain HTTP only on `localhost`.
- For **production**, set `PASSKEY_RP_ID` to your real bare domain
  (e.g. `inventory.safezee.in`, no `https://`, no port) and
  `PASSKEY_ORIGIN` to the exact URL shown in the browser address bar
  (e.g. `https://inventory.safezee.in`). **The site must be served
  over HTTPS** — browsers block WebAuthn on plain HTTP for any host
  other than localhost.

## 2. Database

```bash
python manage.py migrate
```

This automatically creates the **Godown** location on first migrate
(see `inventory/apps.py`). No fixtures needed.

## 3. Register your passkey (one-time, per device)

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/accounts/register/**, enter the
`PASSKEY_ENROLLMENT_SECRET` from your `.env`, give the device a
label (e.g. "Tushar's iPhone"), and follow the Face ID / Touch ID
prompt. You're now signed in and redirected to the dashboard.

Repeat this once for every device you want to use (phone, laptop,
etc) — each gets its own passkey. Keep the enrollment secret private;
anyone who has it can register a device and gain access. You can
rotate it any time by changing the env var (existing registered
devices are unaffected).

## 4. Everyday use

Visit **http://127.0.0.1:8000/** — you'll be redirected to
**/accounts/login/** if not already signed in. Tap "Sign in with
Face ID / Touch ID", approve the biometric prompt, and you land on
the dashboard. Sessions persist until you tap "Sign out" or clear
cookies.

Optionally create a Django superuser to use `/admin/` for direct data
fixes or to remove a lost device's passkey:

```bash
python manage.py createsuperuser
```

## 5. How the inventory logic works

- **Add Item** — creates the item and an Inventory row at every
  existing location. The quantity you enter goes to Godown; every
  other location starts at 0.
- **Add Location** — creates the location and an Inventory row
  (quantity 0) for every existing item.
- **Edit a location** — click *Edit* on a card. Only that card enters
  edit mode; `+`/`-` only change numbers on screen (nothing is saved
  yet). If you're editing any location other than Godown, each `+`/`-`
  also nudges the Godown card's on-screen number in the opposite
  direction, so you can see the transfer before committing it.
- **Save** — sends one request with every changed quantity for that
  card. The server re-validates everything and writes both the
  location and Godown (if applicable) inside a single atomic
  transaction. If Godown would go negative, the whole save is
  rejected and nothing is written.
- **Cancel** — discards all on-screen changes, including the mirrored
  Godown preview, and restores the original numbers.
- **Search** — filters items instantly across every card, client-side.
- **Delete item** — removes the item and its rows at every location.

## 6. Project structure

```
safezee_inventory/
    safezee_inventory/      # project settings, urls, wsgi/asgi
    accounts/                # passkey (WebAuthn) authentication
        models.py             # PasskeyCredential
        views.py               # registration + login endpoints
        middleware.py          # gates the whole site behind login
        urls.py
        admin.py
        migrations/
        templates/accounts/
            login.html
            register.html
        static/js/passkey.js   # WebAuthn client logic
    inventory/
        models.py             # Item, Location, Inventory
        views.py                # dashboard + JSON endpoints
        urls.py
        forms.py
        admin.py
        apps.py                 # auto-creates Godown on migrate
        migrations/
        templates/inventory/
            base.html
            dashboard.html
            add_item.html        # modal partial
            add_location.html    # modal partial
        static/
            css/style.css
            js/inventory.js
    manage.py
    requirements.txt
    .env.example
```

## 7. Deploying

The project is preconfigured with WhiteNoise so `collectstatic` +
`gunicorn` works out of the box on most PaaS providers:

```bash
python manage.py collectstatic --noinput
gunicorn safezee_inventory.wsgi:application
```

Set in production:
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS` to your real domain
- `PASSKEY_RP_ID` and `PASSKEY_ORIGIN` to your real HTTPS domain
- A fresh `PASSKEY_ENROLLMENT_SECRET`

**HTTPS is mandatory** for passkeys to work anywhere other than
`localhost` — make sure your host/proxy terminates TLS before you
try to register or sign in on the deployed URL.
