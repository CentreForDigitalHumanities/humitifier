from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO
from typing import TypedDict

from django.db.models import QuerySet
from openpyxl.styles import Font, NamedStyle, PatternFill
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel

from hosts.models import Host
from humitifier_common.artefacts import Hardware
from reporting.models import CostsScheme
from reporting.utils import CostsBreakdown, calculate_from_hardware_artefact
from reporting.utils.get_server_hardware import get_hardware_for_hosts


##
## Data models
##


class _Host(BaseModel):
    hostname: str
    hardware: Hardware
    cost_breakdown: CostsBreakdown
    scan_date: datetime


class CostExcelCustomer(BaseModel):
    name: str | None = None
    hosts: list[_Host]


##
## Data-based generator funcs
##


def create_current_cost_excel(
    costs_scheme: CostsScheme, filename: str, customers: list[str] | str | None = None
) -> BytesIO:
    customer_info = []

    if not customers:
        customers = (
            Host.objects.values_list("customer", flat=True).order_by().distinct()
        )

    for customer in customers:
        hosts = Host.objects.filter(customer=customer, archived=False)

        server_details = get_hardware_for_hosts(hosts)

        hosts = []
        for server in server_details:
            cost_breakdown = calculate_from_hardware_artefact(
                server.hardware,
                costs_scheme,
            )

            hosts.append(
                _Host(
                    hostname=server.hostname,
                    hardware=server.hardware,
                    cost_breakdown=cost_breakdown,
                    scan_date=server.scan_date,
                )
            )

        customer_info.append(
            CostExcelCustomer(
                name=customer,
                hosts=hosts,
            )
        )

    return generate_excel(filename, customer_info)


##
## Actual Excel creation func
##


def generate_excel(
    filename: str, customers: list[CostExcelCustomer] | CostExcelCustomer
) -> BytesIO:
    wb = Workbook()
    main_sheet = wb.active

    if not isinstance(customers, (list, tuple)):
        customers = [customers]

    header = NamedStyle(name="header")
    header.font = Font(name="Calibri", bold=True, color="000000")
    header.fill = PatternFill("solid", fgColor="DDDDDD")
    wb.add_named_style(header)

    for customer in customers:
        ws = wb.create_sheet(_get_customer_sheet_name(customer.name))
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

        total_server_costs = Decimal("0")
        total_support_costs = Decimal("0")

        for i, host in enumerate(customer.hosts):

            total_server_costs += host.cost_breakdown.total_hardware_costs
            total_support_costs += host.cost_breakdown.management

            # Excel doesn't know what timezones are
            date = host.scan_date.replace(tzinfo=None)

            ws.append(
                [
                    host.hostname,
                    date,
                    host.cost_breakdown.num_cpu,
                    host.cost_breakdown.memory_size,
                    host.cost_breakdown.total_storage_usage,
                    host.cost_breakdown.vm_costs,
                    host.cost_breakdown.total_storage_costs,
                    host.cost_breakdown.management,
                    host.cost_breakdown.total_costs,
                ]
            )

            ws[f"F{i+2}"].number_format = "€ #,##0.00"
            ws[f"G{i+2}"].number_format = "€ #,##0.00"
            ws[f"H{i+2}"].number_format = "€ #,##0.00"
            ws[f"I{i+2}"].number_format = "€ #,##0.00"

        _set_sheet_width(ws)

        max_index = len(customer.hosts) + 1

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
        sheet_name = _get_customer_sheet_name(customer.name)
        total_vm_costs = f"=SUM('{sheet_name}'!F2:F999) + SUM('{sheet_name}'!G2:G999)"
        total_support_costs = f"=ROUND(SUM('{sheet_name}'!H2:H999),2)"
        total_costs = f"=ROUND(SUM('{sheet_name}'!I2:I999),2)"
        main_sheet.append(
            [
                customer.name,
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


##
## Helpers
##


def _get_customer_sheet_name(customer_name: str | None) -> str:
    if customer_name is None:
        customer_name = "Unknown"
    postfix = "- Server List"
    max_length = 31 - len(postfix) - 1  # Account for space and "-"
    truncated_customer = (
        customer_name[:max_length] if len(customer_name) > max_length else customer_name
    )
    return f"{truncated_customer} {postfix}"


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
