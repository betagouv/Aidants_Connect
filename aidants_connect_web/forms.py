import re
from typing import Optional
from urllib.parse import unquote

from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.forms import EmailField, Media, RadioSelect, modelformset_factory
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from django_otp import match_token
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from dsfr.forms import DsfrBaseForm, DsfrDjangoTemplates
from magicauth import settings as magicauth_settings
from magicauth.forms import EmailForm as MagicAuthEmailForm
from magicauth.otp_forms import OTPForm
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from pydantic import field_validator

from aidants_connect_common.constants import AuthorizationDurations as ADKW
from aidants_connect_common.forms import (
    AcPhoneNumberField,
    AsHiddenMixin,
    BaseHabilitationRequestFormSet,
    BaseModelMultiForm,
    CleanEmailMixin,
    ConseillerNumerique,
    CustomBoundFieldForm,
    ErrorCodesManipulationMixin,
    PatchedForm,
)
from aidants_connect_common.widgets import DetailedRadioSelect, JSModulePath, NoopWidget
from aidants_connect_web.constants import (
    HabilitationRequestCourseType,
    RemoteConsentMethodChoices,
)
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    HabilitationRequest,
    Organisation,
    Usager,
    UsagerQuerySet,
)
from aidants_connect_web.models.other_models import CoReferentNonAidantRequest
from aidants_connect_web.utilities import generate_sha256_hash
from aidants_connect_web.widgets import MandatDemarcheSelect, MandatDureeRadioSelect


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
        cleaned_data = super().clean()
        aidant_email = cleaned_data.get("email")
        if Aidant.objects.filter(email__iexact=aidant_email).exists():
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
                Aidant.objects.filter(email__iexact=data_email).exists()
                or Aidant.objects.exclude(id=initial_id)
                .filter(username__iexact=data_email)
                .exists()
            ):
                self.add_error(
                    "email", forms.ValidationError("Erreur : cet e-mail existe déjà")
                )
            else:
                cleaned_data["username"] = data_email

        return cleaned_data


class LoginEmailForm(MagicAuthEmailForm, DsfrBaseForm):
    email = forms.EmailField(
        label="Adresse e-mail", help_text="Format attendu : prenom-nom@exemple.fr"
    )

    def clean_email(self):
        user_email = super().clean_email()
        if not Aidant.objects.filter(email__iexact=user_email, is_active=True).exists():
            raise ValidationError(
                "Erreur : votre compte a été désactivé. "
                "Si vous pensez que c’est une erreur, prenez contact avec votre "
                "référent ou avec Aidants Connect."
            )
        return user_email


class ManagerFirstLoginForm(DsfrBaseForm):
    email = forms.EmailField(
        label="Adresse e-mail", help_text="Format attendu : prenom-nom@exemple.fr"
    )

    mobile = AcPhoneNumberField(
        label="Numéro de téléphone mobile",
        label_suffix=" :",
        initial="",
        help_text="Format attendu : 10 chiffres",
    )

    def clean(self):
        cleaned_data = super().clean()
        if "email" not in cleaned_data:
            return cleaned_data
        if "mobile" not in cleaned_data:
            return cleaned_data

        user_email = cleaned_data["email"]
        user_mobile = cleaned_data["mobile"]
        user_email = user_email.lower()

        aidant = Aidant.objects.filter(email__iexact=user_email, is_active=True).first()
        if aidant and aidant.has_a_totp_device:
            raise ValidationError(
                "Erreur : vous avez déjà un moyen de configuration configuré. "
                "Vous devez utiliser le formulaire de connexion classique "
                "et non pas le formulaire de première connexion référent."
            )

        if aidant is None:
            raise ValidationError(
                "Erreur : votre compte a été désactivé. "
                "Si vous pensez que c’est une erreur, prenez contact avec "
                "Aidants Connect."
            )

        if not user_mobile == aidant.phone:
            raise ValidationError(
                "Erreur : votre compte n'existe pas ou nous ne trouvons pas "
                "la correspondance "
                "entre celui-ci et les informations que vous avez saisi."
                "Si vous pensez que c’est une erreur, prenez contact avec "
                "Aidants Connect."
            )

        return cleaned_data


