from django import forms
from .models import Item, Location


class AddItemForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. ABC 4 KG",
            "autofocus": True,
        }),
    )
    quantity = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"}),
        help_text="Initial quantity — added to Godown. Every other location starts at 0.",
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Item name cannot be empty.")
        if Item.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(f"An item named '{name}' already exists.")
        return name


class AddLocationForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Warehouse",
            "autofocus": True,
        }),
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Location name cannot be empty.")
        if Location.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(f"A location named '{name}' already exists.")
        return name
