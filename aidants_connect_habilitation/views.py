from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.forms import Form
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import yesno
from django.urls import reverse
from django.views.generic import FormView, RedirectView, TemplateView, View
from django.views.generic.base import ContextMixin

from aidants_connect_common.constants import (
    MessageStakeholders,
    RequestOriginConstants,
    RequestStatusConstants,
)
from aidants_connect_common.forms import PatchedModelForm
from aidants_connect_common.presenters import GenericHabilitationRequestPresenter
from aidants_connect_common.utils import issuer_exists_send_reminder_email
from aidants_connect_common.views import (
    FormationRegistrationView as CommonFormationRegistrationView,
)
from aidants_connect_habilitation.constants import HabilitationFormStep
from aidants_connect_habilitation.forms import (
    AidantRequestFormSet,
    IssuerForm,
    OrganisationRequestForm,
    PersonnelForm,
    RequestMessageForm,
    ValidationForm,
)
from aidants_connect_habilitation.models import (
    AidantRequest,
    Issuer,
    IssuerEmailConfirmation,
    Manager,
    OrganisationRequest,
    RequestMessage,
)

__all__ = [
    "NewHabilitationView",
    "NewIssuerFormView",
    "IssuerEmailConfirmationWaitingView",
    "IssuerEmailConfirmationView",
    "IssuerPageView",
    "ModifyIssuerFormView",
    "NewOrganisationRequestFormView",
    "ModifyOrganisationRequestFormView",
    "PersonnelRequestFormView",
    "ValidationRequestFormView",
    "ReadonlyRequestView",
    "AddAidantsRequestView",
    "AidantFormationRegistrationView",
    "HabilitationRequestCancelationView",
    "ManagerFormationRegistrationView",
]

from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation

"""Mixins"""


class HabilitationStepMixin(ContextMixin):
    @property
    def step(self) -> HabilitationFormStep:
        raise NotImplementedError()

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "step": self.step,
        }


class CheckIssuerMixin(ContextMixin, View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            uuid = UUID(kwargs.get("issuer_id"))
        except ValueError:
            raise Http404()
        self.issuer = get_object_or_404(Issuer, issuer_id=uuid)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "issuer": self.issuer,
        }


