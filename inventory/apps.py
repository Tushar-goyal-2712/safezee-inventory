from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_default_godown(sender, **kwargs):
    """
    Ensure the 'Godown' location always exists.

    Runs after every `migrate`. Safe to run repeatedly — get_or_create
    is idempotent, so this will not create duplicates or overwrite
    an existing Godown location or its inventory.
    """
    from inventory.models import Location, Item, Inventory

    godown, created = Location.objects.get_or_create(name="Godown")

    if created:
        # If items already exist (e.g. re-running migrate on an
        # existing DB after Godown was somehow deleted), backfill
        # inventory rows for the new Godown so nothing is missing.
        for item in Item.objects.all():
            Inventory.objects.get_or_create(
                item=item, location=godown, defaults={"quantity": 0}
            )


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = "SAFEZEE Inventory"

    def ready(self):
        post_migrate.connect(create_default_godown, sender=self)
