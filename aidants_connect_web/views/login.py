from django.template.defaultfilters import urlencode
from django.urls import reverse

from magicauth import views as magicauth_views

from aidants_connect_common.utils.email import render_email as render_mjml_email
from aidants_connect_web.forms import LoginEmailForm


class LoginView(magicauth_views.LoginView):
    form_class = LoginEmailForm

    def render_email(self, context):
        return render_mjml_email("login/email_template.mjml", context)

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
