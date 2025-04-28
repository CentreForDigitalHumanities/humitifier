from django.urls import path

from .views import (
    CostCalculatorView,
    CostsOverviewView,
    CostsReportView,
    CostsSchemeCreateView,
    CostsSchemeDeleteView,
    CostsSchemeListView,
    CostsSchemeUpdateView,
)

app_name = "reporting"

urlpatterns = [
    path("costs/", CostsSchemeListView.as_view(), name="costs_list"),
    path("costs/new/", CostsSchemeCreateView.as_view(), name="costs_new"),
    path("costs/<int:pk>/", CostsSchemeUpdateView.as_view(), name="costs_update"),
    path(
        "costs/<int:pk>/delete/", CostsSchemeDeleteView.as_view(), name="costs_delete"
    ),
    path("cost_calculator/", CostCalculatorView.as_view(), name="cost_calculator"),
    path("server_costs/", CostsOverviewView.as_view(), name="server_cost_overview"),
    path("server_costs/report/", CostsReportView.as_view(), name="server_cost_report"),
]
