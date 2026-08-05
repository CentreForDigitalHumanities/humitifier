from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from reporting.models import CostsScheme, GeneratedReport
from decimal import Decimal

User = get_user_model()

class ReportActionsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="password", email="admin@example.com")
        self.client.login(username="admin", password="password")
        
        self.scheme = CostsScheme.objects.create(
            name="Test Scheme",
            cpu=Decimal("10.00"),
            memory=Decimal("2.00"),
            storage=Decimal("50.00"),
            linux=Decimal("5.00"),
            windows=Decimal("15.00"),
            management=Decimal("100.00"),
        )
        
        self.report = GeneratedReport.objects.create(
            filename="test_report.xlsx",
            created_by=self.user,
            customers=["Customer A"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.report.costs_schemes.add(self.scheme)

    def test_delete_report(self):
        delete_url = reverse("reporting:report_delete", args=[self.report.pk])
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(GeneratedReport.objects.filter(pk=self.report.pk).exists())

    def test_rerun_report(self):
        rerun_url = reverse("reporting:report_rerun", args=[self.report.pk])
        response = self.client.post(rerun_url)
        self.assertEqual(response.status_code, 302)
        
        # Check if a new report was created
        new_reports = GeneratedReport.objects.exclude(pk=self.report.pk)
        self.assertEqual(new_reports.count(), 1)
        new_report = new_reports.first()
        
        self.assertEqual(new_report.filename, self.report.filename)
        self.assertEqual(new_report.customers, self.report.customers)
        self.assertEqual(list(new_report.costs_schemes.all()), list(self.report.costs_schemes.all()))
        self.assertEqual(new_report.start_date, self.report.start_date)
        self.assertEqual(new_report.end_date, self.report.end_date)
        self.assertEqual(new_report.status, GeneratedReport.Status.PENDING)

    def test_delete_report_get(self):
        delete_url = reverse("reporting:report_delete", args=[self.report.pk])
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure you want to delete the report")

    def test_rerun_report_get(self):
        rerun_url = reverse("reporting:report_rerun", args=[self.report.pk])
        response = self.client.get(rerun_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure you want to rerun the report")
