from celery import shared_task
from django.core.files.base import ContentFile

from humitifier_server.celery.task_names import REPORTING_GENERATE_COST_REPORT


@shared_task(name=REPORTING_GENERATE_COST_REPORT)
def generate_cost_report(
    report_id, costs_scheme_ids, filename, start_date, end_date, customers
):
    from datetime import date as date_type

    from reporting.models import CostsScheme, GeneratedReport
    from reporting.utils.costs_excel_export import create_timeseries_cost_excel

    report = GeneratedReport.objects.get(pk=report_id)

    try:
        # Find all schemes selected to support multiple platforms
        all_schemes = CostsScheme.objects.filter(pk__in=costs_scheme_ids)
        schemes_by_platform = {s.platform: s for s in all_schemes}

        start = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)

        file_data = create_timeseries_cost_excel(
            schemes_by_platform, filename, start, end, customers or None
        )

        report.file.save(filename, ContentFile(file_data.getvalue()), save=False)
        report.status = GeneratedReport.Status.COMPLETED

        # Only save if the report still exists in the DB; handles race conditions
        if GeneratedReport.objects.filter(pk=report_id).exists():
            report.save()
    except Exception as e:
        report.status = GeneratedReport.Status.FAILED
        report.error_message = str(e)

        # Only save if the report still exists in the DB; handles race conditions
        if GeneratedReport.objects.filter(pk=report_id).exists():
            report.save()
        raise
