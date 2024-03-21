import logging
import re
from secrets import token_urlsafe
from urllib.parse import unquote, urlencode

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView

import jwt

from aidants_connect_common.forms import PatchedErrorList
from aidants_connect_common.views import RequireConnectionMixin
from aidants_connect_web.decorators import aidant_logged_with_activity_required
from aidants_connect_web.forms import (
    AuthorizeSelectUsagerForm,
    OAuthParametersForm,
    OAuthParametersFormV2,
    SelectDemarcheForm,
    TokenForm,
    TokenFormV2,
)
from aidants_connect_web.models import (
    Aidant,
    AutorisationQuerySet,
    Connection,
    Journal,
    Usager,
    UsagerQuerySet,
)
from aidants_connect_web.utilities import generate_id_token

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@aidant_logged_with_activity_required
class Authorize(RequireConnectionMixin, FormView):
    form_class = AuthorizeSelectUsagerForm
    template_name = "aidants_connect_web/id_provider/authorize.html"

    def dispatch(self, request, *args, **kwargs):
        self.aidant: Aidant = request.user
        self.usager_with_active_auth: UsagerQuerySet = (
            self.aidant.get_usagers_with_active_autorisation()
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.get_oauth_parameters_form()
        if form.is_valid():
            self.oauth_parameters_form = form
            self.connection = Connection.objects.create(
                state=form.cleaned_data["state"], nonce=form.cleaned_data["nonce"]
            )
            return super().get(request, *args, **kwargs)
        else:
            return self.form_invalid_get(form)

    def post(self, request, *args, **kwargs):
        self.oauth_parameters_form = self.get_oauth_parameters_form(relaxed=True)

        if not self.oauth_parameters_form.is_valid():
            # That case should only happen if, for whatever reason,
            # the user touched the HTML with their sticky fingers…
            log.error(
                "The HTML was modified, bad OAuth parameters "
                f"{self.oauth_parameters_form.data!r}"
            )
            # Punish the user
            logout(self.request)
            return HttpResponseForbidden()

        view_location = f"{self.__module__}.{self.__class__.__name__}"
        connection_id = self.request.POST.get("connection_id")

        try:
            self.connection = Connection.objects.get(pk=connection_id)

            if self.connection.is_expired:
                log.info(f"Connection has expired @ {view_location}")
                return render(request, "408.html", status=408)

        except Connection.DoesNotExist:
            log.error(
                f"No connection id found for id {connection_id} @ {view_location}"
            )
            logout(request)
            return HttpResponseForbidden()

        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        if (
            "unauthorized_user"
            in form.errors.get("chosen_usager", PatchedErrorList()).error_codes
        ):
            log.info(
                f"User {self.request.POST['chosen_usager']} does not have a valid "
                f"autorisation with the organisation of aidant with id {self.aidant.id}"
            )
            logout(self.request)
            return HttpResponseForbidden()

        if "invalid" in form.errors.get("connection", PatchedErrorList()).error_codes:
            view_location = f"{self.__module__}.{self.__class__.__name__}"
            log.error(f"Absent connection id @ {view_location}")
            logout(self.request)
            return HttpResponseForbidden()

        return super().form_invalid(form)

    def form_valid(self, form):
        self.connection.usager = form.cleaned_data["chosen_usager"]
        self.connection.save()
        self.request.session["connection"] = self.connection.pk
        return super().form_valid(form)

    def form_invalid_get(self, form):
        view_location = f"{self.__module__}.{self.__class__.__name__}"
        requirement_errors = set()
        format_validation_errors = set()
        additionnal_keys_errors = set()
        for field_name, errors in form.errors.items():
            if "required" in errors.error_codes:
                requirement_errors.update([field_name])
            if "invalid" in errors.error_codes:
                format_validation_errors.update([field_name])
            if error := errors.get_error_by_code("additionnal_key"):
                additionnal_keys_errors.update([error.message])

        if requirement_errors:
            log.info(
                f"400 Bad request: The following parameters are missing: "
                f"{requirement_errors!r} @ {view_location}"
            )
            return HttpResponseBadRequest("missing parameter")

        if format_validation_errors:
            log.info(
                "403 forbidden request: The following parameters are malformed: "
                f"{format_validation_errors!r} @ {view_location}"
            )
            return HttpResponseForbidden("malformed parameter value")

        if additionnal_keys_errors:
            log.info(
                "403 forbidden request: Unexpected parameters: "
                f"{additionnal_keys_errors!r} @ {view_location}"
            )
            return HttpResponseForbidden("forbidden parameter value {")

        log.warning(f"Uncatched validation error @ {view_location}")
        return HttpResponseBadRequest()

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "usager_with_active_auth": self.usager_with_active_auth,
        }

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "oauth_parameters_form": self.oauth_parameters_form,
            "connection_id": self.connection.pk,
            "usagers": self.usager_with_active_auth,
            "aidant": self.aidant,
            "data": [
                {"value": user.id, "label": user.get_full_name()}
                for user in self.usager_with_active_auth
            ],
        }

    def get_oauth_parameters_form(self, **kwargs):
        data = self.request.GET if self.request.method == "GET" else self.request.POST
        return (
            OAuthParametersFormV2(
                data=data, organisation=self.aidant.organisation, **kwargs
            )
            if (
                unquote(data.get("redirect_uri", ""))
                == settings.FC_AS_FI_CALLBACK_URL_V2
            )
            else OAuthParametersForm(
                data=data, organisation=self.aidant.organisation, **kwargs
            )
        )

    def get_success_url(self):
        parameters = urlencode(self.oauth_parameters_form.cleaned_data)
        return f"{reverse('fi_select_demarche')}?{parameters}"


