from django.urls import reverse
from simple_menu import Menu, MenuItem

from main.menu_item import HumitifierMenuItem

Menu.add_item(
    "main",
    HumitifierMenuItem(
        "Reporting",
        None,
        weight=30,
        icon="icons/document-check.html",
        check=lambda request: request.user.is_authenticated,
        children=[
            HumitifierMenuItem(
                "Costs calculator",
                reverse("reporting:cost_calculator"),
                icon="icons/euro.html",
                check=lambda request: request.user.is_authenticated,
            ),
            HumitifierMenuItem(
                "Server cost overview",
                reverse("reporting:server_cost_overview"),
                icon="icons/creditcard.html",
                check=lambda request: request.user.is_authenticated,
            ),
            HumitifierMenuItem(
                "Costs schemes list",
                reverse("reporting:costs_list"),
                icon="icons/banknotes.html",
                check=lambda request: request.user.is_authenticated
                and request.user.is_superuser,
            ),
        ],
    ),
)
