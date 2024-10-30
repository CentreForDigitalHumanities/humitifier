from django.forms.renderers import TemplatesSetting


class CustomFormRenderer(TemplatesSetting):
    form_template_name = 'base/forms/form_template.html'
    field_template_name = "base/forms/field_template.html"