class ManagerFirstLoginWithCodeForm(DsfrBaseForm):
    code_otp = forms.CharField(
        label="Code de première connexion", help_text="Format attendu : 6 chiffres"
    )


class DsfrOtpForm(OTPForm, DsfrBaseForm):
    OTP_NUM_DIGITS = magicauth_settings.OTP_NUM_DIGITS
    otp_token = forms.CharField(
        max_length=OTP_NUM_DIGITS,
        min_length=OTP_NUM_DIGITS,
        validators=[RegexValidator(r"^\d{6}$")],
        label=_(
            "Entrez le code à %(OTP_NUM_DIGITS)s chiffres généré par votre téléphone ou votre carte OTP"  # noqa
        )
        % {"OTP_NUM_DIGITS": OTP_NUM_DIGITS},
        help_text="Format attendu : 6 chiffres",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)


def get_choices_for_remote_method():
    from django.conf import settings

    remote_choices = RemoteConsentMethodChoices.choices
    if settings.FF_ACTIVATE_SMS_CONSENT:
        return remote_choices
    else:
        return [
            (key, value)
            for key, value in remote_choices
            if key != RemoteConsentMethodChoices.SMS.name
        ]


class MandatForm(PatchedForm):
    demarche = forms.MultipleChoiceField(
        label="Sélectionnez la ou les démarches",
        choices=[],
        required=True,
        widget=MandatDemarcheSelect,
        error_messages={
            "required": _("Vous devez sélectionner au moins une démarche.")
        },
    )

    DUREES = [
        (
            ADKW.SHORT,
            {"label": "Mandat court", "description": "expire demain"},
        ),
        (
            ADKW.MONTH,
            {
                "label": "Mandat d'un mois",
                "description": f"{ADKW.DAYS[ADKW.MONTH]} jours",
            },
        ),
        (
            ADKW.LONG,
            {"label": "Mandat long", "description": "12 mois"},
        ),
        (
            ADKW.SEMESTER,
            {
                "label": "Mandat de 6 mois",
                "description": f"{ADKW.DAYS[ADKW.SEMESTER]} jours",
            },
        ),
    ]
    duree = forms.ChoiceField(
        label="Choisissez la durée du mandat",
        choices=DUREES,
        required=True,
        initial=3,
        error_messages={"required": _("Veuillez sélectionner la durée du mandat.")},
        widget=MandatDureeRadioSelect,
    )

    is_remote = forms.BooleanField(
        label="Je souhaite signer le mandat à distance",
        label_suffix="",
        required=False,
    )

    remote_constent_method = forms.ChoiceField(
        label="Sélectionnez une méthode de consentement à distance",
        choices=get_choices_for_remote_method,
        required=False,
        error_messages={
            "required": _(
                "Erreur : veuillez sélectionner la méthode de consentement à distance."
            )
        },
        widget=DetailedRadioSelect,
    )

    user_phone = AcPhoneNumberField(
        label="Numéro de téléphone de la personne accompagnée",
        label_suffix=" :",
        initial="",
        required=False,
    )

    user_remote_contact_verified = forms.BooleanField(
        required=False,
        label=(
            "Je certifie avoir validé l’identité de l’usager répondant au numéro de "
            "téléphone qui recevra la demande de consentement par SMS."
        ),
        label_suffix="",
    )

    def __init__(self, organisation: Organisation, *args, **kwargs):
        self.organisation = organisation
        super().__init__(*args, **kwargs)
        self.fields["demarche"].choices = [
            (key, settings.DEMARCHES[key])
            for key in self.organisation.allowed_demarches
        ]

    def clean_remote_constent_method(self):
        if not self.cleaned_data["is_remote"]:
            return ""

        # the form errors only triggers if html novalidate is set in form
        if not self.cleaned_data.get("remote_constent_method"):
            self.add_error(
                "remote_constent_method",
                _(
                    "Vous devez choisir parmis l'une des "
                    "méthodes de consentement à distance."
                ),
            )
            return ""

        return self.cleaned_data["remote_constent_method"]

    def clean_user_phone(self):
        if (
            not self.cleaned_data["is_remote"]
            or self.cleaned_data.get("remote_constent_method")
            != RemoteConsentMethodChoices.SMS.name
        ):
            return ""

        if not self.cleaned_data.get("user_phone"):
            self.add_error(
                "user_phone",
                _(
                    "Un numéro de téléphone est obligatoire "
                    "si le consentement est demandé par SMS."
                ),
            )
            return ""

        return self.cleaned_data["user_phone"]

    def clean_user_remote_contact_verified(self):
        if (
            not self.cleaned_data["is_remote"]
            or self.cleaned_data.get("remote_constent_method")
            not in RemoteConsentMethodChoices.blocked_methods()
        ):
            return True

        if not self.cleaned_data.get("user_remote_contact_verified"):
            raise ValidationError(
                self.fields["user_remote_contact_verified"].error_messages["required"],
                code="required",
            )

        return True


