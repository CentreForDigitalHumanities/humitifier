from django.test import TestCase

from main.models import User
from .models import Alert, AlertAcknowledgment
from hosts.models import Host


class TestAlertSignals(TestCase):

    def setUp(self):
        # Example setup for tests
        self.host = Host.objects.create(fqdn="test")

        self.alert_creator = "test!"

        self.user = User.objects.create_user(username="testuser")

    def test_on_alert_created_with_acknowledgment(self):
        """
        Test that on_alert_created attaches acknowledgment correctly.
        """
        # Create a persistent acknowledgment manually
        acknowledgment = AlertAcknowledgment.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            acknowledged_by=self.user,
        )

        # Create an alert that matches the acknowledgment
        alert = Alert.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            message="Test alert",
            severity="critical",
        )

        # Refresh acknowledgment instance and check that `_alert` was set
        acknowledgment.refresh_from_db()
        self.assertEqual(acknowledgment._alert, alert)

    def test_on_alert_created_without_acknowledgment(self):
        """
        Test that on_alert_created does nothing if no acknowledgment is found.
        """
        # Create an alert without any matching acknowledgment
        alert = Alert.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            message="Test alert",
            severity="critical",
        )

        # Ensure no acknowledgment exists for this alert
        self.assertFalse(AlertAcknowledgment.objects.filter(_alert=alert).exists())

    def test_on_alert_deletion_with_non_persistent_acknowledgment(self):
        """
        Test that on_alert_deletion deletes a non-persistent acknowledgment.
        """
        # Create an alert and attach a non-persistent acknowledgment
        alert = Alert.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            message="Test alert",
            severity="critical",
        )
        acknowledgment = AlertAcknowledgment.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            acknowledged_by=self.user,
            persistent=False,  # Non-persistent acknowledgment
            _alert=alert,
        )
        # Cache the ID, such that we know what it was before refetching
        acknowledgment_id = acknowledgment.id

        # Delete the alert, triggering the `pre_delete` signal
        alert.delete()

        # Assert that the acknowledgment was also deleted
        self.assertFalse(
            AlertAcknowledgment.objects.filter(id=acknowledgment_id).exists()
        )

    def test_on_alert_deletion_with_persistent_acknowledgment(self):
        """
        Test that on_alert_deletion does not delete a persistent acknowledgment.
        """
        # Create an alert and attach a persistent acknowledgment
        alert = Alert.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            message="Test alert",
            severity="critical",
        )
        acknowledgment = AlertAcknowledgment.objects.create(
            host=self.host,
            _creator=self.alert_creator,
            acknowledged_by=self.user,
            persistent=True,  # Persistent acknowledgment
            _alert=alert,
        )
        # Cache the ID, such that we know what it was before refetching
        acknowledgment_id = acknowledgment.id

        # Delete the alert, triggering the `pre_delete` signal
        alert.delete()

        # Assert that the acknowledgment still exists
        acknowledgment.refresh_from_db()
        self.assertTrue(
            AlertAcknowledgment.objects.filter(id=acknowledgment_id).exists()
        )
        self.assertIsNone(
            acknowledgment._alert
        )  # Ensure `_alert` is de-coupled but acknowledgment is not deleted
