from magicauth import views as magicauth_views

from aidants_connect_common.utils.email import render_email
from aidants_connect_web.forms import LoginEmailForm


class LoginView(magicauth_views.LoginView):
    form_class = LoginEmailForm

    def render_email(self, context):
        return render_email(self.html_template, context)
