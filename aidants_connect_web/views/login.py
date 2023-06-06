from magicauth import views as magicauth_views

from aidants_connect_common.utils.email import render_email
from aidants_connect_web.forms import LoginEmailForm


class LoginView(magicauth_views.LoginView):
    form_class = LoginEmailForm

    def render_email(self, context):
        return render_email(self.html_template, context)

    def get_email_context(self, user, token, extra_context=None):
        return {
            **super().get_email_context(user, token, extra_context),
            "email_title": "Votre lien de connexion à Aidants Connect",
        }
