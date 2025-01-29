from django.views.generic import TemplateView

from aidants_connect_common.models import Formation


class FormationsListing(TemplateView):
    template_name = "public_website/listing_formations.html"

    def get_context_data(self, **kwargs):
        list_formations = Formation.objects.available_now()
        return {
            **super().get_context_data(**kwargs),
            "list_formations": list_formations,
        }
