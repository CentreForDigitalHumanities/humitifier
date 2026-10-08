from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from hosts.models import OperatingSystem

User = get_user_model()


class OperatingSystemDeleteViewTestCase(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", password="password", email="admin@example.com"
        )
        self.regular_user = User.objects.create_user(
            username="user", password="password", email="user@example.com"
        )
        self.os = OperatingSystem.objects.create(name="Debian 12", outdated=False)

    def test_superuser_can_get_confirm_delete_page(self):
        self.client.login(username="admin", password="password")
        url = reverse("hosts:delete_operating_system", args=[self.os.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hosts/operatingsystem_confirm_delete.html")
        self.assertContains(response, "Debian 12")

    def test_superuser_can_delete_operating_system(self):
        self.client.login(username="admin", password="password")
        url = reverse("hosts:delete_operating_system", args=[self.os.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("hosts:operating_systems"))
        self.assertFalse(OperatingSystem.objects.filter(pk=self.os.pk).exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Operating system deleted" in str(m) for m in messages))

    def test_regular_user_cannot_delete_operating_system(self):
        self.client.login(username="user", password="password")
        url = reverse("hosts:delete_operating_system", args=[self.os.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OperatingSystem.objects.filter(pk=self.os.pk).exists())

    def test_unauthenticated_user_redirected(self):
        url = reverse("hosts:delete_operating_system", args=[self.os.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OperatingSystem.objects.filter(pk=self.os.pk).exists())
