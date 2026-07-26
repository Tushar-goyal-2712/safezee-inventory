from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("item/add/", views.add_item, name="add_item"),
    path("item/<int:item_id>/delete/", views.delete_item, name="delete_item"),
    path("location/add/", views.add_location, name="add_location"),
    path("inventory/save/", views.save_inventory, name="save_inventory"),
    path("search/", views.search_items, name="search_items"),
]
