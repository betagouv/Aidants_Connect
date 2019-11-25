from django import forms
from django.forms import EmailField
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth import password_validation
from aidants_connect_web.models import Aidant, Organisation
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AidantCreationForm(forms.ModelForm):
    """
    A form that creates an aidant, with no privileges, from the given email and
    password.
    """

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    first_name = forms.CharField(label="Prénom")
    email = forms.EmailField(label="Email", widget=forms.EmailInput())
    username = forms.CharField(required=False)
    last_name = forms.CharField(label="Nom de famille")

    profession = forms.CharField(label="Profession")
    organisation = forms.ModelChoiceField(
        queryset=Organisation.objects.all(), empty_label="Organisation"
    )

    class Meta:
        model = Aidant
        fields = (
            "email",
            "last_name",
            "first_name",
            "profession",
            "organisation",
            "username",
        )

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        aidant_email = cleaned_data.get("email")
        if aidant_email in Aidant.objects.all().values_list("username", flat=True):
            self.add_error(
                "email", forms.ValidationError("This email is already " "taken")
            )
        else:
            cleaned_data["username"] = aidant_email

        return cleaned_data

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        aidant = super().save(commit=False)
        aidant.set_password(self.cleaned_data["password"])
        if commit:
            aidant.save()
        return aidant


class AidantChangeForm(forms.ModelForm):

    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this "
            "aidant’s password, but you can change the password using "
            '<a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = Aidant
        fields = (
            "email",
            "last_name",
            "first_name",
            "profession",
            "organisation",
            "username",
        )
        field_classes = {"email": EmailField}

    def clean_password(self):
        # Regardless of what the aidant provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial.get("password")

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        data_email = cleaned_data.get("email")
        initial_email = self.instance.email

        if data_email != initial_email:
            claimed_emails = Aidant.objects.all().values_list("username", flat=True)
            if data_email in claimed_emails:
                self.add_error(
                    "email", forms.ValidationError("This email is already taken")
                )
            else:
                cleaned_data["username"] = data_email

        return cleaned_data


class MandatForm(forms.Form):

    DEMARCHES = [(key, value) for key, value in settings.DEMARCHES.items()]

    perimeter = forms.MultipleChoiceField(
        choices=DEMARCHES, widget=forms.CheckboxSelectMultiple
    )
    DUREES = [
        ("short", {"title": "Mandat court", "description": "(1 jour)"}),
        ("long", {"title": "Mandat long", "description": "(12 mois)"}),
    ]
    duree = forms.ChoiceField(choices=DUREES, required=True, initial=3)
