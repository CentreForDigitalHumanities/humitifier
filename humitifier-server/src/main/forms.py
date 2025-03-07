from django import forms
from django.forms.renderers import TemplatesSetting
from django.utils.safestring import mark_safe

from hosts.filters import _get_choices
from hosts.models import Host
from main.models import AccessProfile, User


class CustomFormRenderer(TemplatesSetting):
    form_template_name = "base/forms/form_template.html"
    field_template_name = "base/forms/field_template.html"


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "wild_wasteland_mode",
            "default_home",
            "is_superuser",
            "access_profiles",
        ]
        widgets = {
            "access_profiles": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and not self.instance.is_local_account:
            self.fields["username"].disabled = True
            self.fields["email"].disabled = True
            self.fields["first_name"].disabled = True
            self.fields["last_name"].disabled = True

    def clean_username(self):
        if self.instance and not self.instance.is_local_account:
            return self.instance.username
        return self.cleaned_data["username"]

    def clean_email(self):
        if self.instance and not self.instance.is_local_account:
            return self.instance.email
        return self.cleaned_data["email"]

    def clean_first_name(self):
        if self.instance and not self.instance.is_local_account:
            return self.instance.first_name
        return self.cleaned_data["first_name"]

    def clean_last_name(self):
        if self.instance and not self.instance.is_local_account:
            return self.instance.last_name
        return self.cleaned_data["last_name"]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "wild_wasteland_mode",
            "default_home",
        ]
        widgets = {
            "wild_wasteland_mode": forms.CheckboxInput,
        }


class CreateSolisUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "is_superuser",
            "access_profiles",
        ]
        widgets = {
            "access_profiles": forms.CheckboxSelectMultiple,
        }


class SetPasswordForm(forms.ModelForm):
    class Meta:
        model = User
        fields = []

    new_password = forms.CharField(
        widget=forms.PasswordInput,
        label="New Password",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["new_password"].widget.attrs["placeholder"] = "hunter2"
        self.fields["password_confirm"].widget.attrs["placeholder"] = "hunter2"

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        password_confirm = cleaned_data.get("password_confirm")

        if new_password != password_confirm:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        self.instance.set_password(self.cleaned_data["new_password"])
        return super().save(commit=commit)


class CustomersWidget(forms.CheckboxSelectMultiple):

    def format_value(self, value):
        if value is None:
            return []
        return value.split(",")

    def optgroups(self, name, value, attrs=None):
        # First, reset the choices with the current options from the DB
        # This cannot be done in __init__ because the choices change over time
        self.choices = _get_choices(Host, "customer", strip_quotes=False)

        # Then, add any values that are not in the choices (but are in the
        # value) to the options, as they might be customers that were removed
        # from the dataset at some point
        for val in value:
            if val not in dict(self.choices):
                label = val.strip('"')
                # Mark the label as gray to indicate it's not in the dataset
                label = mark_safe(f"<span class='text-gray-500'>{label}</span>")
                self.choices.append((val, label))

        self.choices = sorted(self.choices, key=lambda x: x[0])

        return super().optgroups(name, value, attrs)


class AccessProfileForm(forms.ModelForm):
    class Meta:
        model = AccessProfile
        fields = [
            "name",
            "description",
            "customers",
            "data_sources",
        ]
        widgets = {
            "customers": CustomersWidget,
            "data_sources": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make sure data_sources isn't actually required
        self.fields["data_sources"].required = False
        # Make sure customers isn't actually required
        self.fields["customers"].required = False

