from datetime import timedelta

from django.db import models
from django.utils import timezone

from hosts.models import Host, Scan


def historical_clean():
    """Cleans up historical scan data, keeping only one record per day per host for the past week and one record per month

    :return:
    """
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)

    for host in Host.objects.all():

        # Step 1: Reduce records older than one day but within the past week, keeping one per day per host
        for day_delta in range(7):  # 7 days between one_week_ago and one_day_ago
            day = one_week_ago + timedelta(days=day_delta)
            daily_records = Scan.objects.filter(created_at__date=day, host=host)

            earliest_record = daily_records.order_by("created_at").first()
            if earliest_record:
                to_remove = daily_records.exclude(pk=earliest_record.pk)
                to_remove.delete()

        # Step 2: Reduce records older than one week, keeping one per month per host
        records_older_than_week = Scan.objects.filter(
            created_at__lt=one_week_ago, host=host
        )
        months_and_hosts = (
            records_older_than_week.annotate(
                month=models.F("created_at__month"),
                year=models.F("created_at__year"),
            )
            .filter(host=host)
            .values("month", "year", "host_id")
            .distinct()
        )

        for record_group in months_and_hosts:
            earliest_record = (
                records_older_than_week.filter(
                    created_at__month=record_group["month"],
                    created_at__year=record_group["year"],
                    host_id=record_group["host_id"],
                )
                .order_by("created_at")
                .first()
            )

            if earliest_record:
                to_remove = records_older_than_week.filter(
                    created_at__month=record_group["month"],
                    created_at__year=record_group["year"],
                    host_id=record_group["host_id"],
                ).exclude(pk=earliest_record.pk)
                to_remove.delete()