class OTPForm(DsfrBaseForm):
    otp_token = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r"^\d{6}$")],
        label=("Code temporaire"),
        help_text=("Format attendu : 6 chiffres"),
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
            raise ValidationError("Erreur : ce code n'est pas valide.")


class RecapMandatForm(OTPForm):
    personal_data = forms.BooleanField()

    def __init__(self, usager: Usager, aidant: Aidant, *args, **kwargs):
        super().__init__(aidant, *args, **kwargs)
        self["personal_data"].label = mark_safe(
            f"Avoir communiqué à <strong>{usager.get_full_name()}</strong> les "
            "informations concernant l’objet de l’intervention, la raison pour "
            "laquelle ses informations sont collectées et leur utilité ; les droits "
            "sur ses données ET avoir conservé son consentement écrit "
            "(capture d'écran email, SMS…) pour conclure le mandat et utiliser ses "
            "données à caractère personnel."
        )


class CarteOTPSerialNumberForm(forms.Form):
    serial_number = forms.CharField(label="Entrez le numéro de série")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["serial_number"].widget.attrs.update(
            {"placeholder": "Ex : GADT000XXXX"}
        )

    def clean_serial_number(self):
        serial_number = self.cleaned_data["serial_number"]
        try:
            carte = CarteTOTP.objects.get(serial_number=serial_number)
        except CarteTOTP.DoesNotExist:
            raise ValidationError(
                "Erreur : aucune carte n'a été trouvée avec ce numéro de série."
            )
        if carte.aidant:
            raise ValidationError("Erreur : cette carte est déjà associée à un aidant.")
        return serial_number


class CarteTOTPValidationForm(forms.Form):
    otp_token = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r"^\d{6}$")],
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )


