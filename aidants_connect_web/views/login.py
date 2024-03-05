from django.template.defaultfilters import urlencode
from django.urls import reverse
from django.views.generic import RedirectView

from magicauth import views as magicauth_views

from aidants_connect_common.utils import render_email
from aidants_connect_web.forms import DsfrOtpForm, LoginEmailForm


class LoginRedirect(RedirectView):
    pattern_name = "login"
    permanent = True


class LoginView(magicauth_views.LoginView):
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