@aidant_logged_with_activity_required
class FISelectDemarche(RequireConnectionMixin, FormView):
    template_name = "aidants_connect_web/id_provider/fi_select_demarche.html"
    form_class = SelectDemarcheForm

    def dispatch(self, request, *args, **kwargs):
        if isinstance(result := self.check_connection(request), HttpResponse):
            return result

        self.connection = result
        self.aidant: Aidant = request.user
        self.usager: Usager = self.connection.usager
        self.user_demarches: AutorisationQuerySet = (
            self.aidant.get_active_demarches_for_usager(self.usager)
        )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form: SelectDemarcheForm):
        if (
            "chosen_demarche" in form.errors
            and "unauthorized_demarche" in form.errors["chosen_demarche"].error_codes
        ):
            log.info("The autorisation asked does not exist")
            return HttpResponseForbidden()

        return super().form_invalid(form)

    def form_valid(self, form):
        self.code = token_urlsafe(64)
        self.connection.code = make_password(self.code, settings.FC_AS_FI_HASH_SALT)
        self.connection.demarche = form.cleaned_data["chosen_demarche"]
        self.connection.autorisation = self.aidant.get_valid_autorisation(
            self.connection.demarche, self.usager
        )
        self.connection.complete = True
        self.connection.aidant = self.aidant
        self.connection.organisation = self.aidant.organisation
        self.connection.save()
        self.redirect_uri = form.cleaned_data["redirect_uri"]
        return super().form_valid(form)

    def get_form_kwargs(self):
        return {
            **super().get_form_kwargs(),
            "aidant": self.aidant,
            "user": self.usager,
        }

    def get_context_data(self, **kwargs):
        oauth_parameters_form = (
            OAuthParametersFormV2(
                data=self.request.GET, organisation=self.aidant.organisation
            )
            if (
                unquote(self.request.GET.get("redirect_uri", ""))
                == settings.FC_AS_FI_CALLBACK_URL_V2
            )
            else OAuthParametersForm(
                organisation=self.aidant.organisation, data=self.request.GET
            )
        )
        if oauth_parameters_form.is_valid():
            parameters = urlencode(oauth_parameters_form.cleaned_data)
            change_user_url = f"{reverse('authorize')}?{parameters}"
        else:
            change_user_url = None
        return {
            **super().get_context_data(**kwargs),
            "aidant": self.aidant.get_full_name(),
            "usager": self.usager,
            "demarches": {
                demarche_name: settings.DEMARCHES[demarche_name]
                for demarche_name in self.user_demarches
            },
            "change_user_url": change_user_url,
            "redirect_uri": oauth_parameters_form.cleaned_data.get(
                "redirect_uri", settings.FC_AS_FI_CALLBACK_URL
            ),
            "warn_scope": (
                {**settings.DEMARCHES["argent"], "value": "argent"}
                if "argent" in self.user_demarches
                else None
            ),
        }

    def get_success_url(self):
        return f"{self.redirect_uri}?code={self.code}&state={self.connection.state}"


