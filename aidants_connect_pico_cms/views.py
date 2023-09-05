from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import RedirectView, View
from django.views.generic.detail import DetailView

from aidants_connect_pico_cms.models import FaqCategory, FaqQuestion, Testimony
from aidants_connect_pico_cms.utils import render_markdown


class TestimoniesView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        testimony_qs = Testimony.objects.for_display()
        if not testimony_qs.exists():
            return reverse("espace_aidant_home")

        return reverse("temoignage-detail", kwargs={"slug": testimony_qs.first().slug})


class TestimonyView(DetailView):
    model = Testimony

    def get_context_data(self, **kwargs):
        kwargs.update({"all_testimonies": Testimony.objects.for_display()})
        return super().get_context_data(**kwargs)


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


@method_decorator(csrf_exempt, name="dispatch")
class MarkdownRenderView(View):
    def post(self, request, *args, **kwargs):
        return HttpResponse(render_markdown(self.request.POST.get("body", "")))
