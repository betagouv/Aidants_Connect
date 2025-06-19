from django.conf import settings
from django.contrib.auth import login
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import get_connection, send_mail
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import urlencode
from django.urls import reverse, reverse_lazy
from django.utils.crypto import get_random_string
from django.views.generic import FormView, RedirectView, TemplateView

import requests
from django_otp.plugins.otp_static.lib import add_static_token
from magicauth import views as magicauth_views
from magicauth.next_url import NextUrlMixin
from magicauth.otp_forms import OTPForm

from aidants_connect_common.utils import render_email
from aidants_connect_web.forms import (
    DsfrOtpForm,
    LoginEmailForm,
    ManagerFirstLoginForm,
    ManagerFirstLoginWithCodeForm,
)
from aidants_connect_web.models import Aidant

from ..models import FirstConnexionManagerInfo


class LoginRedirect(RedirectView):
    pattern_name = "login"
    permanent = True


def tld_need_another_stmp(user_email):
    tdls_need_another_smtp = settings.TDL_NEED_BACKUP_SMTP.split(",")
    tld = user_email.rsplit("@", 1)[1]
    return tld in tdls_need_another_smtp


class ACSendEMailForTokenMixin:
    def send_email(self, user, user_email, token, extra_context=None):
        text_message, html_message = self.render_email(
            self.get_email_context(user, token, extra_context)
        )
        connection = None
        if tld_need_another_stmp(user_email):
            connection = get_connection(
                host=settings.BACKUP_EMAIL_HOST,
                port=settings.BACKUP_EMAIL_PORT,
                username=settings.BACKUP_EMAIL_HOST_USER,
                password=settings.BACKUP_EMAIL_HOST_PASSWORD,
                use_tls=settings.BACKUP_EMAIL_USE_TLS,
                use_ssl=settings.BACKUP_EMAIL_USE_SSL,
            )
        send_mail(
            subject=self.email_subject,
            message=text_message,
            from_email=self.from_email,
            html_message=html_message,
            recipient_list=[user_email],
            fail_silently=False,
            connection=connection,
        )


class LoginView(ACSendEMailForTokenMixin, magicauth_views.LoginView):
    form_class = LoginEmailForm
    otp_form_class = DsfrOtpForm

    def otp_form_invalid(self, form, otp_form):
        from aidants_connect_web.signals import otp_challenge_failed

        otp_challenge_failed.send(
            sender=self.__class__, user=otp_form.user, request=self.request
        )

        return super().otp_form_invalid(form, otp_form)

    def render_email(self, context):
        return render_email(self.html_template, context)

    def get_email_context(self, user, token, extra_context=None):
        context = super().get_email_context(user, token, extra_context)
        return {
            **context,
            "email_title": "Votre lien de connexion à Aidants Connect",
            "href": (
                f"https://{context['site'].domain}"
                f"{reverse('magicauth-wait', args=(context['token'].key,))}"
                f"?next={urlencode(context['next_url'])}"
            ),
        }


class ManagerFirstLoginView(ACSendEMailForTokenMixin, NextUrlMixin, FormView):
    email_subject = settings.FIRST_LOGIN_REFERENT_EMAIL_SUBJECT
    html_template = settings.FIRST_LOGIN_REFERENT_EMAIL_HTML_TEMPLATE
    text_template = settings.FIRST_LOGIN_REFERENT_EMAIL_TEXT_TEMPLATE
    from_email = settings.MAGICAUTH_FROM_EMAIL
    form_class = ManagerFirstLoginForm
    template_name = "login/manager_first_login.html"

    def form_valid(self, form, *args, **kwargs):
        user_email = form.cleaned_data["email"]
        user_mobile = form.cleaned_data["mobile"]

        user_email = user_email.lower()

        referent = get_object_or_404(
            Aidant,
            email__iexact=user_email,
            is_active=True,
        )

        if not user_mobile == referent.phone:
            raise Http404()

        mobile_referent = user_mobile.as_e164.replace("+", "00")

        fconnexion_info, _ = FirstConnexionManagerInfo.objects.get_or_create(
            user=referent,
            already_used=False,
            defaults={"user_secret": get_random_string(16)},
        )
        new_token = get_random_string(6, allowed_chars="123456789")
        add_static_token(user_email, new_token)
        requests.get(
            f"{settings.FIRT_LOGIN_URL}?&account={settings.FIRT_LOGIN_ACCOUNT}&login={settings.FIRST_LOGIN_USER}&password={settings.FIRT_LOGIN_PASS}&from={settings.FIRST_LOGIN_SENDER}&to={mobile_referent}&message={settings.FISRT_LOGIN_MESSAGE}:{new_token}"  # noqa
        )
        self.send_email(referent, user_email, fconnexion_info.user_secret)
        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        url = reverse_lazy("manager_first_connexion_email_sent")

        next_url_quoted = self.get_next_url_encoded(self.request)
        return f"{url}?next={next_url_quoted}"

    def render_email(self, context):
        return render_email(self.html_template, context)

    def get_email_context(self, user, token, extra_context=None):
        context = {
            "user": user,
            "TOKEN_DURATION_MINUTES": 30,
            "email_title": "Votre lien pour le code de première connexion à Aidants Connect",  # noqa
            "href": (
                f"https://{get_current_site(self.request).domain}"
                f"{reverse('manager_first_login_with_code', args=(token,))}"
            ),
        }
        if extra_context:
            context.update(extra_context)

        return context


class ManagerFirstLoginEmailSentView(NextUrlMixin, TemplateView):
    template_name = "login/manager_first_login_email_sent.html"


class ManagerFirstLoginWithCodeView(FormView):
    form_class = ManagerFirstLoginWithCodeForm
    otp_form_class = OTPForm
    template_name = "login/manager_first_login_with_code.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            manager_id = kwargs.get("manager_id")
        except ValueError:
            raise Http404()
        self.manager_info = get_object_or_404(
            FirstConnexionManagerInfo,
            user_secret=manager_id,
            already_used=False,
        )

    def get_otp_form_class(self):
        return self.otp_form_class

    def form_valid(self, form, *args, **kwargs):
        user = self.manager_info.user
        otp_form = self.get_otp_form_class()(
            user, data={"otp_token": form.cleaned_data["code_otp"]}
        )

        if not otp_form.is_valid():
            return self.otp_form_invalid(form, otp_form)

        self.manager_info.already_used = True
        self.manager_info.save()
        login(
            self.request,
            user,
        )
        return super().form_valid(form)

    def otp_form_invalid(self, form, otp_form):

        form.add_error("code_otp", "Code de première connexion invalide")

        return self.render_to_response(
            self.get_context_data(form=form, OTP_form=otp_form)
        )

    def get_success_url(self, **kwargs):
        # url = reverse_lazy("espace_responsable_aidant_add_app_otp", args=(self.manager_info.pk,))  # noqa
        url = reverse_lazy("espace_responsable")
        return url