@method_decorator([csrf_exempt, require_POST], name="dispatch")
class Token(FormView):
    form_class = TokenForm

    def get_form_class(self):
        if (
            unquote(self.request.POST.get("redirect_uri", ""))
            == settings.FC_AS_FI_CALLBACK_URL_V2
        ):
            return TokenFormV2
        return super().get_form_class()

    def form_invalid(self, form):
        view_location = f"{self.__module__}.{self.__class__.__name__}"
        parameter = list(form.errors.keys())[0]
        error_codes = form.errors[parameter].error_codes

        if "required" in error_codes:
            log.info(f"400 Bad request: There is no {parameter} @ {view_location}")
            return HttpResponseBadRequest()

        if "additionnal_key" in error_codes:
            log.info(f"403 forbidden request: unexpected {parameter} @ {view_location}")
        else:
            log.info(f"403 forbidden request: malformed {parameter} @ {view_location}")
        return HttpResponseForbidden()

    def form_valid(self, form):
        code = form.cleaned_data["code"]
        code_hash = make_password(code, settings.FC_AS_FI_HASH_SALT)
        try:
            connection = Connection.objects.get(code=code_hash)
            if connection.is_expired:
                log.info("connection has expired at token")
                return render(self.request, "408.html", status=408)
        except ObjectDoesNotExist:
            view_location = f"{self.__module__}.{self.__class__.__name__}"
            log.info(
                f"403: No connection corresponds to the code {code} @ {view_location}"
            )
            return HttpResponseForbidden()

        encoded_id_token = jwt.encode(
            generate_id_token(connection),
            form.cleaned_data["client_secret"],
            algorithm="HS256",
        )

        access_token = token_urlsafe(64)
        connection.access_token = make_password(
            access_token, settings.FC_AS_FI_HASH_SALT
        )
        connection.save()

        return JsonResponse(
            {
                "access_token": access_token,
                "expires_in": 3600,
                "id_token": encoded_id_token,
                "refresh_token": get_random_string(18).lower(),
                "token_type": "Bearer",
            }
        )


def user_info(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    if not auth_header:
        log.info("403: Missing auth header")
        return HttpResponseForbidden()

    pattern = re.compile(r"^Bearer\s([A-Z-a-z-0-9-_/-]+)$")
    if not pattern.match(auth_header):
        log.info("Auth header has wrong format")
        return HttpResponseForbidden()

    auth_token = auth_header[7:]
    auth_token_hash = make_password(auth_token, settings.FC_AS_FI_HASH_SALT)
    try:
        connection = Connection.objects.get(access_token=auth_token_hash)
        if connection.is_expired:
            log.info("connection has expired at user_info")
            return render(request, "408.html", status=408)
    except ObjectDoesNotExist:
        log.info("403: /user_info No connection corresponds to the access_token")
        log.info(auth_token)
        return HttpResponseForbidden()

    usager = model_to_dict(
        connection.usager,
        fields=[
            "birthcountry",
            "birthdate",
            "birthplace",
            "creation_date",
            "email",
            "family_name",
            "gender",
            "given_name",
            "preferred_username",
            "sub",
        ],
    )

    birthdate = usager["birthdate"]
    birthplace = usager["birthplace"]
    birthcountry = usager["birthcountry"]
    usager["birthplace"] = str(birthplace)
    usager["birthcountry"] = str(birthcountry)
    usager["birthdate"] = str(birthdate)

    Journal.log_autorisation_use(
        aidant=connection.aidant,
        usager=connection.usager,
        demarche=connection.demarche,
        access_token=connection.access_token,
        autorisation=connection.autorisation,
    )

    return JsonResponse(usager, safe=False)


def end_session_endpoint(request):
    if request.method != "GET":
        log.info("Request should be a GET @ end_session_endpoint")
        return HttpResponseBadRequest()

    if (redirect_uri := request.GET.get("post_logout_redirect_uri")) not in [
        settings.FC_AS_FI_LOGOUT_REDIRECT_URI,
        settings.FC_AS_FI_LOGOUT_REDIRECT_URI_V2,
    ]:
        message = (
            f"post_logout_redirect_uri is "
            f"{request.GET.get('post_logout_redirect_uri')} instead of "
            f"{redirect_uri} @ end_session_endpoint"
        )
        log.info(message)
        return HttpResponseBadRequest()

    if redirect_uri == settings.FC_AS_FI_LOGOUT_REDIRECT_URI_V2:
        redirect_uri = f"{redirect_uri}?state={request.GET.get('state')}"

    return HttpResponseRedirect(redirect_uri)
