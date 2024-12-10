from django.urls import reverse
from simple_menu import Menu, MenuItem


Menu.add_item(
    "main",
    MenuItem(
        "API documentation",
        reverse("api:redoc"),
        weight=22,
        icon="icons/document.html",
        separator=True,
        target="_blank",
    ),
)

Menu.add_item(
    "main",
    MenuItem(
        "OAuth2 Applications",
        reverse("api:oauth_applications"),
        weight=23,
        check=lambda request: request.user.is_superuser,
        icon="icons/api.html",
    ),
)
