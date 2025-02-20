from django.urls import reverse
from simple_menu import Menu, MenuItem


Menu.add_item(
    "main",
    MenuItem(
        "Scan specifications",
        reverse("scanning:scan_specs"),
        weight=10,
        icon="icons/terminal.html",
        check=lambda request: request.user.is_superuser,
    ),
)
