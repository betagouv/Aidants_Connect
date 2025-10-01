import logging

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from ..forms import AskingMobileForm, ConnexionChoiceForm
from ..models import HabilitationRequest, MobileAskingUser

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class ConnexionChoiceView(FormView):
    template_name = "public_website/connexion_choice.html"
    form_class = ConnexionChoiceForm

    def form_valid(self, form):
        h_requests = HabilitationRequest.objects.filter(
            email=form.cleaned_data["email"]
        )
        for h_request in h_requests:
            h_request.connexion_mode = form.cleaned_data["connexion_mode"]
            h_request.save()
        return super().form_valid(form)

    def get_success_url(self):
        return settings.URL_TEST_PIX


class AskingMobileView(FormView):
    template_name = "public_website/asking_mobile.html"
    form_class = AskingMobileForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            referent_id = kwargs.get("referent_id")
        except ValueError:
            raise Http404()
        self.mobile_asking = get_object_or_404(
            MobileAskingUser, user_padding=referent_id
        )

    def form_valid(self, form):
        form_email = form.cleaned_data["user_email"]
        if form_email.lower() == self.mobile_asking.user.email.lower():
            self.mobile_asking.user_mobile = form.cleaned_data["user_mobile"]
            self.mobile_asking.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("thanks_asking_mobile")


class ThanksAskingMobileView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "public_website/thanks_asking_mobile.html")
