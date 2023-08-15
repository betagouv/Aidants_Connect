from django.conf import settings
from django.views.generic import TemplateView


class Sandbox(TemplateView):
    template_name = "aidants_connect_web/sandbox/presentation.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "sandbox_url": settings.SANDBOX_URL,
        }
