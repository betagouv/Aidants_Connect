from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from django_otp import match_token
from magicauth.forms import EmailForm as MagicAuthEmailForm

from aidants_connect_common.forms import AcPhoneNumberField, PatchedForm
from aidants_connect_common.utils.constants import AuthorizationDurations as ADKW
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    HabilitationRequest,
    Organisation,
)


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

    class Meta:
        model = Aidant
        fields = (
            "email",
            "last_name",
            "first_name",
            "profession",
            "phone",
            "organisation",
            "username",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation"].required = True

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        aidant_email = cleaned_data.get("email")
        if aidant_email in Aidant.objects.all().values_list("username", flat=True):
            self.add_error(
                "email", forms.ValidationError("This email is already taken")
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
            "phone",
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
        initial_id = self.instance.id

        if data_email != initial_email:
            if (
                Aidant.objects.filter(email=data_email).exists()
                or Aidant.objects.exclude(id=initial_id)
                .filter(username=data_email)
                .exists()
            ):
                self.add_error(
                    "email", forms.ValidationError("This email is already taken")
                )
            else:
                cleaned_data["username"] = data_email

        return cleaned_data


class LoginEmailForm(MagicAuthEmailForm):
    email = forms.EmailField()

    def clean_email(self):
        user_email = super().clean_email()
        if not Aidant.objects.filter(email=user_email, is_active=True).exists():
            raise ValidationError(
                "Votre compte existe mais il n’est pas encore actif. "
                "Si vous pensez que c’est une erreur, prenez contact avec votre "
                "responsable ou avec Aidants Connect."
            )
        return user_email


class MandatForm(PatchedForm):
    DEMARCHES = [(key, value) for key, value in settings.DEMARCHES.items()]
    demarche = forms.MultipleChoiceField(
        choices=DEMARCHES,
        required=True,
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": _("Vous devez sélectionner au moins une démarche.")
        },
    )

    DUREES = [
        (
            ADKW.SHORT,
            {"title": "Mandat court", "description": "(expire demain)"},
        ),
        (
            ADKW.MONTH,
            {
                "title": "Mandat d'un mois",
                "description": f"({ADKW.DAYS[ADKW.MONTH]} jours)",
            },
        ),
        (
            ADKW.LONG,
            {"title": "Mandat long", "description": "(12 mois)"},
        ),
        (
            ADKW.SEMESTER,
            {
                "title": "Mandat de 6 mois",
                "description": f"({ADKW.DAYS[ADKW.SEMESTER]} jours)",
            },
        ),
    ]
    duree = forms.ChoiceField(
        choices=DUREES,
        required=True,
        initial=3,
        error_messages={"required": _("Veuillez sélectionner la durée du mandat.")},
    )

    is_remote = forms.BooleanField(required=False)

    user_phone = AcPhoneNumberField(
        initial="",
        required=False,
    )

    def clean(self):
        cleaned = super().clean()

        # TODO: Reactivate when SMS consent is a thing
        # user_phone = cleaned.get("user_phone")
        # if user_phone is not None and cleaned["is_remote"] and len(user_phone) == 0:
        #     self.add_error(
        #         "user_phone",
        #         _(
        #             "Un numéro de téléphone est obligatoire "
        #             "si le mandat est signé à distance."
        #         ),
        #     )

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
    reason = forms.ChoiceField(
        choices=(
            ("perte", "Perte : La carte a été perdue."),
            ("casse", "Casse : La carte a été détériorée."),
            (
                "dysfonctionnement",
                "Dysfonctionnement : La carte ne fonctionne pas ou plus.",
            ),
            ("depart", "Départ : L’aidant concerné quitte la structure."),
            ("erreur", "Erreur : J’ai lié cette carte à ce compte par erreur."),
            ("autre", "Autre : Je complète ci-dessous."),
        )
    )
    other_reason = forms.CharField(required=False)


class SwitchMainAidantOrganisationForm(forms.Form):
    organisation = forms.ModelChoiceField(
        queryset=Organisation.objects.none(),
        widget=forms.RadioSelect,
    )
    next_url = forms.CharField(required=False)

    def __init__(self, aidant: Aidant, next_url="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aidant = aidant
        self.fields["organisation"].queryset = Organisation.objects.filter(
            aidants=self.aidant
        ).order_by("name")
        self.initial["organisation"] = self.aidant.organisation
        self.initial["next_url"] = next_url


class AddOrganisationResponsableForm(forms.Form):
    candidate = forms.ModelChoiceField(queryset=Aidant.objects.none())

    def __init__(self, organisation: Organisation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["candidate"].queryset = organisation.aidants.exclude(
            responsable_de=organisation
        ).order_by("last_name")


class ChangeAidantOrganisationsForm(forms.Form):
    organisations = forms.ModelMultipleChoiceField(
        queryset=Organisation.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": "Vous devez rattacher l’aidant à au moins une organisation."
        },
    )

    def __init__(self, responsable: Aidant, aidant: Aidant, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aidant = aidant
        self.responsable = responsable
        self.fields["organisations"].queryset = Organisation.objects.filter(
            responsables=self.responsable
        ).order_by("name")
        self.initial["organisations"] = self.aidant.organisations.all()


class HabilitationRequestCreationForm(forms.ModelForm):
    def __init__(self, responsable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.responsable = responsable
        self.fields["organisation"] = forms.ModelChoiceField(
            queryset=Organisation.objects.filter(
                responsables=self.responsable
            ).order_by("name"),
            empty_label="Choisir...",
        )

    class Meta:
        model = HabilitationRequest
        fields = (
            "email",
            "last_name",
            "first_name",
            "profession",
            "organisation",
        )
        error_messages = {
            NON_FIELD_ERRORS: {
                "unique_together": (
                    "Une demande d’habilitation est déjà en cours pour cette adresse "
                    "e-mail. Vous n’avez pas besoin d’en déposer une nouvelle."
                ),
            }
        }

    def clean_email(self):
        return self.cleaned_data.get("email").lower()


class DatapassForm(forms.Form):
    data_pass_id = forms.IntegerField()
    organization_name = forms.CharField()
    organization_siret = forms.IntegerField()
    organization_address = forms.CharField()
    organization_postal_code = forms.CharField()
    organization_type = forms.CharField()


class ValidateCGUForm(forms.Form):
    agree = forms.BooleanField(
        label="J’ai lu et j’accepte les conditions d’utilisation Aidants Connect.",
        required=True,
    )


class DatapassHabilitationForm(forms.ModelForm):
    data_pass_id = forms.IntegerField()

    class Meta:
        model = HabilitationRequest
        fields = [
            "first_name",
            "last_name",
            "email",
            "profession",
        ]

    def clean_data_pass_id(self):
        data_pass_id = self.cleaned_data["data_pass_id"]
        organisations = Organisation.objects.filter(data_pass_id=data_pass_id)
        if not organisations.exists():
            raise ValidationError("No organisation for data_pass_id")
        self.cleaned_data["organisation"] = organisations[0]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            return email.lower()
        return email

    def save(self, commit=True):
        self.instance.organisation = self.cleaned_data["organisation"]
        self.instance.origin = HabilitationRequest.ORIGIN_DATAPASS
        return super().save(commit)


class MassEmailHabilitatonForm(forms.Form):
    email_list = forms.Field(widget=forms.Textarea)

    def clean_email_list(self):
        email_list = self.cleaned_data.get("email_list")
        validate_email = EmailValidator(
            message="Veuillez saisir uniquement des adresses e-mail valides."
        )

        def is_email_valid(value):
            validate_email(value)
            return True

        return set(
            filter(
                is_email_valid,
                (filter(None, (email.strip() for email in email_list.splitlines()))),
            )
        )
