from django.db import models
from django.core.validators import MinValueValidator


class Item(models.Model):
    """A type of fire extinguisher, e.g. 'ABC 4 KG', 'CO2 4.5 KG'."""

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    """A physical location that holds stock, e.g. 'Godown', 'Flat'."""

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    @property
    def is_godown(self):
        return self.name.strip().lower() == "godown"


class Inventory(models.Model):
    """
    Stock count of a specific Item at a specific Location.

    Godown is the master stock. Quantities anywhere must never be
    negative, enforced both at the application layer (see views.py)
    and here at the database layer as a safety net.
    """

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="inventories")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="inventories")
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ("item", "location")
        ordering = ["location__id", "item__name"]
        verbose_name_plural = "Inventories"

    def __str__(self):
        return f"{self.item.name} @ {self.location.name}: {self.quantity}"
