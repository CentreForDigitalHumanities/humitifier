from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models


class HomeOptions(models.TextChoices):
    DASHBOARD = 'dashboard', 'Dashboard'
    HOSTS = 'hosts', 'Hosts'


class User(AbstractUser):

    is_local_account = models.BooleanField(default=True)

    wild_wasteland_mode = models.BooleanField(default=False)

    default_home = models.CharField(
        max_length=20,
        choices=HomeOptions.choices,
        default=HomeOptions.HOSTS
    )

    access_profiles = models.ManyToManyField(
        'AccessProfile',
        blank=True,
        related_name='users',
    )

    @property
    def departments_for_filter(self):
        departments = set()

        for access_profile in self.access_profiles.all():
            departments.update(access_profile.departments_for_filter)

        return departments


class AccessProfile(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    departments = ArrayField(
        models.CharField(max_length=200),
    )

    @property
    def departments_for_filter(self):
        departments = []

        for department in self.departments:
            departments.append(department)

            # Explanation for the following: the department field on hosts
            # is generated from JSON data. For some reason, this adds
            # quotes around the department name.
            # The following code is some safeguarding to make sure that
            # the filter works as expected. (As 'self.departments' is human
            # input)

            # If we have a department with quotes, we need to add an option
            # without quotes as well, just to be sure.
            if department.endswith('"'):
                departments.append(department[1:-1])
            # And the other way around too
            else:
                departments.append(f'"{department}"')

        return departments

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<AccessProfile: {self.name}>"