class RemoveCardFromAidantForm(DsfrBaseForm):
    reason = forms.ChoiceField(
        label="Pourquoi séparer cette carte du compte ?",
        label_suffix=" :",
        choices=(
            ("perte", "Perte : La carte a été perdue."),
            ("casse", "Casse : La carte a été détériorée."),
            (
                "dysfonctionnement",
                "Disfonctionnement : La carte ne fonctionne pas ou plus.",
            ),
            ("depart", "Départ : L’aidant concerné quitte la structure."),
            ("erreur", "Erreur : J’ai lié cette carte à ce compte par erreur."),
            ("autre", "Autre : Je complète ci-dessous."),
        ),
    )
    other_reason = forms.CharField(
        label="Autre raison", label_suffix=" :", required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get("reason").lower()
        other_reason = cleaned_data.get("other_reason")

        if reason != "autre":
            return cleaned_data

        if not other_reason:
            self.add_error(
                "other_reason",
                ValidationError(
                    "Erreur : vous devez remplir ce champ si la raison "
                    "indiquée est autre.",
                    code="required",
                ),
            )
        else:
            cleaned_data["reason"] = other_reason

        return cleaned_data


class SwitchMainAidantOrganisationForm(forms.Form):
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.none())
    next_url = forms.CharField(required=False)

    def __init__(self, aidant: Aidant, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation"].queryset = aidant.organisations.order_by("name")

    def clean_next_url(self):
        return unquote(self.cleaned_data.get("next_url", ""))


class AddOrganisationReferentForm(DsfrBaseForm):
    candidate = forms.ModelChoiceField(
        label="Nouveau référent", label_suffix=" :", queryset=Aidant.objects.none()
    )

    def __init__(self, organisation: Organisation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["candidate"].queryset = organisation.referents_eligible_aidants


class ChangeAidantOrganisationsForm(forms.Form):
    organisations = forms.ModelMultipleChoiceField(
        queryset=Organisation.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": "Erreur : vous devez rattacher l’aidant "
            "à au moins une organisation."
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


class HabilitationRequestCreationForm(
    ConseillerNumerique,
    CleanEmailMixin,
    forms.ModelForm,
    DsfrBaseForm,
    CustomBoundFieldForm,
    AsHiddenMixin,
):
    template_name = "aidants_connect_web/forms/habilitation-request-creation-form.html"  # noqa: E501
    organisation = forms.ModelChoiceField(
        queryset=Organisation.objects.none(),
        empty_label="Choisir…",
    )

    def __init__(self, referent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.referent = referent
        self.fields["organisation"].queryset = Organisation.objects.filter(
            responsables=self.referent
        ).order_by("name")

    @property
    def clean_fullname(self):
        first_name = (
            self.data.get(f"{self.prefix}-first_name", "").strip() if self.data else ""
        )
        last_name = (
            self.data.get(f"{self.prefix}-last_name", "").strip() if self.data else ""
        )

        if not first_name and not last_name and self.instance.pk:
            first_name = self.instance.first_name or ""
            last_name = self.instance.last_name or ""

        if first_name or last_name:
            return f"{first_name.capitalize()} {last_name.capitalize()}".strip()
        return ""

    def clean_email(self):
        email = super().clean_email()

        if Aidant.objects.filter(
            email__iexact=email,
            organisation__in=self.referent.responsable_de.all(),
        ).exists():
            raise ValidationError(
                "Erreur : il existe déjà un compte aidant pour cette adresse e-mail. "
                "Vous n’avez pas besoin de déposer une "
                "nouvelle demande pour cette adresse-ci."
            )

        if HabilitationRequest.objects.filter(
            email=email,
            organisation__in=self.referent.responsable_de.all(),
        ).exists():
            raise ValidationError(
                "Erreur : une demande d’habilitation est déjà "
                "en cours pour l’adresse e-mail. "
                "Vous n’avez pas besoin de déposer une "
                "nouvelle demande pour cette adresse-ci.",
            )

        return email

    def save(self, commit=True):
        self.instance.origin = HabilitationRequest.ORIGIN_RESPONSABLE
        return super().save(commit)

    class Meta:
        model = HabilitationRequest
        fields = (
            "email",
            "first_name",
            "last_name",
            "profession",
            "organisation",
        )
        labels = {
            "email": "Adresse e-mail",
        }
        help_texts = {
            "email": "Exemple : prenom-nom@exemple.fr",
        }

        error_messages = {
            NON_FIELD_ERRORS: {
                "unique_together": (
                    "Erreur : une demande d'habilitation est déjà en cours "
                    "pour cette adresse e-mail. "
                    "Vous n'avez pas besoin d'en déposer une nouvelle."
                ),
            }
        }


class HabilitationRequestCreationFormSet(BaseHabilitationRequestFormSet):
    @property
    def action_url(self):
        return reverse("api_espace_responsable_aidant_new")

    def get_presenter_kwargs(self, idx, form) -> dict:
        return {"form": form, "idx": idx}

    def total_form_count(self):
        """Force l'affichage d'au moins un formulaire vide pour l'espace responsable"""
        if self.is_bound:
            return super().total_form_count()
        else:
            # Pour l'espace responsable, on veut toujours au moins 1 formulaire
            return max(1, min(self.initial_form_count(), self.max_num))

    def validate_unique(self):
        """Validate that emails are unique within the formset"""
        referent = self.forms[0].referent
        organisation = referent.organisation

        existing_emails = set()

        existing_emails.update(
            Aidant.objects.filter(organisation=organisation).values_list(
                "email", flat=True
            )
        )

        # Emails des demandes d'habilitation en cours dans l'organisation
        existing_emails.update(
            HabilitationRequest.objects.filter(organisation=organisation).values_list(
                "email", flat=True
            )
        )

        # Convertir en lowercase pour comparaison
        existing_emails = {email.lower() for email in existing_emails}

        # Vérifier les doublons dans le formset + contre la base
        form_emails = {}
        for form in self.forms:
            email = form.cleaned_data.get("email")
            if not email:
                continue

            email_lower = email.lower()

            # Vérifier contre la base de données
            if email_lower in existing_emails:
                form.add_error(
                    "email",
                    ValidationError(
                        "Erreur : il existe déjà un compte aidant ou une demande "
                        "d'habilitation pour cette adresse e-mail "
                        "dans cette organisation."
                    ),
                )

            # Collecter pour vérifier les doublons internes
            form_emails.setdefault(email_lower, []).append(form)

        # Traiter les doublons internes
        for email, form_list in form_emails.items():
            if len(form_list) > 1:
                for form in form_list:
                    form.add_error(
                        "email",
                        ValidationError(
                            f"L'adresse e-mail '{email}' apparaît plusieurs fois. "
                            "Chaque aidant doit avoir son propre e-mail nominatif."
                        ),
                    )

    def clean(self):
        """Override clean to call validate_unique"""
        super().clean()
        if not self._errors:
            self.validate_unique()


class HabilitationRequestCreationFormationTypeForm(DsfrBaseForm, AsHiddenMixin):
    Type = HabilitationRequestCourseType

    type = forms.ChoiceField(
        label=(
            "Choisissez la modalité de formation pour le ou les aidants "
            "que vous souhaitez habiliter. "
            "La même modalité s'appliquera pour tous les aidants."
        ),
        label_suffix=None,
        choices=Type.choices,
        widget=RadioSelect,
    )

    email_formateur = forms.EmailField(
        label="Adresse e-mail de l'aidant formateur",
        help_text="Exemple : prenom-nom@exemple.fr",
        required=False,
    )

    @property
    def media(self):
        return super().media + Media(
            js=(JSModulePath("js/formation-type.mjs"),),
        )

    def clean_email_formateur(self):
        email_formateur = self.cleaned_data.get("email_formateur")
        type_formation = self.cleaned_data.get("type")

        if type_formation == str(self.Type.P2P) and not email_formateur:
            raise ValidationError(
                "L'email du formateur est obligatoire pour une formation entre pairs."
            )

        return email_formateur


class NewHabilitationRequestForm(BaseModelMultiForm):
    habilitation_requests = modelformset_factory(
        HabilitationRequestCreationForm.Meta.model,
        HabilitationRequestCreationForm,
        formset=HabilitationRequestCreationFormSet,
    )

    course_type = HabilitationRequestCreationFormationTypeForm

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("renderer", DsfrDjangoTemplates())  # Patched in Django 5)
        super().__init__(*args, **kwargs)

    def is_valid(self):
        if "partial-submit" in getattr(self, "data", {}):
            return self["habilitation_requests"].is_valid()
        return super().is_valid()

    def save(self, commit=True):
        super().save(commit=False)
        for form in self["habilitation_requests"].forms:
            form.instance.course_type = self["course_type"].cleaned_data["type"]
            form.instance.email_formateur = self["course_type"].cleaned_data.get(
                "email_formateur"
            )

        return super().save(commit)


class DatapassForm(forms.Form):
    data_pass_id = forms.IntegerField()
    organization_name = forms.CharField()
    organization_siret = forms.IntegerField()
    organization_address = forms.CharField()
    organization_postal_code = forms.CharField()
    organization_type = forms.CharField()


class ValidateCGUForm(DsfrBaseForm):
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


class MassEmailActionForm(forms.Form):
    email_list = forms.Field(widget=forms.Textarea)

    def clean_email_list(self):
        email_list = self.cleaned_data.get("email_list")
        validate_email = EmailValidator(
            message="Erreur : veuillez saisir uniquement des adresses e-mail valides."
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


class AuthorizeSelectUsagerForm(DsfrBaseForm, ErrorCodesManipulationMixin):
    chosen_usager = forms.IntegerField(
        required=True,
        error_messages={
            "required": (
                required_msg := (
                    "Erreur : aucun profil n'a été trouvé. "
                    "Veuillez taper le nom d'une personne et la barre de recherche et "
                    "sélectionner parmis les propositions dans la liste déroulante"
                )
            ),
            "invalid": required_msg,
        },
    )

    def __init__(self, usager_with_active_auth: UsagerQuerySet, *args, **kwargs):
        self.usager_with_active_auth = usager_with_active_auth
        super().__init__(*args, **kwargs)

    def clean_chosen_usager(self):
        chosen_usager = self.cleaned_data.get("chosen_usager")
        try:
            user = Usager.objects.get(pk=chosen_usager)
            if user not in self.usager_with_active_auth:
                raise ValidationError("", code="unauthorized_user")
            return user
        except (Usager.DoesNotExist, Usager.MultipleObjectsReturned):
            raise ValidationError(
                "Erreur : la personne sélectionnée ne semble pas exister",
                code="invalid",
            )


class OAuthParametersForm(DsfrBaseForm, ErrorCodesManipulationMixin):
    state = forms.CharField()
    nonce = forms.CharField()
    response_type = forms.CharField()
    client_id = forms.CharField()
    redirect_uri = forms.CharField()
    scope = forms.CharField()
    acr_values = forms.CharField()
    claims = forms.JSONField(required=False)

    def __init__(self, organisation: Organisation, *args, relaxed=False, **kwargs):
        self.relaxed = relaxed
        self.organisation = organisation
        super().__init__(*args, **kwargs)

    def clean_nonce(self):
        result = self.cleaned_data.get("nonce")
        if result and not result.isalnum():
            raise ValidationError("", "invalid")
        return result

    def clean_state(self):
        result = self.cleaned_data.get("state")
        if result and not result.isalnum():
            raise ValidationError("", "invalid")
        return result

    def clean_response_type(self):
        result = self.cleaned_data.get("response_type")
        if result != "code":
            raise ValidationError("", "invalid")
        return result

    def clean_client_id(self):
        result = self.cleaned_data.get("client_id")
        if result != settings.FC_AS_FI_ID:
            raise ValidationError("", "invalid")
        return result

    def clean_redirect_uri(self):
        result = unquote(self.cleaned_data.get("redirect_uri", ""))
        if result != settings.FC_AS_FI_CALLBACK_URL:
            raise ValidationError("", "invalid")
        return result

    def clean_scope(self):
        result = unquote(self.cleaned_data.get("scope", ""))
        splitted = set(re.split(r"\s+", result))
        required = {"address", "birth", "email", "openid", "phone", "profile"}

        if required - splitted:
            raise ValidationError("", "invalid")
        return result

    def clean_acr_values(self):
        result = self.cleaned_data.get("acr_values")
        if result != "eidas1":
            raise ValidationError("", "invalid")
        return result

    def clean_claims(self):
        result = self.cleaned_data.get("claims")
        if not result:
            return None

        class Claim(BaseModel):
            class IdToken(BaseModel):
                class RepScope(BaseModel):
                    essential: bool
                    values: Optional[set[str]] = set()

                    @field_validator("essential")
                    @classmethod
                    def check_true(cls, v):
                        assert v is True
                        return v

                    @field_validator("values")
                    @classmethod
                    def check_demarche(cls, v):
                        assert all(value in settings.DEMARCHES.keys() for value in v)
                        return v

                rep_scope: RepScope

            id_token: IdToken

        try:
            unauthorized_perimeters = Claim(**result).id_token.rep_scope.values - set(
                self.organisation.allowed_demarches
            )

            if unauthorized_perimeters:
                raise ValidationError(
                    f"Unauthorized perimeters: {unauthorized_perimeters}",
                    code="unauthorized_perimeter",
                )
        except (TypeError, PydanticValidationError):
            raise ValidationError(
                self.fields["claims"].error_messages["invalid"],
                code="invalid",
                params={"value": result},
            )

        return result

    def clean(self):
        cleaned_data = {k: v for k, v in super().clean().items() if v is not None}

        if self.relaxed:
            return cleaned_data

        additionnal_keys = set(self.data.keys()) - set(self.fields.keys())

        for additionnal_key in additionnal_keys:
            self.add_error(None, ValidationError(additionnal_key, "additionnal_key"))

        return cleaned_data


class OAuthParametersFormV2(OAuthParametersForm):
    prompt = forms.CharField()

    def clean_prompt(self):
        result = unquote(self.cleaned_data.get("prompt", ""))
        splitted = set(re.split(r"\s+", result))

        if {"login"} - splitted:
            raise ValidationError("", "invalid")
        return result

    def clean_scope(self):
        result = unquote(self.cleaned_data.get("scope", ""))
        splitted = set(re.split(r"\s+", result))

        if {"birth", "email", "openid", "profile"} - splitted:
            raise ValidationError("", "invalid")
        return result

    def clean_redirect_uri(self):
        result = unquote(self.cleaned_data.get("redirect_uri", ""))
        if result != settings.FC_AS_FI_CALLBACK_URL_V2:
            raise ValidationError("", "invalid")
        return result


class SelectDemarcheForm(PatchedForm):
    chosen_demarche = forms.CharField()
    redirect_uri = forms.CharField()

    def __init__(self, aidant: Aidant, user: Usager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aidant = aidant
        self.user = user

    def clean_chosen_demarche(self):
        result = self.cleaned_data["chosen_demarche"]
        if not self.aidant.get_valid_autorisation(result, self.user):
            raise ValidationError("", code="unauthorized_demarche")
        return result

    def clean_redirect_uri(self):
        result = unquote(self.cleaned_data.get("redirect_uri", ""))
        if result not in [
            settings.FC_AS_FI_CALLBACK_URL,
            settings.FC_AS_FI_CALLBACK_URL_V2,
        ]:
            raise ValidationError("", "invalid")
        return result


class TokenForm(PatchedForm):
    code = forms.CharField()
    grant_type = forms.CharField()
    redirect_uri = forms.CharField()
    client_id = forms.CharField()
    client_secret = forms.CharField()

    def __init__(self, *args, relaxed=False, **kwargs):
        self.relaxed = relaxed
        super().__init__(*args, **kwargs)

    def clean_grant_type(self):
        expected = "authorization_code"
        result = self.cleaned_data["grant_type"]
        if result != expected:
            raise ValidationError(
                f"'grant_type' must be '{expected}', was '{result}'", "invalid"
            )
        return result

    def clean_redirect_uri(self):
        expected = settings.FC_AS_FI_CALLBACK_URL
        result = self.cleaned_data["redirect_uri"]
        if result != expected:
            raise ValidationError(
                f"'redirect_uri' must be '{expected}', was '{result}'",
                "invalid",
            )
        return result

    def clean_client_id(self):
        expected = settings.FC_AS_FI_ID
        result = self.cleaned_data["client_id"]
        if result != expected:
            raise ValidationError(
                f"'client_id' must be '{expected}', was '{result}'",
                "invalid",
            )
        return result

    def clean_client_secret(self):
        result = self.cleaned_data["client_secret"]
        try:
            computed = generate_sha256_hash(result.encode())
            if computed != settings.HASH_FC_AS_FI_SECRET:
                raise AttributeError()
        except AttributeError:
            raise ValidationError(
                "'client_secret' value does not correspond to the one in settings",
                "invalid",
            )

        return result

    def clean(self):
        cleaned_data = super().clean()

        if self.relaxed:
            return cleaned_data

        additionnal_keys = set(self.data.keys()) - set(self.fields.keys())

        for additionnal_key in additionnal_keys:
            self.add_error(None, ValidationError(additionnal_key, "additionnal_key"))

        return cleaned_data


class TokenFormV2(TokenForm):
    def clean_redirect_uri(self):
        expected = settings.FC_AS_FI_CALLBACK_URL_V2
        result = self.cleaned_data["redirect_uri"]
        if result != expected:
            raise ValidationError(
                f"'redirect_uri' must be '{expected}', was '{result}'",
                "invalid",
            )
        return result


class AddAppOTPToAidantForm(PatchedForm):
    otp_token = forms.CharField(
        label=(
            "Entrez ici le code de vérification donné par "
            "votre application pour valider la création"
        ),
        label_suffix=" :",
        min_length=6,
        max_length=8,
    )

    def __init__(self, otp_device: TOTPDevice, *args, **kwargs):
        self.otp_device = otp_device
        super().__init__(*args, **kwargs)

    def clean_otp_token(self):
        try:
            token = int(self.cleaned_data["otp_token"])
        except Exception:
            raise ValidationError("Erreur : le code OTP doit être composé de chiffres")

        totp = TOTP(
            self.otp_device.bin_key,
            self.otp_device.step,
            self.otp_device.t0,
            self.otp_device.digits,
            self.otp_device.drift,
        )
        if not totp.verify(token):
            raise ValidationError("Erreur : la vérification du code OTP a échoué")

        return token


class CoReferentNonAidantRequestForm(forms.ModelForm, DsfrBaseForm):
    organisation = forms.Field(required=False, widget=NoopWidget)

    def __init__(self, organisation: Organisation, *args, **kwargs):
        self.organisation = organisation
        super().__init__(*args, **kwargs)

    def clean_organisation(self):
        return self.organisation

    class Meta:
        model = CoReferentNonAidantRequest
        fields = (
            "first_name",
            "last_name",
            "profession",
            "email",
            "organisation",
        )


class OrganisationRestrictDemarchesForm(PatchedForm):
    demarches = forms.MultipleChoiceField(
        choices=[(key, value) for key, value in settings.DEMARCHES.items()],
        required=True,
        widget=MandatDemarcheSelect,
        error_messages={
            "required": _("Vous devez sélectionner au moins une démarche.")
        },
    )


class ConnexionChoiceForm(DsfrBaseForm):
    email = forms.CharField(
        label="E-mail professionnel",
        required=True,
        help_text="⚠️ Il s'agit de l'e-mail renseigné lors de la demande d'habilitation (e-mail nominatif de type prenom-nom@structure.fr)",  # noqa
    )
    connexion_mode = forms.ChoiceField(
        label="Moyen de connexion choisi",
        required=True,
        choices=[
            (HabilitationRequest.CONNEXION_MODE_PHONE, "Application Mobile"),
            (HabilitationRequest.CONNEXION_MODE_CARD, "Carte Physique"),
        ],
    )


class AskingMobileForm(DsfrBaseForm):
    user_email = forms.CharField(
        label="E-mail professionnel",
        required=True,
        help_text="⚠️ Il s'agit de l'e-mail renseigné lors de la demande d'habilitation (e-mail nominatif de type prenom-nom@structure.fr)",  # noqa
    )

    user_mobile = forms.CharField(
        label="Téléphone mobile", required=True, min_length=10, max_length=20
    )
