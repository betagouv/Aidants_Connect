from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.template.defaultfilters import urlencode
from django.urls import reverse
from django.views.generic import RedirectView

from magicauth import views as magicauth_views

from aidants_connect_common.utils import render_email
from aidants_connect_web.forms import DsfrOtpForm, LoginEmailForm


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
                username=settings.BACKUP_EMAIL_USERNAME,
                password=settings.BACKUP_EMAIL_PASSWORD,
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
