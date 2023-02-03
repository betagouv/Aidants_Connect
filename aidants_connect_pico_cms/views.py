from django.conf import settings
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic.base import View
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


class FaqDefaultView(View):
    def get(self, request, *args, **kwargs):
        if not settings.FF_USE_PICO_CMS_FOR_FAQ:
            return render(request, "public_website/faq/generale.html")

        first_published_category = (
            FaqCategory.objects.filter(published=True).order_by("sort_order").first()
        )
        if not first_published_category:
            return HttpResponseNotFound()
        return HttpResponseRedirect(first_published_category.get_absolute_url())


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
