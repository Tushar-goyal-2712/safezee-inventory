from django.contrib import admin
from .models import Item, Location, Inventory


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "location", "quantity")
    list_filter = ("location", "item")
    search_fields = ("item__name", "location__name")
    autocomplete_fields = ("item", "location")
