from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Alert, AlertAcknowledgment


@receiver(post_save, sender=Alert)
def on_alert_created(sender, instance: Alert, created: bool, **kwargs):
    """
    Signal triggered when an Alert is created.
    :param sender: The model class (Alert)
    :param instance: The actual instance of the Alert being created
    :param created: Boolean, True if record was created, False if updated
    """
    if created:
        # If there is a persistent acknowledgment, we should auto-attach our new alert
        # This method already does a non-fk lookup if no fk ref is there
        ack = instance.get_acknowledgment()
        # If we indeed got a non-fk coupled instance, couple it
        if ack and not ack._alert:
            ack._alert = instance
            ack.save()


@receiver(pre_delete, sender=Alert)
def on_alert_deletion(sender, instance: Alert, **kwargs):
    """
    Signal triggered when an Alert is about to be deleted.
    :param sender: The model class (Alert)
    :param instance: The actual instance of the Alert being deleted
    """
    # If we are deleting an acknowledged alert
    if hasattr(instance, "acknowledgement") and instance.acknowledgement:
        ack = instance.acknowledgement
        # And it's not a persistent acknowledgment
        if not ack.persistent:
            # Delete the acknowledgment
            ack.delete()


@receiver(post_save, sender=AlertAcknowledgment)
def on_alert_acknowledgment_created(
    sender, instance: AlertAcknowledgment, created: bool, **kwargs
):
    """
    Signal triggered when an Alert is created.
    :param sender: The model class (Alert)
    :param instance: The actual instance of the Alert being created
    :param created: Boolean, True if record was created, False if updated
    """
    if created and not instance._alert:
        # If there is a persistent acknowledgment, we should auto-attach our new alert
        # This method already does a non-fk lookup if no fk ref is there
        alert = instance.get_alert()
        # If we indeed got a non-fk coupled instance, couple it
        if alert and not alert.acknowledgement:
            instance._alert = alert
            instance.save()
