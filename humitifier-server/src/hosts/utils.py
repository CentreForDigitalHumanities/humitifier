from datetime import timedelta

from django.db.models import Min
from django.utils import timezone

from hosts.models import Scan


def historical_clean():
    """Cleans up historical scan data, keeping only one record per day per host for the past week and one record per month

    :return:
    """
    now = timezone.now()
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)

    # Step 1: Reduce records older than one day but within the past week, keeping one per day per host
    daily_records = (
        Scan.objects.filter(created_at__lt=one_day_ago, created_at__gte=one_week_ago)
        .values("host", "created_at__date")  # Group by host and day
        .annotate(earliest_record=Min("created_at"))
        .distinct()
    )

    # Delete all records in the past week except the earliest record per day per host
    for daily_record in daily_records:
        Scan.objects.filter(
            created_at__lt=one_day_ago,
            created_at__gte=one_week_ago,
            host=daily_record["host"],
            created_at__date=daily_record["created_at__date"],
        ).exclude(created_at=daily_record["earliest_record"]).delete()

    # Step 2: Reduce records older than one week, keeping one per month per host
    monthly_records = (
        Scan.objects.filter(created_at__lt=one_week_ago)
        .extra({"month": "date_trunc('month', created_at)"})
        .values("host", "month")  # Group by host and month
        .annotate(earliest_record=Min("created_at"))
    )

    # Delete all records older than a week except the earliest record per month per host
    for monthly_record in monthly_records:
        Scan.objects.filter(
            created_at__lt=one_week_ago,
            host=monthly_record["host"],
            created_at__month=monthly_record["month"].month,
            created_at__year=monthly_record["month"].year,
        ).exclude(created_at=monthly_record["earliest_record"]).delete()
