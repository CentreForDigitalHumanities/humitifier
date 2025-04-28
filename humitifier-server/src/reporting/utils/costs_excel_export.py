from decimal import Decimal
from io import BytesIO, StringIO

from django.db.models import QuerySet
from openpyxl.styles import Font, NamedStyle, PatternFill
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from hosts.models import Host
from reporting.models import CostsScheme
from reporting.utils import calculate_from_hardware_artefact
from reporting.utils.get_server_hardware import get_server_hardware


def _get_customer_sheet_name(customer: str) -> str:
    return f"{customer} - Server list"


def _set_sheet_width(ws: Worksheet):
    dims = {}
    for row in ws.rows:
        for cell in row:
            if cell.value:
                dims[cell.column_letter] = max(
                    (dims.get(cell.column_letter, 0), len(str(cell.value)))
                )
    for col, value in dims.items():
        ws.column_dimensions[col].width = value + 5


def create_cost_excel(
    costs_scheme: CostsScheme, filename: str, customers: list[str] | str | None = None
) -> BytesIO:
    wb = Workbook()
    main_sheet = wb.active

    if customers is None:
        customers = (
            Host.objects.values_list("customer", flat=True).order_by().distinct()
        )
    if not isinstance(customers, (list, tuple, QuerySet)):
        customers = [customers]

    header = NamedStyle(name="header")
    header.font = Font(name="Calibri", bold=True, color="000000")
    header.fill = PatternFill("solid", fgColor="DDDDDD")
    wb.add_named_style(header)

    for customer in customers:
        ws = wb.create_sheet(_get_customer_sheet_name(customer))
        ws.append(
            [
                "Server",
                "Reference date",
                "Num. CPU",
                "Memory",
                "Storage",
                "VM Costs",
                "Storage Costs",
                "Support Costs",
                "Total Costs",
            ]
        )

        for column in [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
        ]:
            cell = ws[f"{column}1"]
            cell.style = header

        hosts = Host.objects.filter(customer=customer, archived=False)

        server_details = get_server_hardware(hosts)

        total_server_costs = Decimal("0")
        total_support_costs = Decimal("0")

        for i, server in enumerate(server_details):
            cost_breakdown = calculate_from_hardware_artefact(
                server.hardware,
                costs_scheme,
            )

            total_server_costs += cost_breakdown.total_hardware_costs
            total_support_costs += cost_breakdown.management

            # Excel doesn't know what timezones are
            date = server.scan_date.replace(tzinfo=None)

            ws.append(
                [
                    server.hostname,
                    date,
                    cost_breakdown.num_cpu,
                    cost_breakdown.memory_size,
                    cost_breakdown.total_storage_usage,
                    cost_breakdown.vm_costs,
                    cost_breakdown.total_storage_costs,
                    cost_breakdown.management,
                    cost_breakdown.total_costs,
                ]
            )

            ws[f"F{i+2}"].number_format = "€ #,##0.00"
            ws[f"G{i+2}"].number_format = "€ #,##0.00"
            ws[f"H{i+2}"].number_format = "€ #,##0.00"
            ws[f"I{i+2}"].number_format = "€ #,##0.00"

        _set_sheet_width(ws)

        max_index = hosts.count() + 1

        filters = ws.auto_filter
        filters.ref = f"A1:I{max_index}"
        for column in [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
        ]:
            ws.auto_filter.add_sort_condition(f"{column}2:{column}{max_index}")

    main_sheet.title = "Overview"
    main_sheet.column_dimensions["A"].width = 30
    main_sheet.column_dimensions["B"].width = 20
    main_sheet.column_dimensions["C"].width = 20
    main_sheet.column_dimensions["D"].width = 20

    main_sheet.append(["Customer", "Server costs", "Support costs", "Total costs"])

    for column in ["A", "B", "C", "D"]:
        cell = main_sheet[f"{column}1"]
        cell.style = header

    for i, customer in enumerate(customers):
        sheet_name = _get_customer_sheet_name(customer)
        total_vm_costs = f"=SUM('{sheet_name}'!F2:F999) + SUM('{sheet_name}'!G2:G999)"
        total_support_costs = f"=ROUND(SUM('{sheet_name}'!H2:H999),2)"
        total_costs = f"=ROUND(SUM('{sheet_name}'!I2:I999),2)"
        main_sheet.append(
            [
                customer,
                total_vm_costs,
                total_support_costs,
                total_costs,
            ]
        )

        main_sheet[f"B{i + 2}"].number_format = "€ #,##0.00"
        main_sheet[f"C{i + 2}"].number_format = "€ #,##0.00"
        main_sheet[f"D{i + 2}"].number_format = "€ #,##0.00"

    buffer = BytesIO()
    buffer.name = filename
    wb.save(buffer)

    return buffer
