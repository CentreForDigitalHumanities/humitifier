from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import GeneratedReport

@receiver(post_delete, sender=GeneratedReport)
def delete_file_on_report_delete(sender, instance, **kwargs):
    """
    Deletes the file from filesystem when the GeneratedReport object is deleted.
    """
    if instance.file:
        instance.file.delete(save=False)
