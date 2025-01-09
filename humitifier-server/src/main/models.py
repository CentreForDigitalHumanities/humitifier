from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models


class HomeOptions(models.TextChoices):
    DASHBOARD = "dashboard", "Dashboard"
    HOSTS = "hosts", "Hosts"


class User(AbstractUser):

    is_local_account = models.BooleanField(default=True)

    wild_wasteland_mode = models.BooleanField(
        default=False,
        help_text="Enables easter eggs, non-default as it's less professional.",
    )

    default_home = models.CharField(
        max_length=20,
        choices=HomeOptions.choices,
        default=HomeOptions.HOSTS,
        help_text="The default page to redirect to after login.",
    )

    access_profiles = models.ManyToManyField(
        "AccessProfile",
        blank=True,
        related_name="users",
    )

    @property
    def can_view_datasources(self):
        return (
            self.is_superuser
            or self.access_profiles.exclude(data_sources__count=0).exists()
        )

    @property
    def customers_for_filter(self):
        customers = set()

        for access_profile in self.access_profiles.all():
            customers.update(access_profile.customers_for_filter)

        return customers


class AccessProfile(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    customers = ArrayField(
        models.CharField(max_length=200),
    )

    data_sources = models.ManyToManyField(
        "hosts.DataSource",
        verbose_name="Manage data sources",
        help_text="Determines which data sources this access profile gives manage access to.",
    )

    def get_customers_display(self):
        stripped = [customer.strip('"') for customer in self.customers]
        return ", ".join(stripped)

    @property
    def customers_for_filter(self):
        customers = []

        for department in self.customers:
            customers.append(department)

            # If we have a customer with quotes, we need to add an option
            # without quotes as well, just to be sure.
            # As of 4.0 this should no longer be a problem, but well, better safe than sorry
            if department.endswith('"'):
                customers.append(department[1:-1])
            # And the other way around too
            else:
                customers.append(f'"{department}"')

        return customers

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<AccessProfile: {self.name}>"
