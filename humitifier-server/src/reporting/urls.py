from django.urls import path

from .views import (
    CostCalculatorView,
    CostsOverviewView,
    CostsSchemeCreateView,
    CostsSchemeListView,
    CostsSchemeUpdateView,
)

app_name = "reporting"

urlpatterns = [
    path("costs/", CostsSchemeListView.as_view(), name="costs_list"),
    path("costs/new/", CostsSchemeCreateView.as_view(), name="costs_new"),
    path("costs/<int:pk>/", CostsSchemeUpdateView.as_view(), name="costs_update"),
    path("cost_calculator/", CostCalculatorView.as_view(), name="cost_calculator"),
    path("server_costs/", CostsOverviewView.as_view(), name="server_cost_overview"),
]
