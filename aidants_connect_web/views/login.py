from magicauth import views as magicauth_views

from aidants_connect_web.forms import LoginEmailForm


class LoginView(magicauth_views.LoginView):
    form_class = LoginEmailForm
