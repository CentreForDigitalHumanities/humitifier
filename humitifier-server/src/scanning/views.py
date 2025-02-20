from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelformset_factory
from django.forms.formsets import DELETION_FIELD_NAME
from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, UpdateView

from main.views import FilteredListView, SuperuserRequiredMixin, TableMixin
from scanning.filters import ScanSpecFilters
from scanning.forms import ArtefactSpecForm, ScanSpecCreateForm, ScanSpecForm
from scanning.models import ArtefactSpec, ScanSpec
from scanning.tables import ScanSpecTable


class ScanSpecView(
    LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, FilteredListView
):
    model = ScanSpec
    table_class = ScanSpecTable
    filterset_class = ScanSpecFilters
    paginate_by = 50
    template_name = "scanning/scanspec_list.html"
    ordering = "name"
    ordering_fields = {
        "name": "Name",
    }


class CreateScanSpecView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = ScanSpec
    form_class = ScanSpecCreateForm

    def get_success_url(self):
        return reverse("scanning:edit_scan_spec", args=[self.object.pk])


class EditScanSpecView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = ScanSpec
    form_class = ScanSpecForm
    success_url = reverse_lazy("scanning:scan_specs")

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid() and self._formset.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        for form in self._formset.forms:
            form.instance.scan_spec = self.get_object()
        self._formset.save()
        return response

    @cached_property
    def _formset(self):
        ArtefactSpecFormset = modelformset_factory(
            model=ArtefactSpec,
            form=ArtefactSpecForm,
            can_delete=True,
            can_delete_extra=False,
            extra=0,
            max_num=1000,
            help_texts={DELETION_FIELD_NAME: "Test"},
        )

        scan_spec = self.get_object()

        kwargs = {
            "queryset": scan_spec.artefacts.all(),
        }

        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES

        return ArtefactSpecFormset(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["formset"] = self._formset

        return context


class DeleteScanSpecView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = ScanSpec
    success_url = reverse_lazy("scanning:scan_specs")
