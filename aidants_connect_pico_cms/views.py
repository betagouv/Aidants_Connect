from django.views.generic.detail import DetailView

from aidants_connect_pico_cms.models import Testimony


class TestimonyView(DetailView):
    model = Testimony

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_testimonies"] = Testimony.objects.filter(published=True).order_by(
            "sort_order"
        )
        return context
