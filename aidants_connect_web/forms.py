from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import EmailField
from django.forms.utils import ErrorList
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django_otp import match_token
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberInternationalFallbackWidget

from aidants_connect_web.models import Aidant, CarteTOTP, Organisation


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
    demarche = forms.MultipleChoiceField(
        choices=DEMARCHES,
        required=True,
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": _("Vous devez sélectionner au moins une démarche.")
        },
    )

    # models.MandatDureeKeywords
    DUREES = [
        ("SHORT", {"title": "Mandat court", "description": "(expire demain)"}),
        ("LONG", {"title": "Mandat long", "description": "(12 mois)"}),
    ]
    duree = forms.ChoiceField(
        choices=DUREES,
        required=True,
        initial=3,
        error_messages={"required": _("Veuillez sélectionner la durée du mandat.")},
    )

    is_remote = forms.BooleanField(required=False)

    user_phone = PhoneNumberField(
        initial="",
        region=settings.PHONENUMBER_DEFAULT_REGION,
        widget=PhoneNumberInternationalFallbackWidget(
            region=settings.PHONENUMBER_DEFAULT_REGION
        ),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()

        user_phone = cleaned.get("user_phone", None)
        if user_phone is not None and cleaned["is_remote"] and len(user_phone) == 0:
            self.add_error(
                "user_phone",
                _(
                    "Un numéro de téléphone est obligatoire "
                    "si le mandat est signé à distance."
                ),
            )

        return cleaned


class OTPForm(forms.Form):
    otp_token = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r"^\d{6}$")],
        label=(
            "Entrez le code à 6 chiffres généré par votre téléphone "
            "ou votre carte Aidants Connect"
        ),
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, aidant, *args, **kwargs):
        super(OTPForm, self).__init__(*args, **kwargs)
        self.aidant = aidant

    def clean_otp_token(self):
        otp_token = self.cleaned_data["otp_token"]
        aidant = self.aidant
        good_token = match_token(aidant, otp_token)
        if good_token:
            return otp_token
        else:
            raise ValidationError("Ce code n'est pas valide.")


class RecapMandatForm(OTPForm, forms.Form):
    personal_data = forms.BooleanField(
        label="J’autorise mon aidant à utiliser mes données à caractère personnel."
    )


class CarteOTPSerialNumberForm(forms.Form):
    serial_number = forms.CharField()

    def clean_serial_number(self):
        serial_number = self.cleaned_data["serial_number"]
        try:
            carte = CarteTOTP.objects.get(serial_number=serial_number)
        except CarteTOTP.DoesNotExist:
            raise ValidationError(
                "Aucune carte n'a été trouvée avec ce numéro de série."
            )
        if carte.aidant:
            raise ValidationError("Cette carte est déjà associée à un aidant.")
        return serial_number


class CarteTOTPValidationForm(forms.Form):
    otp_token = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r"^\d{6}$")],
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )


class RemoveCardFromAidantForm(forms.Form):
    serial_number = forms.HiddenInput()


class DatapassForm(forms.Form):
    data_pass_id = forms.IntegerField()
    organization_name = forms.CharField()
    organization_siret = forms.IntegerField()
    organization_address = forms.CharField()


class ValidateCGUForm(forms.Form):
    agree = forms.BooleanField(
        label="J’ai lu et j’accepte les conditions d’utilisation Aidants Connect.",
        required=True,
    )


class PatchedErrorList(ErrorList):
    """An ErrorList that will just print itself as a <span> when it has only 1 item"""

    def as_ul(self):
        """Just return a <span> instead of a <ul> if there's only one error"""
        if self.data and len(self) == 1:
            return format_html('<span class="{}">{}</span>', self.error_class, self[0])

        return super().as_ul()
