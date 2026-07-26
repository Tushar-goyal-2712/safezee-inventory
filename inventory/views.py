import json

from django.db import transaction
from django.db.models import ProtectedError
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_GET

from .forms import AddItemForm, AddLocationForm
from .models import Item, Location, Inventory

GODOWN_NAME = "Godown"

# Maps recognizable location-name keywords to a Bootstrap Icon class,
# so the dashboard looks intentional rather than generic. Falls back
# to a generic pin icon for anything unrecognized.
_LOCATION_ICON_KEYWORDS = (
    ("godown", "bi-box-seam-fill"),
    ("flat", "bi-house-door-fill"),
    ("tender", "bi-truck-front-fill"),
    ("office", "bi-building-fill"),
    ("site", "bi-geo-alt-fill"),
    ("warehouse", "bi-boxes"),
)


def _icon_for_location(name):
    lowered = name.lower()
    for keyword, icon in _LOCATION_ICON_KEYWORDS:
        if keyword in lowered:
            return icon
    return "bi-pin-map-fill"


def _get_or_create_godown():
    godown, _ = Location.objects.get_or_create(name=GODOWN_NAME)
    return godown


@require_GET
@ensure_csrf_cookie
def dashboard(request):
    """
    Single-page dashboard: every location rendered as a card, every
    item within it as a row. Godown is always shown first.
    """
    locations = list(Location.objects.all().order_by("id"))
    # Ensure Godown appears first regardless of insertion order.
    locations.sort(key=lambda loc: (not loc.is_godown, loc.id))

    board = []
    for loc in locations:
        rows = (
            Inventory.objects.filter(location=loc)
            .select_related("item")
            .order_by("item__name")
        )
        board.append({
            "location": loc,
            "rows": rows,
            "icon": _icon_for_location(loc.name),
        })

    context = {
        "board": board,
        "item_count": Item.objects.count(),
        "location_count": Location.objects.count(),
    }
    return render(request, "inventory/dashboard.html", context)


@require_POST
def add_item(request):
    """
    Create a new Item, then create an Inventory row for every
    existing Location. The initial quantity goes to Godown; every
    other location starts at 0.
    """
    form = AddItemForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    name = form.cleaned_data["name"]
    quantity = form.cleaned_data["quantity"]

    godown = _get_or_create_godown()

    with transaction.atomic():
        item = Item.objects.create(name=name)

        locations = Location.objects.select_for_update().all()
        inventories = []
        for loc in locations:
            qty = quantity if loc.pk == godown.pk else 0
            inventories.append(Inventory(item=item, location=loc, quantity=qty))
        Inventory.objects.bulk_create(inventories)

    return JsonResponse({
        "ok": True,
        "item": {"id": item.id, "name": item.name},
        "message": f"'{item.name}' added to all locations.",
    })


@require_POST
def add_location(request):
    """
    Create a new Location, then create an Inventory row (quantity 0)
    for every existing Item.
    """
    form = AddLocationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    name = form.cleaned_data["name"]

    with transaction.atomic():
        location = Location.objects.create(name=name)

        items = Item.objects.select_for_update().all()
        inventories = [
            Inventory(item=item, location=location, quantity=0) for item in items
        ]
        Inventory.objects.bulk_create(inventories)

    return JsonResponse({
        "ok": True,
        "location": {"id": location.id, "name": location.name},
        "message": f"'{location.name}' added with all items at 0.",
    })


@require_POST
def delete_item(request, item_id):
    """Delete an Item and (via CASCADE) its Inventory rows at every location."""
    item = get_object_or_404(Item, pk=item_id)
    name = item.name
    try:
        item.delete()
    except ProtectedError:
        return JsonResponse(
            {"ok": False, "message": "This item could not be deleted."}, status=400
        )
    return JsonResponse({"ok": True, "message": f"'{name}' deleted from all locations."})


@require_POST
def save_inventory(request):
    """
    Persist edits made to ONE location in a single request.

    Expected JSON body:
    {
        "location_id": 3,
        "items": [{"item_id": 1, "quantity": 5}, {"item_id": 2, "quantity": 10}]
    }

    Rules:
    - If the edited location IS Godown, quantities are simply set —
      Godown is the master, so editing it directly does not draw
      from/give to anywhere else.
    - If the edited location is NOT Godown, every quantity change
      (delta) is mirrored as an equal-and-opposite change to Godown's
      stock for that same item (a "transfer"). If any resulting
      Godown quantity would go negative, the ENTIRE save is rejected
      and nothing is written.
    - Everything happens in one atomic transaction.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "Invalid request body."}, status=400)

    location_id = payload.get("location_id")
    items_payload = payload.get("items", [])

    if not location_id or not isinstance(items_payload, list) or not items_payload:
        return JsonResponse({"ok": False, "message": "No changes submitted."}, status=400)

    location = get_object_or_404(Location, pk=location_id)
    godown = _get_or_create_godown()
    editing_godown_directly = location.pk == godown.pk

    # Normalize + validate the incoming quantities up front.
    clean_changes = []
    for row in items_payload:
        try:
            item_id = int(row["item_id"])
            new_quantity = int(row["quantity"])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({"ok": False, "message": "Malformed item data."}, status=400)

        if new_quantity < 0:
            return JsonResponse(
                {"ok": False, "message": "Quantity cannot be negative."}, status=400
            )
        clean_changes.append((item_id, new_quantity))

    try:
        with transaction.atomic():
            updated_location_rows = {}
            updated_godown_rows = {}

            for item_id, new_quantity in clean_changes:
                loc_inv = (
                    Inventory.objects.select_for_update()
                    .select_related("item")
                    .get(item_id=item_id, location=location)
                )
                delta = new_quantity - loc_inv.quantity

                if editing_godown_directly:
                    loc_inv.quantity = new_quantity
                    loc_inv.save(update_fields=["quantity"])
                    updated_location_rows[item_id] = new_quantity
                else:
                    godown_inv = Inventory.objects.select_for_update().get(
                        item_id=item_id, location=godown
                    )
                    new_godown_quantity = godown_inv.quantity - delta

                    if new_godown_quantity < 0:
                        raise ValueError(
                            f"Not enough stock available in Godown for "
                            f"'{loc_inv.item.name}'."
                        )

                    loc_inv.quantity = new_quantity
                    loc_inv.save(update_fields=["quantity"])
                    godown_inv.quantity = new_godown_quantity
                    godown_inv.save(update_fields=["quantity"])

                    updated_location_rows[item_id] = new_quantity
                    updated_godown_rows[item_id] = new_godown_quantity

    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse({
        "ok": True,
        "message": "Inventory updated.",
        "location_id": location.pk,
        "godown_id": godown.pk,
        "location_rows": updated_location_rows,
        "godown_rows": updated_godown_rows,
    })


@require_GET
def search_items(request):
    """
    Optional server-side search endpoint (the dashboard also filters
    client-side instantly, but this exists for completeness / can be
    used if the item list grows large).
    """
    query = request.GET.get("q", "").strip()
    items = Item.objects.filter(name__icontains=query).order_by("name") if query else Item.objects.all()
    return JsonResponse({"items": [{"id": i.id, "name": i.name} for i in items]})
