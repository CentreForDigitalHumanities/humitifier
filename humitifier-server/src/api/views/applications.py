from braces.views import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from api.filters import OAuth2ApplicationFilters
from api.forms import OAuth2ApplicationForm
from api.models import OAuth2Application
from api.tables import OAuth2ApplicationsTable
from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin


class OAuthApplicationsView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    TableMixin,
    FilteredListView
):
    model = OAuth2Application
    table_class = OAuth2ApplicationsTable
    filterset_class = OAuth2ApplicationFilters
    paginate_by = 50
    template_name = 'api/application_list.html'
    ordering_fields = {
        'name':       'Name',
        'access_profile':         'Access Profile',
    }

class CreateOAuthApplicationView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    CreateView
):
    model = OAuth2Application
    form_class = OAuth2ApplicationForm
    template_name = 'api/application_form.html'
    success_url = reverse_lazy('api:oauth_applications')

    def form_valid(self, form):
        # We only allow confidential clients with client credentials grant type
        form.instance.client_type = OAuth2Application.CLIENT_CONFIDENTIAL
        form.instance.grant_type = OAuth2Application.GRANT_CLIENT_CREDENTIALS
        return super().form_valid(form)


class EditOAuthApplicationView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    UpdateView
):
    model = OAuth2Application
    form_class = OAuth2ApplicationForm
    template_name = 'api/application_form.html'
    success_url = reverse_lazy('api:oauth_applications')


class DeleteOAuthApplicationView(
    LoginRequiredMixin,
    SuperuserRequiredMixin,
    DeleteView
):
    model = OAuth2Application
    template_name = 'api/application_confirm_delete.html'
    success_url = reverse_lazy('api:oauth_applications')