class VerifiedEmailIssuerView(CheckIssuerMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not self.issuer.email_verified:
            return redirect(
                "habilitation_issuer_email_confirmation_waiting",
                issuer_id=self.issuer.issuer_id,
            )

        return super().dispatch(request, *args, **kwargs)


class LateStageRequestView(VerifiedEmailIssuerView, View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            uuid = UUID(kwargs.get("uuid"))
        except ValueError:
            raise Http404()
        self.organisation = get_object_or_404(
            OrganisationRequest, uuid=uuid, issuer=self.issuer
        )


class OnlyNewRequestsView(HabilitationStepMixin, LateStageRequestView):
    @property
    def step(self) -> HabilitationFormStep:
        raise NotImplementedError()

    def dispatch(self, request, *args, **kwargs):
        if not self.issuer.email_verified:
            # Duplicate logic of VerifiedEmailIssuerView
            # because we want to check issuer email first.
            return redirect(
                "habilitation_issuer_email_confirmation_waiting",
                issuer_id=self.issuer.issuer_id,
            )

        if self.organisation.status not in RequestStatusConstants.validatable:
            return redirect(
                "habilitation_organisation_view",
                issuer_id=self.issuer.issuer_id,
                uuid=self.organisation.uuid,
            )

        return super().dispatch(request, *args, **kwargs)


class AdressAutocompleteJSMixin:
    def define_html_attributes(self, form: PatchedModelForm):
        form.widget_attrs(
            "address",
            {
                "data-address-autocomplete-target": "autcompleteInput",
                "data-action": "focus->address-autocomplete#onAutocompleteFocus",
            },
        )
        form.widget_attrs(
            "zipcode", {"data-address-autocomplete-target": "zipcodeInput"}
        )

        form.widget_attrs("city", {"data-address-autocomplete-target": "cityInput"})
        form.widget_attrs(
            "city_insee_code",
            {"data-address-autocomplete-target": "cityInseeCodeInput"},
        )
        form.widget_attrs(
            "department_insee_code",
            {"data-address-autocomplete-target": "dptInseeCodeInput"},
        )


"""Real views"""


class ProfileCardAidantRequestPresenter(GenericHabilitationRequestPresenter):

    def __init__(self, req: AidantRequest):
        self.req = req

    @property
    def pk(self):
        return self.req.pk

    @property
    def edit_endpoint(self):
        return reverse(
            "api_habilitation_aidant_edit",
            kwargs={
                "issuer_id": self.req.organisation.issuer.issuer_id,
                "uuid": self.req.organisation.uuid,
                "aidant_id": self.req.pk,
            },
        )

    @property
    def full_name(self) -> str:
        return self.req.get_full_name()

    @property
    def email(self) -> str:
        return self.req.email

    @property
    def details_fields(self) -> list[dict[str, Any]]:
        return [
            # email profession conseiller_numerique organisation
            {"label": "Email", "value": self.req.email},
            {"label": "Profession", "value": self.req.profession},
            {
                "label": "Conseiller numérique",
                "value": yesno(self.req.conseiller_numerique, "Oui,Non"),
            },
            {"label": "Organisation", "value": self.req.organisation},
        ]


class NewHabilitationView(RedirectView):
    permanent = True
    pattern_name = "habilitation_new_issuer"


class NewIssuerFormView(HabilitationStepMixin, FormView):
    template_name = "issuer_form.html"
    form_class = IssuerForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def form_invalid(self, form: IssuerForm):
        # Gets the error code of all the errors for email, if any
        # See https://docs.djangoproject.com/en/dev/ref/forms/fields/#django.forms.Field.error_messages  # noqa
        email_errors = form.errors.get("email")
        if email_errors:
            error_codes = [error.code for error in form.errors.get("email").as_data()]
            if "unique" in error_codes:
                self.send_issuer_profile_reminder_mail(form.data["email"])
                return render(self.request, "issuer_already_exists_warning.html")
        return super().form_invalid(form)

    def form_valid(self, form: IssuerForm):
        self.saved_model: Issuer = form.save()
        if not self.saved_model.email_verified:
            IssuerEmailConfirmation.for_issuer(self.saved_model).send(self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_issuer_email_confirmation_waiting",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )

    def send_issuer_profile_reminder_mail(self, email: str):
        issuer: Issuer = Issuer.objects.get(email__iexact=email)

        issuer_exists_send_reminder_email(self.request, issuer)


class IssuerEmailConfirmationWaitingView(
    HabilitationStepMixin, CheckIssuerMixin, TemplateView
):
    template_name = "email_confirmation_waiting.html"

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def post(self, request, *args, **kwargs):
        """Resend a confirmation link"""
        IssuerEmailConfirmation.for_issuer(self.issuer).send(self.request)

        return self.render_to_response(
            {
                **self.get_context_data(**kwargs),
                "support_email": settings.EMAIL_CONFIRMATION_SUPPORT_CONTACT_EMAIL,
                "support_subject": settings.EMAIL_CONFIRMATION_SUPPORT_CONTACT_SUBJECT,
                "support_body": settings.EMAIL_CONFIRMATION_SUPPORT_CONTACT_BODY,
            }
        )


class IssuerEmailConfirmationView(
    HabilitationStepMixin, CheckIssuerMixin, TemplateView
):
    template_name = "email_confirmation_confirm.html"

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.email_confirmation = get_object_or_404(
            IssuerEmailConfirmation, issuer=self.issuer, key=kwargs.get("key")
        )

    def get(self, request, *args, **kwargs):
        return (
            super().get(request, *args, **kwargs)
            if self.email_confirmation.confirm()
            else self.render_to_response(
                {**self.get_context_data(**kwargs), "email_confirmation_expired": True}
            )
        )

    def post(self, request, *args, **kwargs):
        return (
            self.__continue()
            if self.issuer.email_verified
            else self.render_to_response(
                {**self.get_context_data(**kwargs), "email_confirmation_expired": True}
            )
        )

    def __continue(self):
        return redirect(
            "habilitation_new_organisation", issuer_id=self.issuer.issuer_id
        )


class IssuerPageView(VerifiedEmailIssuerView, TemplateView):
    template_name = "issuer_space.html"


class ModifyIssuerFormView(VerifiedEmailIssuerView, NewIssuerFormView):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ISSUER

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organisation = None
        if "issuer_id" in kwargs and "uuid" in kwargs:
            self.organisation = get_object_or_404(
                OrganisationRequest,
                issuer__issuer_id=kwargs["issuer_id"],
                uuid=kwargs["uuid"],
            )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.issuer}

    def get_success_url(self):
        if self.organisation:
            return reverse(
                "habilitation_validation",
                kwargs={
                    "issuer_id": self.saved_model.issuer_id,
                    "uuid": self.organisation.uuid,
                },
            )

        return reverse(
            "habilitation_new_organisation",
            kwargs={"issuer_id": self.saved_model.issuer_id},
        )


class NewOrganisationRequestFormView(
    HabilitationStepMixin, VerifiedEmailIssuerView, FormView, AdressAutocompleteJSMixin
):
    template_name = "organisation_form.html"

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ORGANISATION

    def form_valid(self, form):
        form.instance.issuer = self.issuer
        self.saved_model: OrganisationRequest = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "habilitation_new_aidants",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.saved_model.uuid),
            },
        )

    def get_form(self, form_class=None):
        form = OrganisationRequestForm(**self.get_form_kwargs())
        self.define_html_attributes(form)
        return form

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "type_other_value": RequestOriginConstants.OTHER.value,
        }


