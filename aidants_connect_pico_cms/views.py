from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView

from aidants_connect_pico_cms.models import FaqCategory, FaqQuestion, Testimony


class TestimonyView(DetailView):
    model = Testimony

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_testimonies"] = Testimony.objects.filter(published=True).order_by(
            "sort_order"
        )
        return context


class FaqDefaultView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        first_published_category = (
            FaqCategory.objects.filter(published=True).order_by("sort_order").first()
        )
        return first_published_category.get_absolute_url()


class FaqCategoryView(DetailView):
    model = FaqCategory

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = FaqCategory.objects.filter(published=True).order_by(
            "sort_order"
        )
        context["questions"] = FaqQuestion.objects.filter(
            published=True, category=self.object
        ).order_by("sort_order")
        return context
