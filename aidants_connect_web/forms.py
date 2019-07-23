from django import forms
from django.forms import EmailField
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth import password_validation
from aidants_connect_web.models import User
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class MandatForm(forms.Form):
    perimeter = forms.MultipleChoiceField(
        choices=settings.DEMARCHES, widget=forms.CheckboxSelectMultiple
    )

    duration = forms.CharField(required=True, initial=3)


class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given email and
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
    last_name = forms.CharField(label="Nom de famille")

    profession = forms.CharField(label="Profession")
    organisme = forms.CharField(label="Organisme")
    ville = forms.CharField(label="ville")

    class Meta:
        model = User
        fields = "email", "last_name", "first_name", "profession", "organisme", "ville"

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
        user = super().save(commit=False)
        user.username = user.email
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):

    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this "
            "user’s password, but you can change the password using "
            '<a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = "__all__"
        field_classes = {"email": EmailField}

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial.get("password")