class ModifyOrganisationRequestFormView(
    OnlyNewRequestsView, NewOrganisationRequestFormView
):
    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.ORGANISATION

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.organisation}


class PersonnelRequestFormView(
    OnlyNewRequestsView, FormView, AdressAutocompleteJSMixin
):
    template_name = "personnel_form.html"

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.PERSONNEL

    def form_valid(self, form: PersonnelForm):
        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        issuer_data = model_to_dict(
            self.issuer, exclude=[*IssuerForm.Meta.exclude, "id"]
        )
        issuer_data.update(
            model_to_dict(self.organisation, fields=("zipcode", "city", "address"))
        )
        # Fields of type PhoneNumberField are not natively JSON serializable
        issuer_data["phone"] = str(issuer_data["phone"])
        return {
            **super().get_context_data(**kwargs),
            "issuer_form": IssuerForm(instance=self.issuer, render_non_editable=True),
            "issuer_data": issuer_data,
            "organisation": self.organisation,
        }

    def get_form(self, form_class=None):
        form = PersonnelForm(organisation=self.organisation, **self.get_form_kwargs())
        self.define_html_attributes(form.manager_form)
        return form

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        manager = self.organisation.manager
        aidant_qs = self.organisation.aidant_requests

        if aidant_qs.count() > 0:
            form_kwargs[f"{PersonnelForm.AIDANTS_FORMSET_PREFIX}_queryset"] = (
                aidant_qs.all()
            )

        if manager:
            form_kwargs[f"{PersonnelForm.MANAGER_FORM_PREFIX}_instance"] = manager

        return form_kwargs

    def get_success_url(self):
        return reverse(
            "habilitation_validation",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.organisation.uuid),
            },
        )


