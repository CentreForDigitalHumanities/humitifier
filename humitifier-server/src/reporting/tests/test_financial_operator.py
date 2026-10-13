import os
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from simple_menu import Menu

from main.filters import UserFilters
from main.forms import CreateSolisUserForm, UserForm
from reporting.models import CostsScheme, GeneratedReport

User = get_user_model()


class FinancialOperatorRoleTestCase(TestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user(
            username="regular_user",
            password="password",
            email="regular@example.com",
        )
        self.fin_op_user = User.objects.create_user(
            username="fin_op_user",
            password="password",
            email="fin_op@example.com",
            is_financial_operator=True,
        )
        self.super_user = User.objects.create_superuser(
            username="super_user",
            password="password",
            email="super@example.com",
        )
        self.scheme = CostsScheme.objects.create(
            name="Standard Scheme",
            cpu=Decimal("15.00"),
            memory=Decimal("3.00"),
            storage=Decimal("60.00"),
            linux=Decimal("10.00"),
            windows=Decimal("20.00"),
            management=Decimal("50.00"),
        )
        self.report = GeneratedReport.objects.create(
            filename="financial_report.xlsx",
            created_by=self.fin_op_user,
            customers=["Customer 1"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.report.costs_schemes.add(self.scheme)

    def test_user_model_role_and_property(self):
        self.assertFalse(self.regular_user.is_financial_operator)
        self.assertFalse(self.regular_user.can_access_reporting)

        self.assertTrue(self.fin_op_user.is_financial_operator)
        self.assertFalse(self.fin_op_user.is_superuser)
        self.assertTrue(self.fin_op_user.can_access_reporting)

        self.assertFalse(self.super_user.is_financial_operator)
        self.assertTrue(self.super_user.is_superuser)
        self.assertTrue(self.super_user.can_access_reporting)

    def test_regular_user_denied_access_to_reporting_features(self):
        self.client.login(username="regular_user", password="password")

        urls = [
            reverse("reporting:report_list"),
            reverse("reporting:server_cost_report"),
            reverse("reporting:costs_list"),
            reverse("reporting:costs_new"),
            reverse("reporting:costs_update", args=[self.scheme.pk]),
            reverse("reporting:costs_delete", args=[self.scheme.pk]),
            reverse("reporting:report_rerun", args=[self.report.pk]),
            reverse("reporting:report_delete", args=[self.report.pk]),
            reverse("reporting:report_download", args=[self.report.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.url)

    def test_financial_operator_granted_access_to_reporting_features(self):
        self.client.login(username="fin_op_user", password="password")

        urls_200 = [
            reverse("reporting:report_list"),
            reverse("reporting:server_cost_report"),
            reverse("reporting:costs_list"),
            reverse("reporting:costs_new"),
            reverse("reporting:costs_update", args=[self.scheme.pk]),
            reverse("reporting:costs_delete", args=[self.scheme.pk]),
            reverse("reporting:report_rerun", args=[self.report.pk]),
            reverse("reporting:report_delete", args=[self.report.pk]),
        ]

        for url in urls_200:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_financial_operator_download_report(self):
        self.report.status = GeneratedReport.Status.COMPLETED
        self.report.file.save("test_download.xlsx", ContentFile(b"test file content"))
        self.report.save()

        self.client.login(username="fin_op_user", password="password")
        download_url = reverse("reporting:report_download", args=[self.report.pk])
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)

        # Cleanup file
        if self.report.file and os.path.exists(self.report.file.path):
            os.remove(self.report.file.path)

    def test_superadmin_granted_access_to_reporting_features(self):
        self.client.login(username="super_user", password="password")

        urls_200 = [
            reverse("reporting:report_list"),
            reverse("reporting:server_cost_report"),
            reverse("reporting:costs_list"),
            reverse("reporting:costs_new"),
            reverse("reporting:costs_update", args=[self.scheme.pk]),
            reverse("reporting:costs_delete", args=[self.scheme.pk]),
        ]

        for url in urls_200:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_menu_visibility(self):
        factory = RequestFactory()

        # Regular user request
        request = factory.get("/")
        request.user = self.regular_user
        reporting_menu = Menu.items["main"]
        reporting_item = next(
            item for item in reporting_menu if item.title == "Reporting"
        )
        report_list_item = next(
            item for item in reporting_item.children if item.title == "Server cost report"
        )
        costs_list_item = next(
            item for item in reporting_item.children if item.title == "Costs schemes list"
        )

        self.assertFalse(report_list_item.check_func(request))
        self.assertFalse(costs_list_item.check_func(request))

        # Financial operator request
        request.user = self.fin_op_user
        self.assertTrue(report_list_item.check_func(request))
        self.assertTrue(costs_list_item.check_func(request))

        # Superuser request
        request.user = self.super_user
        self.assertTrue(report_list_item.check_func(request))
        self.assertTrue(costs_list_item.check_func(request))

    def test_user_forms_support_financial_operator(self):
        form_data = {
            "username": "new_local_user",
            "email": "new_local@example.com",
            "first_name": "New",
            "last_name": "Local",
            "default_home": "hosts",
            "is_superuser": False,
            "is_financial_operator": True,
        }
        form = UserForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.is_financial_operator)

        solis_form_data = {
            "username": "new_solis_user",
            "is_superuser": False,
            "is_financial_operator": True,
        }
        solis_form = CreateSolisUserForm(data=solis_form_data)
        self.assertTrue(solis_form.is_valid(), solis_form.errors)
        solis_user = solis_form.save()
        self.assertTrue(solis_user.is_financial_operator)

    def test_user_filters_support_financial_operator(self):
        qs = User.objects.all()
        filter_true = UserFilters(data={"is_financial_operator": True}, queryset=qs)
        self.assertEqual(filter_true.qs.count(), 1)
        self.assertEqual(filter_true.qs.first().username, "fin_op_user")

        filter_false = UserFilters(data={"is_financial_operator": False}, queryset=qs)
        self.assertEqual(filter_false.qs.count(), 2)