class ValidationRequestFormView(OnlyNewRequestsView, FormView):
    template_name = "aidants_connect_habilitation/validation_request_form_view/validation_form.html"  # noqa: E501
    form_class = ValidationForm

    @property
    def step(self) -> HabilitationFormStep:
        return HabilitationFormStep.SUMMARY

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "organisation": self.organisation,
                # using a generator to avoid unneccessary computations
                "habilitation_requests": (
                    ProfileCardAidantRequestPresenter(it)
                    for it in self.organisation.aidant_requests.all()
                ),
                "type_other": RequestOriginConstants.OTHER.value,
            }
        )
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse(
            "habilitation_organisation_view",
            kwargs={
                "issuer_id": str(self.issuer.issuer_id),
                "uuid": str(self.organisation.uuid),
            },
        )

    def get_initial(self):
        return {
            "cgu": self.organisation.cgu,
            "not_free": self.organisation.not_free,
            "dpo": self.organisation.dpo,
            "professionals_only": self.organisation.professionals_only,
            "without_elected": self.organisation.without_elected,
        }

    def form_valid(self, form):
        form.save(self.organisation)
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        form: ValidationForm = self.get_form()
        if self.organisation.manager is None:
            form.add_error(
                None,
                "Veuillez ajouter le ou la référente de la structure avant validation.",
            )
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ReadonlyRequestView(LateStageRequestView, FormView):
    template_name = "view_organisation_request.html"
    form_class = RequestMessageForm

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "organisation": self.organisation,
            "aidants": self.organisation.aidant_requests,
        }

    def get_success_url(self):
        return self.organisation.get_absolute_url()

    def form_valid(self, form):
        message: RequestMessage = form.save(commit=False)
        message.sender = MessageStakeholders.ISSUER.name
        message.organisation = self.organisation
        message.save()

        if self.request.GET.get("http-api", False):
            return self.response_class(
                request=self.request,
                template="request_messages/_message_item.html",
                context={
                    "message": message,
                    "issuer": self.issuer,
                },
                using=self.template_engine,
                content_type="text/html; charset=utf-8",
            )

        return super().form_valid(form)


class AddAidantsRequestView(LateStageRequestView, FormView):
    template_name = "add_aidants_request.html"

    def dispatch(self, request, *args, **kwargs):
        if self.organisation.status not in self.organisation.Status.aidant_registrable:
            messages.error(
                request,
                "Il n'est pas possible d'ajouter de nouveaux aidants à cette demande.",
            )
            return HttpResponseRedirect(
                reverse(
                    "habilitation_organisation_view",
                    kwargs={
                        "issuer_id": self.organisation.issuer.issuer_id,
                        "uuid": self.organisation.uuid,
                    },
                )
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        return AidantRequestFormSet(
            organisation=self.organisation, **self.get_form_kwargs()
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "organisation": self.organisation,
        }

    def get_success_url(self):
        return reverse(
            "habilitation_organisation_view",
            kwargs={
                "issuer_id": self.organisation.issuer.issuer_id,
                "uuid": self.organisation.uuid,
            },
        )

    def form_valid(self, formset: AidantRequestFormSet):
        formset.save()
        if self.organisation.status == RequestStatusConstants.VALIDATED.name:
            self.organisation.create_aidants(
                Organisation.objects.get(data_pass_id=self.organisation.data_pass_id)
            )
        return super().form_valid(formset)


class AidantFormationRegistrationView(
    LateStageRequestView, CommonFormationRegistrationView
):
    def dispatch(self, request, *args, **kwargs):
        self.person = self.get_person()
        if not self.person.habilitation_request:
            raise Http404

        aidant = Aidant.objects.filter(email=self.organisation.manager.email)
        if aidant.exists() and aidant.first().last_login:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get_person(self):
        return get_object_or_404(
            AidantRequest, pk=self.kwargs["aidant_id"], organisation=self.organisation
        )

    def get_cancel_url(self) -> str:
        return self.organisation.get_absolute_url()

    def get_habilitation_request(self) -> HabilitationRequest:
        return self.person.habilitation_request

    def get_success_url(self):
        return self.organisation.get_absolute_url()


class HabilitationRequestCancelationView(LateStageRequestView, FormView):
    form_class = Form
    template_name = "cancel-habilitation-request.html"

    def dispatch(self, request, *args, **kwargs):
        self.person = get_object_or_404(
            AidantRequest, pk=self.kwargs["aidant_id"], organisation=self.organisation
        )

        if (
            not self.person.habilitation_request
            or not self.person.habilitation_request.status_cancellable_by_responsable
        ):
            raise Http404

        aidant = Aidant.objects.filter(email=self.organisation.manager.email)
        if aidant.exists() and aidant.first().last_login:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.person.habilitation_request.cancel_by_responsable()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "request": self.person.habilitation_request,
                "organisation": self.organisation,
            }
        )
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse(
            "habilitation_organisation_view",
            kwargs={"issuer_id": self.issuer.issuer_id, "uuid": self.organisation.uuid},
        )


class ManagerFormationRegistrationView(AidantFormationRegistrationView):
    def get_person(self):
        return get_object_or_404(
            Manager, organisation=self.organisation, is_aidant=True
        )
